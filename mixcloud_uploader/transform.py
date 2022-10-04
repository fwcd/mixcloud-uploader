import re

from dataclasses import replace
from tracklist.model import TrackEntry, Tracklist

def complete_entry(entry: TrackEntry) -> TrackEntry:
    """Attempts to guess the artist from the title if empty."""
    if not entry.artist:
        for pattern in [r'[-–]', r':', r'by']:
            split = re.split(pattern, entry.title, maxsplit=1)
            if len(split) >= 2:
                return replace(
                    entry,
                    artist=split[0].strip(),
                    title=split[1].strip(),
                )
    return entry

def complete_tracklist(tracklist: Tracklist) -> Tracklist:
    """Attempts to guess the artists from the title if empty."""
    return replace(tracklist, entries=[complete_entry(entry) for entry in tracklist.entries])

def trim_tracklist(tracklist: Tracklist, duration: float) -> Tracklist:
    """Truncates the tracklist to the given duration."""
    return replace(tracklist, entries=[entry for entry in tracklist.entries if entry.start_seconds < duration])
