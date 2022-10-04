import argparse
import json
import re
import os
import subprocess
import sys

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from tracklist.format.cuesheet import CuesheetFormat
from tracklist.format.tabular import TabularFormat
from typing import Optional

from mixcloud_uploader.mixcloud import Mixcloud, authenticate_via_browser
from mixcloud_uploader.transform import complete_tracklist, trim_tracklist
from mixcloud_uploader.transcode import transcode
from mixcloud_uploader.utils import confirm, input_with_default, pretty_box

DEFAULT_CONFIG_DIR = Path.home() / '.config' / 'mixcloud-uploader'
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / 'config.json'
DEFAULT_AUTH_PATH = DEFAULT_CONFIG_DIR / 'auth.json'
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
    # The description for the uploaded mix.
    description: Optional[str]
    # The path to the artwork.
    artwork_path: Optional[Path]
    # The tags for the mix.
    tags: list[str]
    # Optionally a duration in seconds to trim to.
    trim_duration: Optional[float]
    # Optionally a duration in seconds to fade in.
    fade_in: Optional[float]
    # Optionally a duration in seconds to fade out.
    fade_out: Optional[float]

def find_latest_recording(recordings_dir: Path) -> tuple[Optional[Path], Optional[Path]]:
    """Finds the latest recording's wav and cue path."""
    sorted_files = sorted(recordings_dir.iterdir(), key=lambda f: f.name, reverse=True)
    for wav_path, cue_path in zip(sorted_files, sorted_files[1:]):
        if wav_path.name.endswith('.wav') and cue_path.name.endswith('.cue'):
            return wav_path, cue_path
    return None, None

def find_next_name(pattern: str, mixcloud: Mixcloud) -> str:
    """
    Finds the 'next' name for a mix given a naming pattern (regex).
    The pattern should have at most one capturing group for capturing an index/number.
    """
    mixes = mixcloud.cloudcasts().get('data', [])
    newest_match = next((match for mix in mixes for match in [re.match(pattern, mix['name'])] if match), None) # TODO: Handle pagination
    newest_number = int(newest_match.group(1)) if newest_match else 0
    next_number = newest_number + 1
    return re.sub(r'\([^\)]+\)', str(next_number), pattern)

def run(opts: Options):
    # Transcode the audio if needed
    if opts.output_path.exists():
        print(f'==> Using cached {opts.output_path}...')
    else:
        print(f'==> Transcoding {opts.recording_path} to {opts.output_path}...')
        transcode(
            recording_path=opts.recording_path,
            output_path=opts.output_path,
            trim_duration=opts.trim_duration,
            fade_in=opts.fade_in,
            fade_out=opts.fade_out,
        )
    
    # Parse and prompt user to edit the tracklist
    with open(opts.tracklist_path, 'r') as f:
        tracks = CuesheetFormat().parse(f.read())

    # Complete artists
    tracks = complete_tracklist(tracks)

    # Truncate tracklist when trimming
    if opts.trim_duration:
        tracks = trim_tracklist(tracks, opts.trim_duration)

    edit_format = TabularFormat(separator=' :: ')

    # Open editor for editing the tracklist if not noninteractive
    if not opts.noninteractive:
        with NamedTemporaryFile(prefix='tracklist-', suffix='.txt', mode='w+t') as tmpfile:
            editor = os.environ.get('EDITOR', 'vim')
            path = Path(tmpfile.name)

            with open(path, 'w') as f:
                f.write(edit_format.format(tracks) + '\n')

            tmpfile.flush()
            subprocess.run([editor, str(path)])

            with open(path, 'r') as f:
                new_tracks = edit_format.parse(f.read())

            if tracks and not new_tracks:
                print('Empty tracklist, aborting...')
                sys.exit(1)
            tracks = new_tracks
    
    print('==> Confirming...')
    print(edit_format.format(tracks))
    print(pretty_box([
        f'- name: {opts.name}',
        f'- description: {opts.description}',
        f'- audio_file_path: {opts.output_path}',
        f'- artwork_path: {opts.artwork_path}',
        f'- tags: {opts.tags}',
        f'- tracks: {len(tracks.entries)} track(s), see above',
    ]))
    confirm('Upload this mix?')

    print('==> Uploading mix...')
    result = opts.mixcloud.upload(
        name=opts.name,
        description=opts.description,
        audio_file_path=opts.output_path,
        artwork_path=opts.artwork_path,
        tags=opts.tags,
        tracks=tracks
    )
    print(result)

    print('==> Successfully uploaded mix')

def main():
    parser = argparse.ArgumentParser(description='CLI tool for uploading Mixxx recordings to Mixcloud')
    parser.add_argument('-c', '--config', type=Path, default=DEFAULT_CONFIG_PATH, help='The path to the config.json')
    parser.add_argument('-a', '--auth', type=Path, default=DEFAULT_AUTH_PATH, help='The path to the auth.json')
    parser.add_argument('-rd', '--recordings-dir', type=Path, help='The recordings directory to use.')
    parser.add_argument('-rn', '--recording-name', help='The name of the recording (which should have a corresponding .cue and .wav file). Defaults to the latest.')
    parser.add_argument('-o', '--output-dir', type=Path, help='The path to the output directory. Defaults to a temporary directory.')
    parser.add_argument('-n', '--name', help='The name to use for the uploaded mix.')
    parser.add_argument('-d', '--description', help='The description to use for the uploaded mix.')
    parser.add_argument('-w', '--artwork', type=Path, help='The artwork to use for the uploaded mix.')
    parser.add_argument('-t', '--tags', default='', help='A comma-separated list of tags to use for the uploaded mix.')
    parser.add_argument('-p', '--preset', help='A preset from the config to use (can be overridden with --name, --artwork and --tags).')
    parser.add_argument('-y', '--noninteractive', action='store_true', help='Runs noninteractively, i.e. uploads the tracklist as-is.')
    parser.add_argument('-at', '--access-token', help='The access token to use. Will skip browser-based authentication if provided.')
    parser.add_argument('-ci', '--client-id', help='The client id to use.')
    parser.add_argument('-cs', '--client-secret', help='The client secret to use.')
    parser.add_argument('--trim-duration', type=int, default=None, help='Trims to the given duration in seconds.')
    parser.add_argument('--fade-in', type=int, default=None, help='Adds the given fade-in in seconds.')
    parser.add_argument('--fade-out', type=int, default=None, help='Adds the given fade-out in seconds.')

    # Parse CLI args
    args = parser.parse_args()
    recordings_dir = args.recordings_dir
    output_dir = args.output_dir
    noninteractive = args.noninteractive
    config_path = args.config
    auth_path = args.auth
    preset_key = args.preset
    access_token = args.access_token
    client_id = args.client_id
    client_secret = args.client_secret
    name = args.name
    description = args.description
    artwork_path = args.artwork
    tags = [tag.strip() for tag in args.tags.split(',')]
    trim_duration = args.trim_duration
    fade_in = args.fade_in
    fade_out = args.fade_out

    # Read config
    if config_path and config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {}
    
    # Read cached auth
    if auth_path and auth_path.exists():
        with open(auth_path, 'r') as f:
            auth = json.load(f)
    else:
        auth = {}

    # Set defaults from stored config/auth
    raw_recordings_dir = config.get('recordings-dir', str(DEFAULT_RECORDINGS_PATH))
    raw_output_dir = config.get('output-dir', None)
    recordings_dir = recordings_dir or Path(raw_recordings_dir)
    output_dir = output_dir or (Path(raw_output_dir) if raw_output_dir else None)
    access_token = access_token or auth.get('access-token', None)
    client_id = client_id or auth.get('client-id', None)
    client_secret = client_secret or auth.get('client-secret', None)

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
        if auth_path:
            auth['access-token'] = access_token
            with open(auth_path, 'w') as f:
                json.dump(auth, f, indent=2, sort_keys=True)
    
    # Set up API wrapper
    mixcloud = Mixcloud(access_token)

    # Read preset
    if preset_key:
        presets = config.get('presets', {})
        if preset_key not in presets:
            print(f'Preset key {preset_key} not found!')
            sys.exit(1)
        preset = presets.get(preset_key, {})
        name_pattern = preset.get('name', None)
        next_name = find_next_name(name_pattern, mixcloud) if name_pattern else None
        name = name or next_name
        description = description or preset.get('description', None)
        artwork = preset.get('artwork', None)
        artwork_path = artwork_path or (Path(artwork) if artwork else None)
        tags = tags or preset.get('tags', [])
    else:
        next_name = None
    
    # Handle absence of name
    if not name or (not noninteractive and next_name):
        if noninteractive:
            print(f'Please specify a name with --name or use a preset from {config_path}!')
            sys.exit(1)
        
        name = input_with_default('Mix name:', name)
    
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
        output_dir = (output_dir or Path(tmpdir)).expanduser()
        output_path = output_dir / f"transcoded-{recording_path.name.split('.')[0]}.mp3"

        # Ensure that the output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)

        opts = Options(
            recording_path=recording_path.expanduser(),
            tracklist_path=tracklist_path.expanduser(),
            output_path=output_path.expanduser(),
            noninteractive=noninteractive,
            mixcloud=mixcloud,
            name=name,
            description=description,
            artwork_path=artwork_path.expanduser() if artwork_path else None,
            tags=[tag.strip() for tag in tags if tag.strip()],
            trim_duration=trim_duration,
            fade_in=fade_in,
            fade_out=fade_out,
        )
        run(opts)
