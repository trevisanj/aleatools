#!/usr/bin/env python
"""Convert files from one encoding into another.

Output files are saved as "<input filename>.<encoding>", e.g.,
 "text.txt" --> "text.txt.windows-1252".

List of input filenames (wildcards allowed) will be glob'ed and
duplicates will be removed.

Files ending with <to> will be skipped as they will be considered
outputs of a previous run.

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
    parser.add_argument('-f', '--from', type=str, default=DEFAULT_FROM, required=False,
        help='encoding (supposed) of input file(s)', )
    parser.add_argument('-t', '--to', default=DEFAULT_TO, required=False, type=str,
        help='output encoding', )
    parser.add_argument('inputs', type=str, nargs='+',
     help='input filenames (wildcards allowed)')

    args = parser.parse_args()

    filenames = get_filenames(args.inputs, args.to)

    wormsay0("hi")

    write0("\n")
    write0("{} file{} to process.\n".format(len(filenames), "" if len(filenames) == 1 else "s"))
    write0("\n")

    args_ = vars(args)
    do_it(filenames, args_["from"], args_["to"])

    line = "bye"
    wormsay1(line)
