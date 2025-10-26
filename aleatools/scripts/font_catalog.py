#!/usr/bin/env python3
# font_catalog.py — neat PDF font catalogue + fuzzy finder
# - Preprocess first; only non-empty sections
# - Clean layout: sample → (optional specs) → path; stable spacing
# - Section headers baseline-corrected; side-pane bookmarks jump to headers
# - PIL fallback rendered to temp PNG at high resolution (configurable scale)
# - NO table of contents page

import os, sys, subprocess, argparse, textwrap, hashlib, socket, io, tempfile, atexit
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Literal
from pathlib import Path
from difflib import SequenceMatcher

# ---------- Optional deps ----------
try:
    from fontTools.ttLib import TTFont, TTCollection
except Exception:
    print("ERROR: fonttools is required: pip install fonttools", file=sys.stderr)
    raise

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont as RLTTFont
    from reportlab.lib.units import mm
except Exception:
    print("ERROR: reportlab is required: pip install reportlab", file=sys.stderr)
    raise

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except Exception:
    PIL_OK = False

# ---------- Data ----------
@dataclass
class FontFace:
    family: str
    style: str
    fullname: str
    path: str
    index: Optional[int] = None
    weight: Optional[int] = None
    italic: Optional[bool] = None
    mono: Optional[bool] = None
    classification: Optional[str] = None
    supports_accents: Optional[bool] = None

@dataclass
class PreparedFace:
    face: FontFace
    section: str                 # A..Z or '#'
    draw_mode: Literal['rl','pil','none']
    sample_w_pt: float           # points
    sample_h_pt: float           # points

# ---------- Config ----------
SAMPLE_TEXT_DEFAULT = "Sphinx of black quartz, judge my vow — ÁÉÍÓÚ áéíóú ãõ ç ß 0123456789"
SAMPLE_FONT_SIZE_PT = 12.0           # target text size (pt)
SAMPLE_LINE_PT      = 14.0           # RL line height (pt)
PATH_FONT_PT        = 8.0            # file path text size (pt)
TITLE_PT            = 16.0
HEADER_PT_DEFAULT   = 26.0
MARGIN_MM           = 15.0
BLOCK_GAP_PT        = 8.0            # gap between entries
AFTER_SECTION_GAP_PT= 6.0            # extra gap after header

# ---------- Helpers ----------
def have_fc_list() -> bool:
    try:
        subprocess.run(["fc-list", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False

def list_fonts_with_fontconfig() -> List[FontFace]:
    fmt = "%{file}|%{family}|%{style}|%{fullname}\n"
    out = subprocess.check_output(["fc-list", "-f", fmt], text=True, errors="ignore")
    faces: List[FontFace] = []
    for line in out.splitlines():
        if not line.strip(): continue
        parts = line.split("|")
        if len(parts) < 4: continue
        fpath, family, style, fullname = [p.strip() for p in parts[:4]]
        family   = family.split(",")[0].strip() or fullname.split(",")[0].strip() or "Unknown"
        style    = style.split(",")[0].strip() or "Regular"
        fullname = fullname.split(",")[0].strip() or f"{family} {style}".strip()
        faces.append(FontFace(family=family, style=style, fullname=fullname, path=fpath))
    return faces

def list_fonts_by_scanning() -> List[FontFace]:
    roots = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        str(Path.home() / ".local/share/fonts"),
        str(Path.home() / ".fonts"),
        "/usr/share/texlive/texmf-dist/fonts",
    ]
    exts = {".ttf", ".otf", ".ttc", ".otc"}
    faces: List[FontFace] = []
    for root in roots:
        if not os.path.isdir(root): continue
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if Path(fn).suffix.lower() in exts:
                    path = os.path.join(dirpath, fn)
                    faces.extend(faces_from_file(path))
    return faces

def faces_from_file(path: str) -> List[FontFace]:
    out: List[FontFace] = []
    try:
        suffix = Path(path).suffix.lower()
        if suffix in (".ttc", ".otc"):
            coll = TTCollection(path)
            for i, tt in enumerate(coll.fonts):
                family, style, fullname = safe_names(tt)
                meta = analyze_font(tt, family)
                out.append(FontFace(family=family, style=style, fullname=fullname, path=path, index=i,
                                    weight=meta["weight"], italic=meta["italic"],
                                    mono=meta["mono"], classification=meta["classification"]))
        else:
            tt = TTFont(path, fontNumber=0, lazy=True)
            family, style, fullname = safe_names(tt)
            meta = analyze_font(tt, family)
            out.append(FontFace(family=family, style=style, fullname=fullname, path=path, index=None,
                                weight=meta["weight"], italic=meta["italic"],
                                mono=meta["mono"], classification=meta["classification"]))
    except Exception:
        pass
    return out

def safe_names(tt) -> Tuple[str, str, str]:
    def _name(nameID, fallback=""):
        try:
            nm = tt["name"].getName(nameID, 3, 1, 0x409) or tt["name"].getName(nameID, 1, 0, 0)
            return str(nm) if nm else fallback
        except Exception:
            return fallback
    family = _name(1, "Unknown")
    subfam = _name(2, "Regular")
    fullname = _name(4, f"{family} {subfam}".strip())
    return family, subfam, fullname

def analyze_font(tt, family_hint: str) -> Dict:
    mono = None; italic = None; weight = None; classification = "unknown"
    try:
        os2 = tt["OS/2"]
        weight = int(getattr(os2, "usWeightClass", 400))
        fs = getattr(os2, "fsSelection", 0)
        italic = bool(fs & 0x01)
        panose = getattr(os2, "panose", None)
    except Exception:
        panose = None
    try:
        post = tt["post"]; mono = (getattr(post, "isFixedPitch", 0) == 1)
    except Exception:
        mono = ("mono" in (family_hint or "").lower())
    if mono:
        classification = "mono"
    else:
        try:
            if panose and getattr(panose, "bFamilyType", 0) == 2:
                bss = getattr(panose, "bSerifStyle", 0)
                classification = "sans" if bss == 11 else ("serif" if bss in (2,3,4,5,7,8,9,10) else "unknown")
            else:
                famlower = (family_hint or "").lower()
                if "sans" in famlower: classification = "sans"
                elif "serif" in famlower: classification = "serif"
        except Exception:
            pass
    return {"weight": weight, "italic": italic, "mono": mono, "classification": classification}

def normalize(s: str) -> str:
    return " ".join(s.lower().replace("-", " ").replace("_", " ").split())

def _initial_letter(name: str) -> str:
    for ch in (name or "").strip():
        if ch.isalpha():
            return ch.upper()
    return "#"

def default_pdf_path() -> str:
    host = socket.gethostname()
    return f"fonts_in_{host}.pdf"

# ---------- Draw/measure ----------
def _register_font_for_pdf(path: str) -> Optional[str]:
    try:
        if Path(path).suffix.lower() in (".ttc", ".otc"):
            return None
        unique = hashlib.md5(path.encode("utf-8")).hexdigest()[:10]
        internal_name = f"F_{unique}"
        if internal_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(RLTTFont(internal_name, path))
        return internal_name
    except Exception:
        return None

def probe_draw_method_and_size(path: str, index: Optional[int], text: str, pil_scale: float) -> Tuple[Literal['rl','pil','none'], float, float]:
    """Return ('rl'|'pil'|'none', width_pt, height_pt) for the sample."""
    internal = _register_font_for_pdf(path)
    if internal:
        return 'rl', 0.0, SAMPLE_LINE_PT
    if PIL_OK:
        try:
            kwargs = {"index": index} if (index is not None) else {}
            fnt = ImageFont.truetype(path, size=int(round(SAMPLE_FONT_SIZE_PT * pil_scale)), **kwargs)
            bbox = fnt.getbbox(text)
            w = max(1, bbox[2] - bbox[0] + 2)
            h = max(1, bbox[3] - bbox[1] + 2)
            return 'pil', float(w)/pil_scale, float(h)/pil_scale
        except Exception:
            pass
    return 'none', 0.0, 0.0

def draw_sample(c: canvas.Canvas, face: PreparedFace, text: str, x: float, y: float, tmp_paths: List[str], pil_scale: float) -> float:
    """Draw the sample for a prepared face at (x,y). Returns new y. Uses temp PNG for PIL path."""
    if face.draw_mode == 'rl':
        internal = _register_font_for_pdf(face.face.path)
        c.setFont(internal, SAMPLE_FONT_SIZE_PT)
        c.drawString(x, y, text)
        return y - SAMPLE_LINE_PT
    elif face.draw_mode == 'pil':
        kwargs = {"index": face.face.index} if (face.face.index is not None) else {}
        fnt = ImageFont.truetype(face.face.path, size=int(round(SAMPLE_FONT_SIZE_PT * pil_scale)), **kwargs)
        bbox = fnt.getbbox(text)
        w_px = max(1, bbox[2] - bbox[0] + 2)
        h_px = max(1, bbox[3] - bbox[1] + 2)
        img = Image.new("L", (w_px, h_px), 255)
        draw = ImageDraw.Draw(img)
        draw.text((-bbox[0]+1, -bbox[1]+1), text, font=fnt, fill=0)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        img.save(tmp, format="PNG"); tmp.flush(); tmp.close()
        tmp_paths.append(tmp.name)
        w_pt, h_pt = w_px/pil_scale, h_px/pil_scale
        c.drawImage(tmp.name, x, y - h_pt + 2, width=w_pt, height=h_pt, mask='auto')
        return y - (h_pt + 2)
    # shouldn't happen if prefiltered
    c.setFont("Helvetica", 9)
    c.drawString(x, y, "(sample unavailable)")
    return y - 12.0

# ---------- Prep pipeline ----------
def enrich_and_prepare(faces: List[FontFace], sample_text: str, require_sample: bool, require_accents: bool, accents: str, pil_scale: float) -> List[PreparedFace]:
    # Accents coverage
    need_codes = {ord(ch) for ch in accents if not ch.isspace()}
    for f in faces:
        try:
            if Path(f.path).suffix.lower() in (".ttc", ".otc"):
                coll = TTCollection(f.path); sub = coll.fonts[(f.index or 0)]
                cmap = sub.getBestCmap() or {}
                f.supports_accents = all(cp in cmap for cp in need_codes)
            else:
                tt = TTFont(f.path, fontNumber=0, lazy=True)
                cmap = tt.getBestCmap() or {}
                f.supports_accents = all(cp in cmap for cp in need_codes)
        except Exception:
            f.supports_accents = False

    faces.sort(key=lambda f: (normalize(f.family), normalize(f.style), f.path))

    prepared: List[PreparedFace] = []
    for f in faces:
        mode, w_pt, h_pt = probe_draw_method_and_size(f.path, f.index, sample_text, pil_scale)
        if require_sample and mode == 'none':
            continue
        if require_accents and not f.supports_accents:
            continue
        letter = _initial_letter(f.family or Path(f.path).name)
        prepared.append(PreparedFace(face=f, section=letter, draw_mode=mode,
                                     sample_w_pt=w_pt, sample_h_pt=(SAMPLE_LINE_PT if mode=='rl' else h_pt)))
    return prepared

# ---------- PDF ----------
def draw_catalog_pdf(prepared: List[PreparedFace], out_pdf: str, simple: bool, sample_text: str, section_size: int, pil_scale: float):
    c = canvas.Canvas(out_pdf, pagesize=A4)
    W, H = A4
    margin = MARGIN_MM * mm
    y = H - margin

    # Track temp images to clean up
    tmp_paths: List[str] = []
    def cleanup_tmp():
        for p in tmp_paths:
            try: os.remove(p)
            except Exception: pass
    atexit.register(cleanup_tmp)

    # Title
    c.setFont("Helvetica-Bold", TITLE_PT)
    c.drawString(margin, y, "System Font Catalogue")
    y -= (TITLE_PT * 1.1)
    c.setFont("Helvetica", 9)
    mode_txt = 'simple' if simple else 'full'
    c.drawString(margin, y, f"Total fonts listed: {len(prepared)}   |   mode: {mode_txt}")
    y -= 14.0

    # Group after filters
    from collections import OrderedDict
    grouped: "OrderedDict[str, List[PreparedFace]]" = OrderedDict()
    for pf in prepared:
        grouped.setdefault(pf.section, []).append(pf)

    def new_page():
        nonlocal y
        c.showPage()
        y = H - margin

    # Section header metrics (lowered baseline)
    header_ascent  = 0.80 * section_size
    header_descent = 0.20 * section_size
    header_total   = header_ascent + header_descent
    header_after_gap = AFTER_SECTION_GAP_PT
    path_gap_above = 4.0
    entry_gap      = BLOCK_GAP_PT

    created_bookmarks = set()  # ensure we bookmark once per letter

    # Iterate sections
    for letter, items in grouped.items():
        # Room for header + first entry
        first = items[0]
        sample_h0 = max(first.sample_h_pt, SAMPLE_LINE_PT)
        min_first_block = sample_h0 + path_gap_above + 10.0 + entry_gap + (0 if simple else 12.0)
        need = header_total + header_after_gap + min_first_block
        if y < margin + need:
            new_page()

        # Header at lowered baseline
        baseline = y - header_descent
        c.setFont("Helvetica-Bold", section_size)
        c.drawString(margin, baseline, letter)
        # Bookmark only once so the outline links to the FIRST occurrence
        if letter not in created_bookmarks:
            dest = f"sec_{letter}"
            c.bookmarkPage(dest)
            c.addOutlineEntry(letter, dest, level=0, closed=False)
            created_bookmarks.add(letter)

        # move below the header
        y = baseline - header_ascent - header_after_gap

        # Entries
        for pf in items:
            sample_h = max(pf.sample_h_pt, SAMPLE_LINE_PT)
            block_h = sample_h + path_gap_above + 10.0 + entry_gap + (0 if simple else 12.0)
            if y < margin + block_h:
                new_page()
                baseline = y - header_descent
                c.setFont("Helvetica-Bold", section_size)
                c.drawString(margin, baseline, letter)
                # no new bookmark here (keep outline pointing to first)
                y = baseline - header_ascent - header_after_gap

            # SAMPLE
            y = draw_sample(c, pf, sample_text, margin, y, tmp_paths, pil_scale)

            # SPECS (full)
            if not simple:
                f = pf.face
                specs = f"{f.family} — {f.style}   |   class={f.classification or 'unknown'}   mono={'yes' if f.mono else 'no'}   weight={f.weight if f.weight else '?'}   italic={'yes' if f.italic else 'no'}   accents={'yes' if f.supports_accents else 'no'}"
                c.setFont("Helvetica-Oblique", 8)
                c.drawString(margin, y, specs)
                y -= 12.0

            # PATH (belongs to this sample)
            c.setFont("Helvetica", PATH_FONT_PT)
            path_text = pf.face.path + (f"  (index {pf.face.index})" if pf.face.index is not None else "")
            y -= path_gap_above
            c.drawString(margin, y, path_text)
            y -= 10.0

            # Gap after entry
            y -= entry_gap

    c.save()
    # cleanup temp files
    for p in tmp_paths:
        try: os.remove(p)
        except Exception: pass

# ---------- Fuzzy search ----------
def match_score(query: str, candidate: str) -> float:
    return 100.0 * SequenceMatcher(None, normalize(query), normalize(candidate)).ratio()

def build_search_index(faces: List[FontFace]) -> List[Tuple[FontFace, str]]:
    corpus = []
    for f in faces:
        fields = [f.family, f.style, f.fullname, Path(f.path).name]
        corpus.append((f, " ".join(x for x in fields if x)))
    return corpus

def search_fonts(faces: List[FontFace], query: str, top_k: int = 10) -> List[Tuple[FontFace, float]]:
    corpus = build_search_index(faces)
    scored = [ (f, match_score(query, s)) for (f, s) in corpus ]
    scored.sort(key=lambda t: (-t[1], t[0].family.lower(), t[0].style.lower()))
    return scored[:top_k]

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser(description="Generate a clean PDF catalogue of system fonts and search them fuzzily.")
    ap.add_argument("--pdf", nargs="?", const="AUTO",
                    help="Output PDF path. If used without value, writes 'fonts_in_<hostname>.pdf'.")
    ap.add_argument("--full", action="store_true",
                    help="Detailed mode (adds family/style/specs). Default is simplified (sample + path).")
    ap.add_argument("--search", type=str, help="Fuzzy search a font by name")
    ap.add_argument("--top", type=int, default=10, help="Top-K search results")
    ap.add_argument("--list-only", action="store_true", help="Just list fonts (no PDF)")
    ap.add_argument("--require-sample", action="store_true",
                    help="Keep only fonts drawable by ReportLab or Pillow (strict).")
    ap.add_argument("--require-accents", action="store_true",
                    help="Keep only fonts covering the accent characters.")
    ap.add_argument("--accents", type=str, default="ÁÉÍÓÚ áéíóú ãõ ç ß",
                    help="Accent characters to require when --require-accents is set.")
    ap.add_argument("--sample", type=str, default=SAMPLE_TEXT_DEFAULT,
                    help="Sample text to print with each font.")
    ap.add_argument("--section-size", type=int, default=int(HEADER_PT_DEFAULT),
                    help="Section header size (points). Default: 26.")
    ap.add_argument("--pil-scale", type=float, default=2.0,
                    help="PIL rasterization scale (1.0–4.0). Higher = sharper samples. Default: 2.0.")
    args = ap.parse_args()

    # Discover
    faces = list_fonts_with_fontconfig() if have_fc_list() else list_fonts_by_scanning()

    # SEARCH FLOW (independent of PDF)
    if args.search:
        results = search_fonts(faces, args.search, top_k=args.top)
        print(f"Top {len(results)} matches for: {args.search!r}")
        for f, score in results:
            ix = f" (index {f.index})" if f.index is not None else ""
            print(f"{score:6.2f}%  {f.family} — {f.style}  ::  {f.path}{ix}")
        if args.list_only and not args.pdf:
            return

    # LIST-ONLY
    if args.list_only and not args.pdf:
        faces.sort(key=lambda f: (normalize(f.family), normalize(f.style), f.path))
        for f in faces:
            ix = f" (index {f.index})" if f.index is not None else ""
            print(f"{f.family} — {f.style} :: {f.path}{ix} | class={f.classification} mono={'yes' if f.mono else 'no'} weight={f.weight} italic={'yes' if f.italic else 'no'} accents={'yes' if f.supports_accents else 'no'}")
        return

    # PDF FLOW — PREP FIRST
    prepared = enrich_and_prepare(
        faces=faces,
        sample_text=args.sample,
        require_sample=args.require_sample,
        require_accents=args.require_accents,
        accents=args.accents,
        pil_scale=args.pil_scale
    )

    if args.pdf:
        out_pdf = default_pdf_path() if args.pdf == "AUTO" else args.pdf
        draw_catalog_pdf(
            prepared=prepared,
            out_pdf=out_pdf,
            simple=(not args.full),
            sample_text=args.sample,
            section_size=int(args.section_size),
            pil_scale=args.pil_scale,
        )
        print(f"PDF written to: {out_pdf}")

if __name__ == "__main__":
    main()
