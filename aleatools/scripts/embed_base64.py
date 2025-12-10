#!/usr/bin/env python
"""Embed image files into an HTML document as base64 data URIs.

Takes an input HTML file, inlines local <img src="..."> references by replacing
them with data URIs, and writes the result to an output file. Remote images and
already inlined data URIs are left untouched.

Default output filename is "<input_basename>_base64.html" placed next to the
input file; an explicit output path may be provided with "-o/--output".
"""

import argparse
import base64
import html
import mimetypes
import os
import sys
from html.parser import HTMLParser

import a107
from _cli_common import make_console


SCRIPT_NAME = "embed_base64"

console = make_console(SCRIPT_NAME)
write0 = console.write0
write1 = console.write1
wormsay0 = console.wormsay0
wormsay1 = console.wormsay1


def is_data_uri(src):
    return src.startswith("data:")


def is_remote_src(src):
    return src.startswith("http://") or src.startswith("https://") or src.startswith("//")


def resolve_image_path(src, html_dir):
    if os.path.isabs(src):
        return src
    return os.path.join(html_dir, src)


def guess_mime(src):
    mtype, _enc = mimetypes.guess_type(src)
    return mtype or "application/octet-stream"


def build_start_tag(tag, attrs, selfclosing=False):
    pieces = ["<", tag]
    for (key, value) in attrs:
        pieces.append(" ")
        pieces.append(key)
        if value is not None:
            pieces.append('="{}"'.format(html.escape(value, quote=True)))
    pieces.append(" />" if selfclosing else ">")
    return "".join(pieces)


class EmbedBase64Parser(HTMLParser):
    def __init__(self, html_dir):
        super(EmbedBase64Parser, self).__init__(convert_charrefs=False)
        self.html_dir = html_dir
        self.out = []
        self.stats = {
            "total_imgs": 0,
            "embedded": 0,
            "skipped_data": 0,
            "skipped_remote": 0,
            "missing": 0,
            "errors": 0,
        }

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "img":
            self.out.append(self.get_starttag_text())
            return
        self.stats["total_imgs"] += 1
        self.out.append(self._process_img(attrs, selfclosing=False))

    def handle_startendtag(self, tag, attrs):
        if tag.lower() != "img":
            self.out.append(self.get_starttag_text())
            return
        self.stats["total_imgs"] += 1
        self.out.append(self._process_img(attrs, selfclosing=True))

    def handle_endtag(self, tag):
        self.out.append("</{}>".format(tag))

    def handle_data(self, data):
        self.out.append(data)

    def handle_comment(self, data):
        self.out.append("<!--{}-->".format(data))

    def handle_entityref(self, name):
        self.out.append("&{};".format(name))

    def handle_charref(self, name):
        self.out.append("&#{};".format(name))

    def handle_decl(self, decl):
        self.out.append("<!{}>".format(decl))

    def handle_pi(self, data):
        self.out.append("<?{}>".format(data))

    def _process_img(self, attrs, selfclosing):
        src_value = None
        attrs_dict = {}
        for (k, v) in attrs:
            attrs_dict[k.lower()] = (k, v)  # store original key casing
            if k.lower() == "src":
                src_value = v

        if not src_value:
            self.stats["missing"] += 1
            write0("img with no src -> skipped\n")
            return self.get_starttag_text()

        if is_data_uri(src_value):
            self.stats["skipped_data"] += 1
            write0("img '{}' is already data URI -> skipped\n".format(src_value))
            return self.get_starttag_text()

        if is_remote_src(src_value):
            self.stats["skipped_remote"] += 1
            write0("img '{}' is remote -> skipped\n".format(src_value))
            return self.get_starttag_text()

        img_path = resolve_image_path(src_value, self.html_dir)
        try:
            with open(img_path, "rb") as f:
                img_bytes = f.read()
        except Exception as e:
            self.stats["errors"] += 1
            write1("Oops :( could not read image '{}': {}\n".format(img_path, str(e)))
            return self.get_starttag_text()

        mime_type = guess_mime(src_value)
        encoded = base64.b64encode(img_bytes).decode("ascii")
        data_uri = "data:{};base64,{}".format(mime_type, encoded)

        attrs_out = []
        for (k_lower, (orig_key, value)) in attrs_dict.items():
            if k_lower == "src":
                attrs_out.append((orig_key, data_uri))
            else:
                attrs_out.append((orig_key, value))

        self.stats["embedded"] += 1
        write0("img '{}' (resolved '{}') embedded as {}\n".format(src_value, img_path, mime_type))
        return build_start_tag("img", attrs_out, selfclosing=selfclosing)

    def getvalue(self):
        return "".join(self.out)


def embed_file(html_path):
    html_dir = os.path.dirname(os.path.abspath(html_path))
    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        html_text = f.read()

    parser = EmbedBase64Parser(html_dir)
    parser.feed(html_text)
    parser.close()

    return parser.getvalue(), parser.stats


def default_output_path(input_path):
    base_dir = os.path.dirname(input_path)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    return os.path.join(base_dir, "{}_base64.html".format(base_name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)
    parser.add_argument("input", type=str, help="input HTML file")
    parser.add_argument("-o", "--output", type=str, required=False,
        help="output HTML file (default: <input_basename>_base64.html)")

    args = parser.parse_args()

    input_path = args.input
    output_path = args.output or default_output_path(input_path)

    if not os.path.isfile(input_path):
        write1("Input file '{}' not found.\n".format(input_path))
        sys.exit(1)

    output_dir = os.path.dirname(os.path.abspath(output_path)) or "."
    if not os.path.isdir(output_dir):
        write1("Output directory '{}' does not exist.\n".format(output_dir))
        sys.exit(1)

    wormsay0("hi")
    write0("embedding images from '{}'\n".format(input_path))

    try:
        html_out, stats = embed_file(input_path)
    except Exception:
        a107.get_python_logger().exception("Error embedding images in '{}'".format(input_path))
        write1("Oops :( unexpected error while embedding images.\n")
        sys.exit(1)

    if os.path.exists(output_path):
        if not a107.yesno("ATTENTION: File '{}' already exists. Overwrite it?".format(output_path), default=True):
            write0("output not overwritten.\n")
            sys.exit(0)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_out)
            write0("written to '{}'\n".format(output_path))
    except Exception:
        a107.get_python_logger().exception("Error writing output file '{}'".format(output_path))
        write1("Oops :( could not write output file.\n")
        sys.exit(1)

    write0("images found: {total_imgs}, embedded: {embedded}, skipped data: {skipped_data}, "
        "skipped remote: {skipped_remote}, missing/no src: {missing}, errors: {errors}\n".format(**stats))

    wormsay1("bye")
