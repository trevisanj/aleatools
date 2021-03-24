#!/usr/bin/env python
"""
Pastes images side-by-side, then chops to match 'aspectratio', saving each chop sequentially.

Images are pre-resized to match height of smallest.

"""

import glob
import argparse
import sys
import os
import a107
import anguishlib
from PIL import Image


def wormsay0(line):
    myprint("")
    myprint("     ^o^ --- {}".format(line))
    myprint("     .")
    myprint("   ..")
    myprint("")


def wormsay1(line):
    myprint("")
    myprint("  ^o^ --- {}".format(line))
    myprint("    .")
    myprint("     ..")
    myprint("")


def myprint(s):
    print("📷 {}".format(s))



# # Old single-file version
# def main(args):
#     img = Image.open(args.input)
#     imgs = anguishlib.split_for_instagram(img, args.aspectratio)
#     name, ext = os.path.splitext(args.input)
#     print(name, "----------------------------------", ext)
#     for img_ in imgs:
#         fn = a107.sequential_filename(name, ext)
#         img_.save(fn)
#         print(a107.format_yoda(f"'{fn}' saved it was."))
#     line = "bye"
#     wormsay1(line)


def main(args):
    filenames = glob.glob(args.input)
    filenames.sort()
    n = len(filenames)
    myprint(f"Number of files: {n}")

    images = [Image.open(filename) for filename in filenames]
    minheight = min([image.size[1] for image in images])
    flag_resize = any([image.size[1] != minheight for image in images])

    if flag_resize:
        for i in range(n):
            image = images[i]
            if image.size[1] != minheight:
                images[i] = anguishlib.resize_image(image, height=minheight)
                myprint(f"Resized image from '{image.filename}'")

    totalwidth = sum([image.size[0] for image in images])

    img = Image.new("RGB", (totalwidth, minheight), (0,0,0))
    x = 0
    for image in images:
        img.paste(image, (x, 0))
        x += image.size[0]

    imgs = anguishlib.split_for_instagram(img, args.aspectratio)
    name, ext = os.path.splitext(filenames[0])
    for img_ in imgs:
        fn = a107.sequential_filename(name, ext)
        img_.save(fn)
        myprint(a107.format_yoda(f"'{fn}' saved it was."))
    line = "bye"
    wormsay1(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument('-r', '--aspectratio', type=float, default=0.8, required=False,
                        help='Aspect ratio of each resulting image', )
    parser.add_argument('input', type=str, help='input filenames (wildcards allowed)')

    args = parser.parse_args()

    wormsay0("hi")
    main(args)
