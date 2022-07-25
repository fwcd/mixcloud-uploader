import ffmpeg

from pathlib import Path

def transcode(recording_path: Path, output_path: Path):
    """Transcodes the raw recording, i.e. compresses the audio."""

    ffmpeg.input(str(recording_path)).output(str(output_path)).run(overwrite_output=True)
