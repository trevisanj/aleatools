#!/usr/bin/env python
"""
Converts text to PNG image

Creates specially to convert ASCII monospace diagrams to PNG image

Based on gist: https://gist.github.com/destan/5540702
"""

from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw
import argparse
import sys
import os


def text2png(lines, fullpath, color ="#000", bgcolor ="#FFF", fontfullpath = None, fontsize = 13,
             padding = 3, box=False, boxcolor="#008080", boxwidth=3):
    # REPLACEMENT_CHARACTER = u'\uFFFD'
    # NEWLINE_REPLACEMENT_STRING = ' ' + REPLACEMENT_CHARACTER + ' '

    font = ImageFont.load_default() if fontfullpath is None else ImageFont.truetype(fontfullpath, fontsize)

    # #prepare linkback
    # linkback = "created via http://ourdomain.com"
    # fontlinkback = ImageFont.truetype('font.ttf', 8)
    # linkbackx = fontlinkback.getsize(linkback)[0]
    # linkback_height = fontlinkback.getsize(linkback)[1]
    # #end of linkback


    line_height = font.getsize(lines[0])[1]
    img_height = line_height * len(lines) + 2*padding + (0 if not box else 2*boxwidth)
    img_width = max([font.getsize(x)[0] for x in lines])+2*padding + (0 if not box else 2*boxwidth)

    img = Image.new("RGBA", (img_width, img_height), bgcolor)
    draw = ImageDraw.Draw(img)

    y = padding + (0 if not box else boxwidth)
    for line in lines:
        draw.text( (padding + (0 if not box else boxwidth), y), line, color, font=font)
        y += line_height

    if box:
        for i in range(boxwidth):
            draw.rectangle((i, i, img_width-i-1, img_height-i-1), None, boxcolor)

    # # add linkback at the bottom
    # draw.text( (width - linkbackx, img_height - linkback_height), linkback, color, font=fontlinkback)

    img.save(fullpath)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert text file to PNG')
    parser.add_argument('-f', type=str, help='Font filename (e.g. "FreeMono.ttf"). See PIL docs for how PIL finds the font filename', required=False)
    parser.add_argument('-s', type=int, default=12, help='Font size (default: 12). Ignored if no font filename is specified', required=False)
    parser.add_argument('-p', type=int, default=4, help='Padding (default: 4)', required=False)
    parser.add_argument('-b', action="store_true", help="Draws box around")
    parser.add_argument('input', type=str, nargs=1, help='Input filename')
    parser.add_argument('output', type=str, default="(automatic)", nargs="?", help='Output filename')

    args = parser.parse_args()

    fn_input = args.input[0]

    fn_output = args.output
    if fn_output == "(automatic)":
        fn_output = os.path.splitext(fn_input)[0]+".png"

    print("Output filename: {}".format(fn_output))

    with open(fn_input, "r") as file:
        lines = file.readlines()

    lines = [x.replace("\n", "") for x in lines]

    # sys.exit()

    text2png(lines, fn_output, fontfullpath=args.f, fontsize=args.s, padding=args.p, box=args.b)
