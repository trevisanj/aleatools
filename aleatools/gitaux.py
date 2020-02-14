"""
API specific to pullall.py and pushall.py. Routines here have lots of side-effects, such as prints
and system exits.
"""
import sys
import os
import logging
import a107

__all__ = ["gitaux_main"]

PWD = ""
MSG = ""
FN = "repos.txt"


def push_pull_1(flag_push, repo):
    """chdir; (git add+commit+push) or (git pull); restore dir"""
    print("\n".join(a107.format_box(repo)))
    try:
        os.chdir(os.path.join(PWD, repo))

        if flag_push:
            os.system("git add . --all")
            os.system("git commit -m \"{}\"".format(MSG))
            os.system("git push")
        else:
            os.system("git pull")

        os.chdir(PWD)
    except:
        logging.exception("Failed '{}'".format(repo))


def get_repos():
    f"""Parses file {FN} and returns list of repositories."""
    if not os.path.isfile(FN):
        print(f"File '{FN} not found in directory.\n"
              "Please create a list of repositories, one per line in the file.\n"
              "Comments (lines starting with '#') are allowed.\nGood luck :)")
        sys.exit()
    with open("repos.txt", "r") as file:
        _repos = [x.strip() for x in file.readlines() if not x.strip().startswith("#")]

    print("Figuring out repositories...")
    repos = []
    for r in _repos:
        for dirpath, dirnames, filenames in os.walk(r):
            if ".git" in dirnames:
                repos.append(dirpath)
    print(f"...found {len(repos)} repositories{'s' if len(repos) != 1 else ''}: {str(repos)[1:-1]}")
    return repos


def gitaux_main(flag_push, flag_simulation=False):
    f"""
    Pushes or pulls repositories listed in file '{FN}' (does NOT recurse into subdirectories).

    Args:
        flag_push: whether to push or pull .
        flag_simulation: if set, will just print repository name and will have no effect.
    """
    global MSG, PWD

    if flag_push:
        if len(sys.argv) < 2:
            print("Please specify a commit message as one or more command-line arguments.")
            sys.exit()
        else:
            MSG = " ".join(sys.argv[1:])

    PWD = os.getcwd()
    repos = get_repos()
    for repo in repos:
        if flag_simulation:
            print(f"{'pushing' if flag_push else 'pulling'} '{repo}'")
        else:
            push_pull_1(flag_push, repo)
