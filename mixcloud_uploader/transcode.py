import ffmpeg

from mixcloud_uploader.options import Options

def transcode(opts: Options):
    """Transcodes the raw recording, i.e. compresses the audio."""

    ffmpeg.input(str(opts.recording_path)).output(str(opts.output_path)).run(overwrite_output=True)
