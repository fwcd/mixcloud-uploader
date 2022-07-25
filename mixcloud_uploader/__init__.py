import argparse
import os
import subprocess
import sys

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from mixcloud_uploader.options import Options
from mixcloud_uploader.tracklist import read_cuesheet, read_tabular, write_tabular
from mixcloud_uploader.transcode import transcode

def find_latest_recording(recordings_dir: Path) -> tuple[Optional[Path], Optional[Path]]:
    sorted_files = sorted(recordings_dir.iterdir(), key=lambda f: f.name, reverse=True)
    for wav_path, cue_path in zip(sorted_files, sorted_files[1:]):
        if wav_path.name.endswith('.wav') and cue_path.name.endswith('.cue'):
            return wav_path, cue_path
    return None, None

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
            tracks = read_tabular(path)
    
    for track in tracks:
        print(track)

def main():
    parser = argparse.ArgumentParser(description='CLI tool for uploading Mixxx recordings to Mixcloud')
    parser.add_argument('-d', '--recordings-dir', default=str(Path.home() / 'Music' / 'Mixxx' / 'Recordings'), help='The recordings directory to use.')
    parser.add_argument('-r', '--recording-name', help='The name of the recording (which should have a corresponding .cue and .wav file). Defaults to the latest.')
    parser.add_argument('-o', '--output-dir', help='The path to the output directory. Defaults to a temporary directory.')
    parser.add_argument('-n', '--name', required=True, help='The name of the mix.')
    parser.add_argument('-y', '--noninteractive', action='store_true', help='Runs noninteractively, i.e. uploads the tracklist as-is.')

    # Parse CLI args
    args = parser.parse_args()
    recordings_dir = Path(args.recordings_dir)
    output_dir = Path(args.output_dir) if args.output_dir else None
    noninteractive = args.noninteractive
    name = args.name

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
    
    if output_dir:
        # Use the specified output directory with a deterministic name
        # to allow caching the transcoded audio file.
        output_path = output_dir / f"transcoded-{recording_path.name.split('.')[0]}.mp3"
        opts = Options(
            recording_path=recording_path,
            tracklist_path=tracklist_path,
            output_path=output_path,
            noninteractive=noninteractive,
            name=name
        )
        run(opts)
    else:
        # Use a temporary file for the transcoded audio file.
        with NamedTemporaryFile(prefix='transcoded-', suffix='.mp3') as tmpfile:
            opts = Options(
                recording_path=recording_path,
                tracklist_path=tracklist_path,
                output_path=Path(tmpfile.name),
                noninteractive=noninteractive,
                name=name
            )
            run(opts)
