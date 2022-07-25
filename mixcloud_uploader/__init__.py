import argparse
import sys

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional

from mixcloud_uploader.options import Options
from mixcloud_uploader.transcode import transcode

def find_latest_recording(recordings_dir: Path) -> tuple[Optional[Path], Optional[Path]]:
    sorted_files = sorted(recordings_dir.iterdir(), key=lambda f: f.name, reverse=True)
    for wav_path, cue_path in zip(sorted_files, sorted_files[1:]):
        print(wav_path, cue_path)
        if wav_path.name.endswith('.wav') and cue_path.name.endswith('.cue'):
            return wav_path, cue_path
    return None, None

def main():
    parser = argparse.ArgumentParser(description='CLI tool for uploading Mixxx recordings to Mixcloud')
    parser.add_argument('-d', '--recordings-dir', default=str(Path.home() / 'Music' / 'Mixxx' / 'Recordings'), help='The recordings directory to use.')
    parser.add_argument('-r', '--recording-name', help='The name of the recording (which should have a corresponding .cue and .wav file). Defaults to the latest.')
    parser.add_argument('-o', '--output-dir', help='The path to the output directory. Defaults to a temporary directory.')
    parser.add_argument('-n', '--name', required=True, help='The name of the mix.')

    args = parser.parse_args()
    recordings_dir = Path(args.recordings_dir)

    if args.recording_name:
        # Use the specified recording
        recording_path = recordings_dir / f'{args.recording_name}.wav'
        tracklist_path = recordings_dir / f'{args.recording_name}.cue'
    else:
        # Default to latest recording
        recording_path, tracklist_path = find_latest_recording(recordings_dir)

    if not recording_path or not tracklist_path:
        print('No recording found!')
        sys.exit(1)
    elif not recording_path.exists():
        print(f'{recording_path} does not exist!')
        sys.exit(1)
    elif not tracklist_path.exists():
        print(f'{tracklist_path} does not exist!')
        sys.exit(1)
    
    with NamedTemporaryFile(prefix='transcoded-', suffix='.mp3', dir=args.output_dir) as output_file:
        output_path = Path(output_file.name)

        opts = Options(
            recording_path=recording_path,
            tracklist_path=tracklist_path,
            output_path=output_path
        )

        print(f'==> Transcoding {recording_path} to {output_path}...')
        transcode(opts)

        # TODO
