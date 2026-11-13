# ![This is a picture of Alea Torina](logo1.png) aleatools

Collection os some useful and sometimes stupid scripts written in Python for everyday use

## Flux capacitor photo dates

`fluxcapacitor.py` stamps JPEG and PNG copies with a Back to the Future-inspired
segmented date/time display and an optional flux capacitor on its left. It does not
modify the original photos or their timestamps. There is one visual style, with
configurable appearance and placement; no external fonts or image assets are needed.

Use Python 3.9 or newer. Install the photo dependency from this checkout:

```bash
python -m pip install '.[photos]'
./aleatools/scripts/fluxcapacitor.py 'photos/*.jpg' -o dated/
```

The installed command is `fluxcapacitor.py`. Within the source checkout, use the
executable path shown above. Inputs can be multiple filenames or quoted wildcard
patterns. Duplicate paths are processed once. Directories are not scanned recursively.

```bash
# Inspect timestamps, placement and output paths without writing anything.
./aleatools/scripts/fluxcapacitor.py 'photos/*.jpg' -o dated/ --dry-run

# Change size, margin, text color and outline; enable the capacitor.
./aleatools/scripts/fluxcapacitor.py photo.jpg -o dated/ \
  --flux --size 8% --margin 24px --color '#ffb347' \
  --outline-color '#101010' --outline-width 1.2

# Add display labels, a background panel, seconds and a shared cyan color.
./aleatools/scripts/fluxcapacitor.py photo.jpg -o labeled/ \
  --labels --panel --seconds --color '#87eaff'

# Use segmented slashes between day, month and year instead of the default spaces.
./aleatools/scripts/fluxcapacitor.py photo.jpg -o slashed/ --date-separator slash

# Move the stamp and hide the capacitor drawing.
./aleatools/scripts/fluxcapacitor.py photo.jpg -o plain/ \
  --position top-left --no-flux --date-order ymd --glow 0

# Supply a known capture time for a photo without capture metadata.
./aleatools/scripts/fluxcapacitor.py scan.png -o dated/ \
  --timestamp '1985-10-26T01:21:00-04:00'

./aleatools/scripts/fluxcapacitor.py --help
```

### Size and appearance

The default anchor is **bottom right**, with a **2% margin** and **6% stamp height**.
The stamp is **yellow (`#ffdd33`)**, with **outline width 3**, **glow strength 1**,
**space-separated date fields**, and **no capacitor drawing**. Use `--flux` to enable the capacitor.
Percentages refer to the shorter edge of the photo after orientation correction.
`--size` sets the entire stamp's height, including the capacitor, outline and glow;
`--margin` sets the inset for its enclosing rectangle. Both accept percentages,
pixels such as `80px`, or bare numbers interpreted as pixels. Reducing the stamp
below 16 pixels or requesting a stamp that cannot fit produces an error instead
of clipping it. Hiding the capacitor removes its space from the layout.

`--outline-width` is a percentage of the complete stamp height. `--glow`,
`--opacity` and `--panel-opacity` range from 0 to 1. Set `--glow 0` to disable glow
or `--outline-width 0` to disable the outline. Colors accept RGB hex notation or
Pillow color names. Quote hex colors in the shell. The entire capacitor drawing
shares the display's single color, outline and glow, including its frame and
terminals. There is no separate capacitor color. Digits use a continuous middle
horizontal segment.

`--date-order` accepts `dmy` (default), `mdy`, or `ymd`. Month names are fixed English
abbreviations; `ymd` uses a numeric month. The default date looks like `26 OCT 1985`.
`--date-separator slash` draws diagonal segments using the digit renderer;
`--date-separator space` (default) leaves those separators blank. Both use the same space
between date fields, half the gap between the date and time, so changing the
separator does not change the stamp's size or position.
`--clock 12` adds AM/PM; the default is
24-hour time. `--date-only`, `--seconds`, `--labels`, and `--panel` control the
display content. Boolean options also accept their `--no-...` forms. There are
no saved presets or configuration files in this version.

### Dates and exports

The timestamp comes from EXIF `DateTimeOriginal`, with `OffsetTimeOriginal` and
`SubsecTimeOriginal` when available. It keeps the camera's recorded local time;
an absent UTC offset stays unknown. It does not fall back to digitization dates,
filesystem dates, filenames, or the computer's timezone. Missing or malformed
capture metadata fails that photo; the remaining batch continues. `--timestamp`
explicitly overrides metadata. `--time-shift SECONDS` corrects the printed time
without editing the capture metadata. Fractional seconds and offsets are shown
in the processing report, not in the stamp.

Output adds `_flux` to the basename, before the original extension, beside each
source photo: `photos/beach.jpg` becomes `photos/beach_flux.jpg`. Use
`-o/--output-directory` to choose another directory, keeping the `_flux` suffix,
or `--prefix` to prepend filenames (for example, `copy-beach_flux.jpg`).
Existing outputs use the same `a107.yesno` overwrite prompt as `embed_base64.py`:
Enter accepts the default **Yes**, while **No** skips that file without failing
the batch. Dry runs do not prompt or overwrite. Paths that could replace an input,
symlink destinations and duplicate output names are rejected during batch
preflight. Outputs are published only after a successful write; an approved
overwrite replaces the old file atomically. New outputs use a hard link inside
the output directory, so the destination filesystem must support hard links.

The image keeps its dimensions after EXIF orientation normalization. PNG alpha,
EXIF capture metadata, ICC profiles, resolution, JPEG comments/XMP, and PNG text
and color metadata are retained where supported by Pillow. Existing EXIF dimension
tags are updated and the applied orientation tag is removed. Unknown metadata
fields exposed by Pillow are reported as errors rather than discarded. This is
not an archival metadata copier: opaque camera maker notes and metadata that
Pillow does not expose cannot be guaranteed to survive a rewrite. JPEG is
re-encoded; `--quality` controls its quality. PNG remains lossless outside the stamp.
JPEG XMP writing requires the declared Pillow version; see the
[Pillow release notes](https://pillow.readthedocs.io/en/stable/releasenotes/11.1.0.html).

Animated images, RAW, HEIC, TIFF, CMYK, high-bit-depth images and profiled non-RGB
images are not supported in this version. Convert a separate copy to RGB JPEG or
PNG first. Ctrl+C cancels processing, removes the current temporary output, and
leaves completed copies intact. Long stages report progress every ten seconds.
Exit status is 0 for success, 1 for per-photo failures, 2 for invalid arguments or
batch paths, and 130 for cancellation. Dry runs validate decoding, metadata and
layout; they do not test writing to the destination filesystem.

### Implementation and checks

`_flux_style.py` owns appearance definitions, defaults and value parsers; the CLI
derives appearance flags from those definitions. `_flux_metadata.py` owns capture
time selection, `_flux_render.py` owns the shared geometry/layout/renderer, and
`_flux_files.py` owns input expansion and output safety. Console messages reuse
`_cli_common.py`. The entry point and helpers follow the existing script-installation
mechanism in `setup.py`.

Run the isolated fixture checks with:

```bash
python -m unittest discover -s tests -p 'test_fluxcapacitor.py' -v
```

