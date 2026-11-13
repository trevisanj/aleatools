"""Appearance definitions and value parsing for the flux capacitor stamp."""

from dataclasses import dataclass, field
import math

from PIL import ImageColor


@dataclass(frozen=True)
class Length:
    value: float
    relative: bool = False

    def pixels(self, reference):
        return self.value * reference / 100 if self.relative else self.value

    def __str__(self):
        return f"{self.value:g}{'%' if self.relative else 'px'}"


def length(value):
    """Percentages use the oriented photo's shorter edge; bare numbers are pixels."""
    if isinstance(value, Length):
        return value
    text = value.strip()
    relative = text.endswith('%')
    number = text[:-1] if relative else text.removesuffix('px')
    result = nonnegative(number)
    return Length(result, relative)


def nonnegative(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError('must be a finite, nonnegative number')
    return number


def unit_interval(value):
    number = nonnegative(value)
    if number > 1:
        raise ValueError('must be between 0 and 1')
    return number


def parse_color(value):
    try:
        ImageColor.getrgb(value)
    except (ValueError, TypeError) as exc:
        raise ValueError('use a color name or hex color, e.g. #55ff99') from exc
    if len(ImageColor.getrgb(value)) != 3:
        raise ValueError('use an RGB color; set transparency with --opacity')
    return value


def option(default, help_text, converter=None, choices=None, boolean=False):
    return field(default=default, metadata={
        'help': help_text, 'type': converter, 'choices': choices, 'boolean': boolean,
    })


# Factors are alignment fractions of the free space inside the margins.
POSITIONS = {
    'top-left': (0, 0), 'top-center': (0.5, 0), 'top-right': (1, 0),
    'center-left': (0, 0.5), 'center': (0.5, 0.5), 'center-right': (1, 0.5),
    'bottom-left': (0, 1), 'bottom-center': (0.5, 1), 'bottom-right': (1, 1),
}


@dataclass(frozen=True)
class StampStyle:
    size: Length = option(Length(6, True), 'Complete stamp height, including glow: pixels or % of shorter edge', length)
    margin: Length = option(Length(2, True), 'Inset from photo edges: pixels or % of shorter edge', length)
    position: str = option('bottom-right', 'Stamp anchor', choices=tuple(POSITIONS))
    color: str = option('#ffdd33', 'Shared display and capacitor color', parse_color)
    outline_color: str = option('#101918', 'Outline color', parse_color)
    outline_width: float = option(3, 'Outline width as % of stamp height', nonnegative)
    glow: float = option(1, 'Glow strength, 0 to 1; 0 disables glow', unit_interval)
    opacity: float = option(1.0, 'Overall stamp opacity, 0 to 1', unit_interval)
    flux: bool = option(False, 'Show the flux capacitor drawing', boolean=True)
    labels: bool = option(False, 'Show MONTH, DAY, YEAR, HOUR and MIN labels', boolean=True)
    panel: bool = option(False, 'Draw a dark panel behind the display', boolean=True)
    panel_color: str = option('#101918', 'Display panel color', parse_color)
    panel_opacity: float = option(0.8, 'Display panel opacity, 0 to 1', unit_interval)
    date_order: str = option('dmy', 'Date order; ymd uses a numeric month', choices=('mdy', 'dmy', 'ymd'))
    date_separator: str = option('space', 'Separate date fields with a segmented slash or space; date/time gap is twice as wide', choices=('slash', 'space'))
    clock: str = option('24', 'Clock format', choices=('12', '24'))
    seconds: bool = option(False, 'Show seconds', boolean=True)
    date_only: bool = option(False, 'Hide the time', boolean=True)

    def validate(self):
        if self.size.value <= 0:
            raise ValueError('--size must be greater than zero')
        if self.outline_width > 5:
            raise ValueError('--outline-width must be at most 5% of stamp height')
