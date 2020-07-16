#!/usr/bin/env python
"""Copies all files in directory with new names starting with a datestamp"""

import glob
import os
import os.path
import argparse
import a107
import shutil
import sys
import re

def get_stamp(filename):
    return a107.dt2stamp(a107.ts2dt(os.stat(filename).st_mtime))

def main():
    ff = glob.glob("*")
    if len(ff) == 0:
        print("No files in directory")
        sys.exit()

    stamplen = len(get_stamp(ff[0]))
    retoexclude = re.compile(f"\d{{{stamplen}}}")

    maxlen = max([len(f) for f in ff])
    map = [(x, f"{get_stamp(x)}-{x}") for x in ff if retoexclude.match(x) is None]

    for f, newf in map:
        print(f"{f:{maxlen}} --> {newf}")

    if not a107.yesno(f"Will copy {len(ff)} files as shown above. Continue", False):
        sys.exit()

    for f, newf in map:
        print(f"{f}...")
        shutil.copy(f, newf)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,  formatter_class=a107.SmartFormatter)
    args = parser.parse_args()
    main()
