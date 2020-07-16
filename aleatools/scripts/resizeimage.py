#!/usr/bin/env python

"""
This is a very specific script to resize image to 64x64 pixels. I don't remember what was the initial goal.

Taken from
http://stackoverflow.com/questions/14634014/resizing-png-image-with-pil-loses-transparency
"""

import sys
from PIL import Image

img = Image.open(sys.argv[1])
pal = img.getpalette()
width, height = img.size
actual_transp = img.info['actual_transparency'] # XXX This will fail.

result = Image.new('LA', img.size)

im = img.load()
res = result.load()
for x in range(width):
    for y in range(height):
        t = actual_transp[im[x, y]]
        color = pal[im[x, y]]
        res[x, y] = (color, t)

result.resize((64, 64), Image.ANTIALIAS).save(sys.argv[2])
