import argparse
import json
import os
import subprocess
import sys

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Optional

from mixcloud_uploader.mixcloud import Mixcloud, authenticate_via_browser
from mixcloud_uploader.tracklist import read_cuesheet, read_tabular, write_tabular
from mixcloud_uploader.transcode import transcode

DEFAULT_CONFIG_DIR = Path.home() / '.config' / 'mixcloud-uploader'
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / 'config.json'
DEFAULT_CACHED_AUTH_PATH = DEFAULT_CONFIG_DIR / 'cached-auth.json'
DEFAULT_RECORDINGS_PATH = Path.home() / 'Music' / 'Mixxx' / 'Recordings'

@dataclass
class Options:
    # The path to the raw recording (a Mixxx-generated wav).
    recording_path: Path
    # The path to the tracklist (a Mixxx-generated Cue sheet).
    tracklist_path: Path
    # The path to the transcoded mp3.
    output_path: Path
    # Whether to run noninteractively.
    noninteractive: bool
    # The API wrapper.
    mixcloud: Mixcloud
    # The name for the uplaoded mix.
    name: str
    # The path to the artwork.
    artwork_path: Optional[Path]
    # The tags for the mix.
    tags: list[str]

def find_latest_recording(recordings_dir: Path) -> tuple[Optional[Path], Optional[Path]]:
    sorted_files = sorted(recordings_dir.iterdir(), key=lambda f: f.name, reverse=True)
    for wav_path, cue_path in zip(sorted_files, sorted_files[1:]):
        if wav_path.name.endswith('.wav') and cue_path.name.endswith('.cue'):
            return wav_path, cue_path
    return None, None

def find_next_name(pattern: str, mixcloud: Mixcloud) -> str:
    # TODO
    pass

def run(opts: Options):
    # Transcode the audio if needed
    if opts.output_path.exists():
        print('==> Already transcoded, skipping...')
    else:
        print(f'==> Transcoding {opts.recording_path} to {opts.output_path}...')
        transcode(opts.recording_path, opts.output_path)
    
    # Parse and prompt user to edit the tracklist
    tracks = read_cuesheet(opts.tracklist_path)

    # Open editor with cuesheet if not noninteractive
    if not opts.noninteractive:
        with NamedTemporaryFile(prefix='tracklist-', suffix='.txt', mode='w+t') as tmpfile:
            editor = os.environ.get('EDITOR', 'vim')

            path = Path(tmpfile.name)
            write_tabular(tracks, path)
            tmpfile.flush()

            subprocess.run([editor, str(path)])

            new_tracks = read_tabular(path)
            if tracks and not new_tracks:
                print('Empty tracklist, aborting...')
                sys.exit(1)
            tracks = new_tracks
    
    for track in tracks:
        print(track)

def main():
    parser = argparse.ArgumentParser(description='CLI tool for uploading Mixxx recordings to Mixcloud')
    parser.add_argument('-c', '--config', default=str(DEFAULT_CONFIG_PATH), help='The path to the config.json')
    parser.add_argument('-ca', '--cached-auth', default=str(DEFAULT_CACHED_AUTH_PATH), help='The path to the cached-auth.json')
    parser.add_argument('-d', '--recordings-dir', default=str(DEFAULT_RECORDINGS_PATH), help='The recordings directory to use.')
    parser.add_argument('-r', '--recording-name', help='The name of the recording (which should have a corresponding .cue and .wav file). Defaults to the latest.')
    parser.add_argument('-o', '--output-dir', help='The path to the output directory. Defaults to a temporary directory.')
    parser.add_argument('-n', '--name', help='The name to use for the uploaded mix.')
    parser.add_argument('-a', '--artwork', help='The artwork to use for the uploaded mix.')
    parser.add_argument('-t', '--tags', default='', help='A comma-separated list of tags to use for the uploaded mix.')
    parser.add_argument('-p', '--preset', help='A preset from the config to use (can be overridden with --name, --artwork and --tags).')
    parser.add_argument('-y', '--noninteractive', action='store_true', help='Runs noninteractively, i.e. uploads the tracklist as-is.')
    parser.add_argument('-at', '--access-token', help='The access token to use. Will skip browser-based authentication if provided.')
    parser.add_argument('-ci', '--client-id', help='The client id to use.')
    parser.add_argument('-cs', '--client-secret', help='The client secret to use.')

    # Parse CLI args
    args = parser.parse_args()
    recordings_dir = Path(args.recordings_dir)
    output_dir = Path(args.output_dir) if args.output_dir else None
    noninteractive = args.noninteractive
    config_path = Path(args.config) if args.config else None
    cached_auth_path = Path(args.cached_auth) if args.cached_auth else None
    preset_key = args.preset
    access_token = args.access_token
    client_id = args.client_id
    client_secret = args.client_secret
    name = args.name
    artwork_path = Path(args.artwork) if args.artwork else None
    tags = [tag.strip() for tag in args.tags.split(',')]

    # Read config
    if config_path and config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {}
    
    # Read cached auth
    if cached_auth_path and cached_auth_path.exists():
        with open(cached_auth_path, 'r') as f:
            cached_auth = json.load(f)
    else:
        cached_auth = {}

    # Read defaults from config and cached auth
    access_token = access_token or config.get('access-token', None) or cached_auth.get('access-token', None)
    client_id = client_id or config.get('client-id', None)
    client_secret = client_secret or config.get('client-secret', None)

    # Handle browser-based API authentication
    if not access_token:
        if noninteractive:
            print('Please specify an --access-token, browser-based authentication is not supported in noninteractive mode!')
            sys.exit(1)
        
        if not client_id or not client_secret:
            print(f'Please specify --client-id and --client-secret or provide them via {config_path}')
            sys.exit(1)
        
        # Perform OAuth2 authentication flow (interactively) via browser
        access_token = authenticate_via_browser(client_id, client_secret)

        # Cache access token
        cached_auth['access-token'] = access_token
        with open(cached_auth_path, 'w') as f:
            json.dump(f)
    
    # Set up API wrapper
    mixcloud = Mixcloud(access_token)

    # Read preset
    if preset_key:
        preset = config.get('presets', {}).get(preset_key, None)
        name_pattern = config.get('name', None)
        name = name or (find_next_name(name_pattern, mixcloud) if name_pattern else None)
        artwork = preset.get('artwork', None)
        artwork_path = artwork_path or (Path(artwork) if artwork else None)
        tags = tags or preset.get('tags', [])
    
    # Handle absence of name
    if not name:
        print(f'Please specify a name with --name or use a preset from {config_path}!')
        sys.exit(1)
    
    # Find recording
    if args.recording_name:
        # Use the specified recording
        recording_path = recordings_dir / f'{args.recording_name}.wav'
        tracklist_path = recordings_dir / f'{args.recording_name}.cue'
    else:
        # Default to latest recording
        recording_path, tracklist_path = find_latest_recording(recordings_dir)

    # Handle absence of a recording
    if not recording_path or not tracklist_path:
        print('No recording found!')
        sys.exit(1)
    elif not recording_path.exists():
        print(f'{recording_path} does not exist!')
        sys.exit(1)
    elif not tracklist_path.exists():
        print(f'{tracklist_path} does not exist!')
        sys.exit(1)
    
    with TemporaryDirectory(prefix='mixcloud-uploader-output-') as tmpdir:
        # Use a deterministic output name to allow caching the transcoded audio file.
        output_dir = output_dir or Path(tmpdir)
        output_path = output_dir / f"transcoded-{recording_path.name.split('.')[0]}.mp3"

        opts = Options(
            recording_path=recording_path,
            tracklist_path=tracklist_path,
            output_path=output_path,
            noninteractive=noninteractive,
            name=name,
            artwork_path=artwork_path,
            tags=tags
        )
        run(opts)
