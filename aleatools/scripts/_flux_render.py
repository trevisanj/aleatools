"""One scalable renderer for the flux capacitor drawing and date display."""

from dataclasses import dataclass, replace
import math

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont

from _flux_style import POSITIONS


MONTHS = ('JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC')

# Letters use split center segments; digits use one continuous center bar.
# All glyphs share the same segment drawing and need no installed font.
SEGMENTS = {
    'a': ((5, 0), (31, 0)), 'b': ((36, 5), (36, 27)),
    'c': ((36, 37), (36, 59)), 'd': ((5, 64), (31, 64)),
    'e': ((0, 37), (0, 59)), 'f': ((0, 5), (0, 27)),
    'g': ((5, 32), (15, 32)), 'n': ((21, 32), (31, 32)),
    'h': ((5, 6), (14, 25)), 'i': ((18, 5), (18, 26)),
    'j': ((31, 6), (22, 25)), 'k': ((14, 39), (5, 58)),
    'l': ((18, 38), (18, 59)), 'm': ((22, 39), (31, 58)),
    'o': ((5, 32), (31, 32)), '/': ((5, 64), (31, 0)),
}
GLYPHS = {
    '0': 'abcdef', '1': 'bc', '2': 'abedo', '3': 'abcdo',
    '4': 'fbco', '5': 'afcdo', '6': 'afcdeo', '7': 'abc',
    '8': 'abcdefo', '9': 'abcdfo',
    'A': 'abcefgn', 'B': 'abcdnil', 'C': 'adef', 'D': 'abcdil',
    'E': 'adefgn', 'F': 'aefgn', 'G': 'acdefn', 'H': 'bcefgn',
    'I': 'adil', 'J': 'bcde', 'K': 'efgjm', 'L': 'def',
    'M': 'bcefhj', 'N': 'bcefhm', 'O': 'abcdef', 'P': 'abefgn',
    'R': 'abefgnm', 'S': 'acdfgn', 'T': 'ail', 'U': 'bcdef',
    'V': 'efkj', 'Y': 'hjl',
    '/': '/',
}
BODY_HEIGHT = 100
GLYPH_WIDTH = max(point[0] for endpoints in SEGMENTS.values() for point in endpoints)
SEGMENT_WIDTH = 7.2
CHAR_GAP = 15
CHAR_ADVANCE = GLYPH_WIDTH + CHAR_GAP
DATE_FIELD_GAP = 48
TIME_FIELD_GAP = 19


@dataclass(frozen=True)
class DisplayField:
    text: str
    label: str = ''
    gap_before: float = 0


@dataclass(frozen=True)
class StampLayout:
    fields: tuple
    padding: int
    display_width: float
    display_x: float
    logical_size: tuple
    pixel_size: tuple
    origin: tuple


def display_fields(timestamp, style):
    date = {
        'm': DisplayField(f'{timestamp.month:02}' if style.date_order == 'ymd' else MONTHS[timestamp.month - 1], 'MONTH'),
        'd': DisplayField(f'{timestamp.day:02}', 'DAY'),
        'y': DisplayField(f'{timestamp.year:04}', 'YEAR'),
    }
    result = []
    for index, key in enumerate(style.date_order):
        gap = DATE_FIELD_GAP if index else 0
        if index and style.date_separator == 'slash':
            gap = (DATE_FIELD_GAP - text_width('/')) / 2
            result.append(DisplayField('/', gap_before=gap))
        result.append(replace(date[key], gap_before=gap))
    if not style.date_only:
        hour = timestamp.hour if style.clock == '24' else timestamp.hour % 12 or 12
        result.extend((DisplayField(f'{hour:02}', 'HOUR', 2 * DATE_FIELD_GAP),
                       DisplayField(':', gap_before=TIME_FIELD_GAP),
                       DisplayField(f'{timestamp.minute:02}', 'MIN', TIME_FIELD_GAP)))
        if style.seconds:
            result.extend((DisplayField(':', gap_before=TIME_FIELD_GAP),
                           DisplayField(f'{timestamp.second:02}', 'SEC', TIME_FIELD_GAP)))
        if style.clock == '12':
            result.append(DisplayField('AM' if timestamp.hour < 12 else 'PM', gap_before=TIME_FIELD_GAP))
    return tuple(result)


def text_width(text):
    return 15 if text == ':' else len(text) * CHAR_ADVANCE - CHAR_GAP


def layout_stamp(photo_size, timestamp, style):
    style.validate()
    reference = min(photo_size)
    height = max(1, round(style.size.pixels(reference)))
    if height < 16:
        raise ValueError('stamp is too small to render; use --size 16px or larger')
    margin = math.ceil(style.margin.pixels(reference))
    fields = display_fields(timestamp, style)
    padding = math.ceil(style.outline_width * 1.4 + (8 if style.glow else 2))
    display_width = sum(text_width(item.text) + item.gap_before for item in fields) + 20
    display_x = padding + (94 if style.flux else 0)
    logical_size = (display_x + display_width + padding, BODY_HEIGHT + 2 * padding)
    width = math.ceil(logical_size[0] * height / logical_size[1])
    if width + 2 * margin > photo_size[0] or height + 2 * margin > photo_size[1]:
        raise ValueError(f'stamp ({width}x{height}) does not fit inside margins; reduce --size or --margin')
    anchor_x, anchor_y = POSITIONS[style.position]
    origin = (round(margin + anchor_x * (photo_size[0] - 2 * margin - width)),
              round(margin + anchor_y * (photo_size[1] - 2 * margin - height)))
    return StampLayout(fields, padding, display_width, display_x, logical_size, (width, height), origin)


def _segment(draw, start, end, width, scale):
    dx, dy = end[0] - start[0], end[1] - start[1]
    distance = math.hypot(dx, dy)
    ux, uy = dx / distance, dy / distance
    nx, ny = -uy * width / 2, ux * width / 2
    bevel = min(width / 2, distance / 3)
    points = [start, (start[0] + ux * bevel + nx, start[1] + uy * bevel + ny),
              (end[0] - ux * bevel + nx, end[1] - uy * bevel + ny), end,
              (end[0] - ux * bevel - nx, end[1] - uy * bevel - ny),
              (start[0] + ux * bevel - nx, start[1] + uy * bevel - ny)]
    draw.polygon([(round(x * scale), round(y * scale)) for x, y in points], fill=255)


def _display(mask, layout, style, scale):
    draw = ImageDraw.Draw(mask)
    x = layout.display_x + 10
    y = layout.padding + (29 if style.labels else 18)
    glyph_scale = 0.88 if style.labels else 1
    font = ImageFont.load_default(size=max(1, round(9 * scale)))
    for item in layout.fields:
        x += item.gap_before
        width = text_width(item.text)
        if style.labels and item.label:
            draw.text(((x + width / 2) * scale, (layout.padding + 9) * scale),
                      item.label, font=font, anchor='mt', fill=255)
        if item.text == ':':
            for dy in (21, 45):
                cx, cy = (x + 7) * scale, (y + dy * glyph_scale) * scale
                radius = SEGMENT_WIDTH * 0.45 * glyph_scale * scale
                draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=255)
        else:
            inset = width * (1 - glyph_scale) / 2
            for index, char in enumerate(item.text):
                for segment in GLYPHS[char]:
                    start, end = SEGMENTS[segment]
                    start = (x + inset + (index * CHAR_ADVANCE + start[0]) * glyph_scale, y + start[1] * glyph_scale)
                    end = (x + inset + (index * CHAR_ADVANCE + end[0]) * glyph_scale, y + end[1] * glyph_scale)
                    _segment(draw, start, end, SEGMENT_WIDTH * glyph_scale, scale)
        x += width


def _capacitor(mask, layout, scale):
    """Draw all capacitor details into the display's shared illumination mask."""
    draw = ImageDraw.Draw(mask)
    ox, oy = layout.padding, layout.padding

    def box(bounds):
        x0, y0, x1, y1 = bounds
        return tuple(round(v * scale) for v in (ox + x0, oy + y0, ox + x1, oy + y1))

    def line(points, width):
        draw.line([(round((ox + x) * scale), round((oy + y) * scale)) for x, y in points],
                  fill=255, width=max(1, round(width * scale)), joint='curve')

    draw.rounded_rectangle(box((0, 0, 80, 100)), radius=9 * scale, outline=255, width=max(1, round(2.5 * scale)))
    for bounds in ((11, 15, 34, 48), (46, 15, 69, 48), (27, 59, 53, 90)):
        draw.arc(box(bounds), 0, 315, fill=255, width=max(1, round(2.2 * scale)))
    tubes = (((21, 25), (24, 35), (40, 54)), ((59, 25), (56, 35), (40, 54)), ((40, 79), (40, 65), (40, 54)))
    for points in tubes:
        line(points, 4)
    for x, y in ((21, 25), (59, 25), (40, 79)):
        draw.ellipse(box((x - 4, y - 4, x + 4, y + 4)), fill=255)
    draw.ellipse(box((37, 51, 43, 57)), fill=255)
    for x, y in ((4, 4), (76, 4), (4, 96), (76, 96)):
        draw.ellipse(box((x - 1.5, y - 1.5, x + 1.5, y + 1.5)), fill=255)


def _paint(base, mask, fill, strength=1):
    if strength != 1:
        mask = mask.point(lambda alpha: round(alpha * strength))
    layer = Image.new('RGBA', base.size, ImageColor.getrgb(fill) + (0,))
    layer.putalpha(mask)
    base.alpha_composite(layer)


def render_stamp(layout, style):
    # Draw at least twice the output resolution; only the stamp is supersampled.
    scale = max(2, 2 * layout.pixel_size[1] / layout.logical_size[1])
    canvas_size = tuple(math.ceil(dimension * scale) for dimension in layout.logical_size)
    base = Image.new('RGBA', canvas_size)
    mask = Image.new('L', canvas_size)
    if style.panel:
        draw = ImageDraw.Draw(base)
        x, y = layout.display_x, layout.padding
        fill = ImageColor.getrgb(style.panel_color) + (round(255 * style.panel_opacity),)
        draw.rounded_rectangle((x * scale, y * scale, (x + layout.display_width) * scale, (y + BODY_HEIGHT) * scale),
                               radius=5 * scale, fill=fill)
    if style.flux:
        _capacitor(mask, layout, scale)
    _display(mask, layout, style, scale)
    if style.glow:
        _paint(base, mask.filter(ImageFilter.GaussianBlur(2 * scale)), style.color, style.glow)
    if style.outline_width:
        radius = round(style.outline_width * layout.logical_size[1] / 100 * scale)
        if radius:
            _paint(base, mask.filter(ImageFilter.MaxFilter(2 * radius + 1)), style.outline_color)
    _paint(base, mask, style.color)
    base = base.resize(layout.pixel_size, Image.Resampling.LANCZOS)
    if style.opacity != 1:
        base.putalpha(base.getchannel('A').point(lambda alpha: round(alpha * style.opacity)))
    return base


def stamp_photo(photo, timestamp, style):
    layout = layout_stamp(photo.size, timestamp, style)
    result = photo.convert('RGBA')
    result.alpha_composite(render_stamp(layout, style), layout.origin)
    return result
