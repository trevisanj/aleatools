#!/usr/bin/env python
"""
Creates an HTML file which displays text rendered using every installed font.
"""
import argparse, webbrowser,  a107, subprocess, socket


def wormsay0(line):
    myprint("")
    myprint("     ^o^ --- {}".format(line))
    myprint("     .")
    myprint("   ..")
    myprint("")


def wormsay1(line):
    myprint("")
    myprint("  ^o^ --- {}".format(line))
    myprint("    .")
    myprint("     ..")
    myprint("")


def myprint(s):
    print("AA {}".format(s))


def main(args):
    """

    Original code is a bash script from https://askubuntu.com/questions/8452/font-viewer-for-font-collectors,
    herein reproduced:

    #! /usr/bin/env bash

        cat << __HEADER
        <!DOCTYPE html>
        <html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
            <title>Sample of local fonts matching '$1'</title>
        </head>
        <body>
        __HEADER

        fc-list --format='%{family}\n' $1 | sort -u | while IFS='' read -r fontfamily
        do
            cat << __BODY
            <hr/>
            <div style="font-family: '${fontfamily}', 'serif'">
                <h1>${fontfamily}</h1>
                <p>
                    The quick brown fox jumped over the lazy brown dog<br/>
                    0123456789,.:;?/<>'"[]{}|\-=\`~!@#$%^&*()-=\\
                </p>
            </div>
        __BODY

        done

        cat << __FOOTER
            <hr/>
        </body>
        </html>
        __FOOTER

    """
    probe = probe = args.containing.lower()
    hostname = socket.gethostname()
    title = f"Fonts in {hostname}"+(f" matching '{probe}'" if probe else "")
    family_and_file = subprocess.run(["fc-list", '--format=%{family}:%{file}\n'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    as_list = family_and_file.split("\n")
    rows = [line.split(":") for line in as_list if len(line) > 1]
    # Filters names matching "--containing" argument
    if probe:
        rows = [row for row in rows if probe in row[0].lower()]
    # Sorts fonts alphabetically
    rows.sort(key=lambda row: row[0])

    # Initializes lines variable with HTML header
    lines = [f"""
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <title>{title}</title>
</head>
<body>
    <style>
    table {{border-spacing: {int(20/32*args.size)}px}}
    td {{vertical-align: top}}
    .f {{font-family: sans; text-align: right}}
    .t {{font-size:{args.size}px}}
    body {{white-space: nowrap}}
    </style>
    <table border=0 width=100%>"""]

    lastfamily = "!@*(#"
    for family, file in rows:
        if family.startswith(lastfamily):
            continue
        lastfamily = family
        lines.append(f"""        <tr>
            <td class=f>
                {family}
            </td>
            <td class=t style="font-family: {family}">
                {args.text}
            </td>\n""")
        if args.show_filename:
            lines.append(f"""            <td>
                <pre>{file}</pre>
            </td>\n""")

        lines.append("        </tr>\n")

    lines.append("""    </table>
</body>
</html>""")

    ret = a107.temp_filename(f"fonts-in-{hostname}", "html")
    with open(ret, "w") as f:
        for line in lines:
            f.write(line); f.write("\n")
    return ret

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument('-s', '--size', type=int, default=32, required=False,
                        help='Font size',)
    parser.add_argument('-c', '--containing', type=str, default="", required=False,
                        help='Filters fonts whose name contain [case-insensitive] string ', )
    parser.add_argument('-f', '--show-filename', action="store_true",
                        help="Show font filename as well")
    parser.add_argument('text', type=str, nargs="?",
                        default="The quick brown fox jumped over the lazy dog 0123456789,.:;?/<>'\"[]{}|-=`~!@#$%^&*()-=\\",
                        help='Text to be rendered using each different font in your system')

    args = parser.parse_args()

    wormsay0("hi")
    filepath = main(args)
    wormsay1(f"now see '{filepath} on your browser")
    webbrowser.open(filepath)
