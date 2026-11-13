"""Select a photo timestamp without inferring missing capture-time information."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re

from PIL import ExifTags


@dataclass(frozen=True)
class CaptureTime:
    value: datetime
    source: str


def parse_timestamp(value):
    """Parse an explicit ISO timestamp; a date alone must not invent midnight."""
    if 'T' not in value and ' ' not in value:
        raise ValueError('include a time, e.g. 1985-10-26T01:21:00')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('use an ISO timestamp, e.g. 1985-10-26T01:21:00') from exc


def _text(value):
    if isinstance(value, bytes):
        value = value.decode('ascii')
    return str(value).rstrip('\x00').strip()


def capture_time(exif, override=None, shift=0):
    if override is not None:
        selected = CaptureTime(override, 'explicit --timestamp')
    else:
        # Standard EXIF stores capture fields in the Exif IFD. Some writers put
        # them in IFD0 instead; consult that only when the nested field is absent.
        nested = exif.get_ifd(ExifTags.IFD.Exif) if ExifTags.IFD.Exif in exif else {}

        def read(tag):
            return nested.get(tag, exif.get(tag))

        raw = read(ExifTags.Base.DateTimeOriginal)
        if raw is None:
            raise ValueError('missing DateTimeOriginal; use --timestamp for an explicit date/time')
        try:
            value = datetime.strptime(_text(raw), '%Y:%m:%d %H:%M:%S')
        except (ValueError, UnicodeError) as exc:
            raise ValueError(f'invalid DateTimeOriginal: {raw!r}') from exc
        subseconds = read(ExifTags.Base.SubsecTimeOriginal)
        if subseconds is not None:
            digits = _text(subseconds)
            if not re.fullmatch(r'[0-9]+', digits):
                raise ValueError(f'invalid SubsecTimeOriginal: {subseconds!r}')
            value = value.replace(microsecond=int((digits + '000000')[:6]))
        offset = read(ExifTags.Base.OffsetTimeOriginal)
        if offset is not None:
            offset = _text(offset)
            if not re.fullmatch(r'[+-][0-9]{2}:[0-9]{2}', offset):
                raise ValueError(f'invalid OffsetTimeOriginal: {offset!r}')
            hours, minutes = map(int, offset[1:].split(':'))
            if hours > 23 or minutes > 59:
                raise ValueError(f'invalid OffsetTimeOriginal: {offset!r}')
            delta = timedelta(hours=hours, minutes=minutes)
            value = value.replace(tzinfo=timezone(-delta if offset[0] == '-' else delta))
        selected = CaptureTime(value, 'EXIF DateTimeOriginal')
    if shift:
        return CaptureTime(selected.value + timedelta(seconds=shift), f'{selected.source}; shifted {shift:+g}s')
    return selected
