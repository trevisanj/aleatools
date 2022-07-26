#!/usr/bin/env python
"""Converts accents in HTML file to "ampesand" entities.

Output files are saved as "<input filename>.amp", e.g.,
 "index.html" --> "index.html.amp".

List of input filenames (wildcards allowed) will be glob'ed and
duplicates will be removed.

Files ending with "amp" will be skipped as they will be considered
outputs of a previous run.
"""

import glob
import argparse
import sys
import os
import a107
import time
import html.entities
import aleatools

TABLE = {k: '&{};'.format(v) for k, v in html.entities.codepoint2name.items()}


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

class WftError(Exception):
    pass

def to_amp(s):
    """Convert bytes_ encoding from <from_> encoding to <to> encoding."""

    buffer = ""
    n = len(s)
    i = 0
    in_tag = False
    ret = ""
    try:
        while True:
            is_end = i == n
            if not is_end:
                ch = s[i]

            if not is_end and ch == ">":
                if in_tag:
                    in_tag = False
                    ret += ch
                else:
                    raise WftError("Closing tag but no tag open")

            elif is_end or ch == "<":
                if in_tag:
                    raise WftError("Opening tag but already open")
                else:
                    if buffer:
                        ret += buffer.translate(TABLE)
                        buffer = ""
                    in_tag = True
                    if not is_end:
                        ret += ch

            elif not is_end:
                if in_tag:
                    ret += ch
                else:
                    buffer += ch

            if is_end:
                break
                
            i += 1

    except WftError as e:
        raise ValueError(f"In position {i}: {str(e)}")

    return ret


def get_filenames(patterns):
    """Compile list of file names.

    Each item in patterns list may have wildcards, and these will be expanded
    into actual filenames, then duplicates will be removed."""

    _ff = []
    for pattern in patterns:
        _ff.extend(glob.glob(pattern))
    ff = []
    for f in _ff:
        if f not in ff and not f.endswith("amp"):
            ff.append(f)

    return ff


def write0(s):
    sys.stdout.write("[ampesandme] {}".format(s))
    sys.stdout.flush()

def write1(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def do_it(filenames):
    for fn in filenames:
        write0("'{}' ...".format(fn))
        try:
            with open(fn, 'r') as f:
                contents = f.read()
                bytes_out = to_amp(contents)
                fn_out = "{}.amp".format(fn)
                with open(fn_out, "w") as g:
                    g.write(bytes_out)
                    write1("\b\b\b--> '{}' OK =D\n".format(fn_out))

        except Exception as e:
            write1("Oops :( {} ):\n".format(str(e)))
            a107.get_python_logger().exception("Error recoding file '{}'".format(fn))


if __name__ == "__main__":
    print(aleatools.asciilogo())
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument('inputs', type=str, nargs='+',
     help='input filenames (wildcards allowed)')

    args = parser.parse_args()

    filenames = get_filenames(args.inputs)

    wormsay0("hi")

    write0("\n")
    write0("{} file{} to process.\n".format(len(filenames), "" if len(filenames) == 1 else "s"))
    write0("\n")

    args_ = vars(args)
    do_it(filenames)

    line = "bye"
    wormsay1(line)
