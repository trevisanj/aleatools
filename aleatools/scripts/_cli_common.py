"""Shared console helpers for aleatools scripts."""

import sys


class ConsoleHelper(object):
    def __init__(self, script_name):
        self.script_name = script_name

    def write0(self, s):
        sys.stdout.write("[{}] {}".format(self.script_name, s))
        sys.stdout.flush()

    def write1(self, s):
        sys.stdout.write(s)
        sys.stdout.flush()

    def wormsay0(self, line):
        self.write0("\n")
        self.write0("     ^o^ --- {}\n".format(line))
        self.write0("     .\n")
        self.write0("   ..\n")
        self.write0("\n")

    def wormsay1(self, line):
        self.write0("\n")
        self.write0("  ^o^ --- {}\n".format(line))
        self.write0("    .\n")
        self.write0("     ..\n")
        self.write0("\n")


def make_console(script_name):
    """Return a ConsoleHelper configured with the given script name prefix."""
    return ConsoleHelper(script_name)
