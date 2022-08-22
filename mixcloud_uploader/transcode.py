import ffmpeg
import ffprobe
import subprocess

from pathlib import Path
from typing import Optional

def get_duration(recording_path: Path) -> float:
    raw = subprocess.run(
        [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(recording_path),
        ],
        capture_output=True,
        encoding='utf8'
    ).stdout
    return float(raw)

def transcode(
    recording_path: Path,
    output_path: Path,
    trim_duration: Optional[float]=None,
    fade_in: Optional[float]=None,
    fade_out: Optional[float]=None,
):
    """Transcodes the raw recording, i.e. compresses the audio."""

    duration = get_duration(recording_path)
    print(f'Duration: {duration}')

    builder = ffmpeg.input(str(recording_path))

    if trim_duration:
        builder = builder.filter('atrim', duration=trim_duration)
    if fade_in:
        builder = builder.filter('afade', type='in', duration=fade_in)
    if fade_out:
        builder = builder.filter('afade', type='out', duration=fade_out, start_time=duration - fade_out)

    builder.output(str(output_path)).run(overwrite_output=True)
