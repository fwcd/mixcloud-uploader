from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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
    # The name for the uplaoded mix.
    name: str
    # The path to the artwork.
    artwork_path: Optional[Path]
    # The tags for the mix.
    tags: list[str]
