#!/usr/bin/env python
"""Convert files from one encoding into another.

Output files are saved as "<input filename>-<nnnn>.<exension>", e.g.,
"horseshit-0000.png".

"""

import glob
import argparse
import sys
import os
import a107
import time

DEFAULT_FROM = "utf-8"
DEFAULT_TO = "windows-1252"


def wormsay0(line):
    write0("\n")
    write0("     ^o^ --- {}\n".format(line))
    write0("     .\n")
    write0("   ..\n")
    write0("\n")


def wormsay1(line):
    write0("\n")
    write0("  ^o^ --- {}\n".format(line))
    write0("    .\n")
    write0("     ..\n")
    write0("\n")


def recode(bytes_, from_=DEFAULT_FROM, to=DEFAULT_TO):
    """Convert bytes_ encoding from <from_> encoding to <to> encoding."""

    return bytes_.decode(from_, "replace").encode(to, "replace")


def get_filenames(patterns, to):
    """Compile list of file names.

    Each item in patterns list may have wildcards, and these will be expanded
    into actual filenames, then duplicates will be removed."""

    _ff = []
    for pattern in patterns:
        _ff.extend(glob.glob(pattern))
    ff = []
    for f in _ff:
        if f not in ff and not f.endswith(to):
            ff.append(f)

    return ff


def write0(s):
    sys.stdout.write("[recode] {}".format(s))
    sys.stdout.flush()


def write1(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def do_it(filenames, from_, to):
    for fn in filenames:
        write0("'{}' ...".format(fn))
        try:
            with open(fn, 'rb') as f:
                bytes_ = f.read()
                bytes_out = recode(bytes_, from_, to)
                fn_out = "{}.{}".format(fn, to)
                with open(fn_out, "wb") as g:
                    g.write(bytes_out)
                    write1("\b\b\b--> '{}' OK =D\n".format(fn_out))

        except Exception as e:
            write1("Oops :( {} ):\n".format(str(e)))
            a107.get_python_logger().exception("Error recoding file '{}'".format(fn))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument('-r', '--aspectratio', type=float, default=0.8, required=False,
                        help='Aspect ratio of each resulting image', )
    parser.add_argument('input', type=str, help='input filenames (wildcards allowed)')

    args = parser.parse_args()

    wormsay0("hi")

    import anguishlib
    from PIL import Image

    img = Image.open(args.input)
    imgs = anguishlib.split_for_instagram(img, args.aspectratio)
    name, ext = os.path.splitext(args.input)
    print(name, "----------------------------------", ext)
    for img_ in imgs:
        fn = a107.sequential_filename(name, ext)
        img_.save(fn)
        print(a107.format_yoda(f"'{fn}' saved it was."))

    line = "bye"
    wormsay1(line)
