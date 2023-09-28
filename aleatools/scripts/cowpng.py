#!/usr/bin/env python

"""
cowsay -> lolcat -> PNG
"""

import argparse, a107, aleatools, os


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,  formatter_class=a107.SmartFormatter)
    parser.add_argument('message', nargs="+", help="Message to be rendered. "
        "May be passsed as multiple arguments and will be concatenated with a ' '")

    args = parser.parse_args()

    text = " ".join(args.message)

    fn_txt = a107.temp_filename("cowpng", "txt")

    os.system(f'script -q -c "cowsay {text} | lolcat" {fn_txt}')

    with open(fn_txt, "r") as f:
        s = f.read()

    # discards first and 2 lasts lines of output text
    s_ = "\n".join(s.split("\n")[1:-2])

    fn_png = a107.new_filename("cowpng", "png")

    aleatools.render_ansi(s_, filename=fn_png)
    a107.print_yoda(f"File '{fn_png}' saved successfully")

    os.system(f"xdg-open {fn_png}")

