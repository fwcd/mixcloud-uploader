from dataclasses import dataclass
from pathlib import Path
from tkinter import SEPARATOR
from typing import Iterable

@dataclass
class TracklistEntry:
    artist: str = ''
    title: str = ''
    start_seconds: int = 0

def parse_quoted(raw: str) -> str:
    return raw.removeprefix('"').removesuffix('"')

def parse_time(raw: str) -> int:
    seconds = 0
    for segment in raw.split(':'):
        seconds = seconds * 60 + int(segment)
    return seconds

def parse_cuesheet(lines: Iterable[str]) -> Iterable[TracklistEntry]:
    entry = None

    for line in lines:
        split = line.strip().split(' ', maxsplit=1)
        if split:
            if split[0] == 'TRACK':
                if entry:
                    yield entry
                entry = TracklistEntry()
            elif entry:
                if split[0] == 'TITLE':
                    entry.title = parse_quoted(split[1])
                elif split[0] == 'PERFORMER':
                    entry.artist = parse_quoted(split[1])
                elif split[0] == 'INDEX':
                    entry.start_seconds = parse_time(split[1].split(' ')[-1])

    if entry:
        yield entry

def read_cuesheet(path: Path) -> list[TracklistEntry]:
    with open(path, 'r') as f:
        return list(parse_cuesheet(f.readlines()))

DEFAULT_SEPARATOR = ' :: '

def format_tabular(tracks: list[TracklistEntry], separator: str=DEFAULT_SEPARATOR) -> Iterable[str]:
    def sanitize(s: str) -> str:
        return s.replace(separator, ' ')

    for track in tracks:
        yield separator.join([sanitize(track.artist), sanitize(track.title), str(track.start_seconds)])

def write_tabular(tracks: list[TracklistEntry], path: Path):
    with open(path, 'w') as f:
        f.write('\n'.join(format_tabular(tracks)))

def parse_tabular(lines: Iterable[str], separator: str=DEFAULT_SEPARATOR) -> Iterable[TracklistEntry]:
    for line in lines:
        split = line.strip().split(separator)
        if len(split) >= 3:
            yield TracklistEntry(
                artist=split[0],
                title=split[1],
                start_seconds=int(split[2])
            )

def read_tabular(path: Path) -> list[TracklistEntry]:
    with open(path, 'r') as f:
        return list(parse_tabular(f.readlines()))
