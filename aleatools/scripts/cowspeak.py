#!/usr/bin/env python
import sys
import os

if __name__ == "__main__":
    what = " ".join(sys.argv[1:])

    if len(what) == 0:
        print("What to speak?")

    os.system('cowsay \"{}\"'.format(what))
    os.system('espeak \"{}\"'.format(what))