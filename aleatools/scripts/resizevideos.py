#!/usr/bin/env python
"""Resizes videos re-encoding using x265

Resizes videos specified with wildcards using the 'ffmpeg' command."""

import glob
import os
import os.path
import argparse
import a107
import shutil
import sys

RED = '\033[0;31m'
PURPLE = '\033[0;35m'
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
NC = '\033[0m' # No Color

# https://stackoverflow.com/questions/11210104/check-if-a-program-exists-from-a-python-script
def is_tool(name):
    """Check whether `name` is on PATH and marked as executable."""

    # from whichcraft import which
    from shutil import which

    return which(name) is not None

def pprint(*args):
    print("{}resizeimages.py{}:".format(PURPLE, NC), *args)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,  formatter_class=a107.SmartFormatter)
    parser.add_argument('-d', '--delete-after', action="store_true", help="Deletes each file after it has been successfully converted")
    parser.add_argument('-o', '--output-directory', default='.', help='Output directory')
    parser.add_argument('files', type=str, help='Files specified with wildcards')
    parser.add_argument('geometry', type=str, help="New geometry, e.g. '720x405', '1024x576' etc.")
    parser.add_argument('prefix', nargs='?', type=str, default='resized-', help='Prefix to be added at the beginning of the output files')

    args = parser.parse_args()

    if not is_tool('ffmpeg'):
        pprint("'ffmpeg' command not found, bye.")
        sys.exit()

    prefix = args.prefix
    # I think this behaviour is not necessary; rather limiting and confusing
    # if not prefix.endswith(("-", "_")):
    #     prefix += "-"
    #     pprint("'-' appended to prefix")

    a = glob.glob(args.files)
    pprint("Number of files: ", len(a))
    for fn in a:
        fno = os.path.join(args.output_directory, prefix+fn)
        pprint("{}Processing file '{}'...{}".format(BLUE, fn, NC))

        line = f"ffmpeg -i {fn} -crf 26 -s:v {args.geometry} {fno}"
        # line = f"ffmpeg -i {fn} -vcodec libx265 -crf 28 -s:v {args.geometry} {fno}"
        pprint(line)
        res = os.system(line)
        # res = 0
        pprint("{}Error {}{}".format(RED, res, NC) if res != 0 else "{}Saved '{}'.{}".format(GREEN, fno, NC))
        if res == 0 and args.delete_after:
            try:
                os.unlink(fn)
            except Exception as e:
                pprint(f"{RED}Error deleting file '{fn}': '{str(e)}'{NC}")
            else:
                pprint(f"{GREEN}File '{fn}' was deleted{NC}")
