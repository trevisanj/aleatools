#!/usr/bin/env python3
import os, sys, argparse, a107

SIMULATION = False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please specify a commit message as one or more command-line arguments.")
        sys.exit()
    msg = " ".join(sys.argv[1:])
    print(f"Commit message: {msg}")
    f = print if SIMULATION else os.system
    f("git add . --all")
    f("git commit -m \"{}\"".format(msg))
    f("git push")
