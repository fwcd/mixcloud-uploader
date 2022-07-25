from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

@dataclass
class TracklistEntry:
    title: str = ''
    artist: str = ''
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
    with open(path) as f:
        return list(parse_cuesheet(f.readlines()))
