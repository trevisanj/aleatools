#!/usr/bin/env python3
"""Stamp photo capture dates with a time-circuit display and optional flux capacitor.

JPEG and PNG inputs accept filenames or quoted wildcards. Originals are never
modified. Missing/invalid capture dates are reported, not guessed. Outputs add
_flux before the extension, beside each source photo unless -o is specified.
"""

import argparse
from contextlib import contextmanager
from dataclasses import fields
import math
from pathlib import Path
import sys
from threading import Event, Thread

from a107 import yesno

try:
    from _flux_files import open_photo, plan_jobs, save_photo
    from _flux_metadata import capture_time, parse_timestamp
    from _flux_render import layout_stamp, stamp_photo
    from _flux_style import StampStyle
except ModuleNotFoundError as exc:
    if exc.name == 'PIL':
        raise SystemExit('Pillow is required: install aleatools[photos]') from exc
    raise

from _cli_common import make_console


console = make_console('fluxcapacitor')


def finite_seconds(value):
    seconds = float(value)
    if not math.isfinite(seconds):
        raise ValueError('must be a finite number of seconds')
    return seconds


def jpeg_quality(value):
    quality = int(value)
    if not 1 <= quality <= 100:
        raise ValueError('must be between 1 and 100')
    return quality


def make_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('inputs', nargs='+', help='Input filenames or quoted wildcard patterns')
    parser.add_argument('-o', '--output-directory', type=Path, help='Directory for stamped copies; otherwise beside each source photo')
    parser.add_argument('--prefix', default='', help='Prefix for output filenames')
    parser.add_argument('--quality', type=jpeg_quality, default=95, help='JPEG output quality, 1 to 100')
    parser.add_argument('--dry-run', action='store_true', help='Validate photos, timestamps and layout without writing')
    parser.add_argument('--timestamp', type=parse_timestamp, help='Explicit ISO date/time instead of EXIF capture time')
    parser.add_argument('--time-shift', type=finite_seconds, default=0, metavar='SECONDS', help='Correct the printed time by this many seconds; metadata is unchanged')
    appearance = parser.add_argument_group('stamp appearance')
    for definition in fields(StampStyle):
        spec = definition.metadata
        kwargs = {'default': definition.default, 'help': spec['help'].replace('%', '%%')}
        if spec['boolean']:
            kwargs['action'] = argparse.BooleanOptionalAction
        elif spec['type'] is not None:
            kwargs['type'] = spec['type']
        if spec['choices'] is not None:
            kwargs['choices'] = spec['choices']
        appearance.add_argument('--' + definition.name.replace('_', '-'), **kwargs)
    return parser


@contextmanager
def progress(label):
    console.write0(label + '\n')
    stopped = Event()

    def heartbeat():
        while not stopped.wait(10):
            console.write0(label + ' (still working)\n')

    thread = Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stopped.set()
        thread.join()


def main(argv=None):
    parser = make_parser()
    args = parser.parse_args(argv)
    style = StampStyle(**{definition.name: getattr(args, definition.name) for definition in fields(StampStyle)})
    try:
        style.validate()
        jobs = plan_jobs(args.inputs, args.output_directory, args.prefix)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    succeeded = failed = skipped = 0
    try:
        for index, job in enumerate(jobs, 1):
            photo = result = None
            try:
                with progress(f'[{index}/{len(jobs)}] Reading {job.source}'):
                    photo, container = open_photo(job.source)
                    selected = capture_time(photo.getexif(), args.timestamp, args.time_shift)
                    layout = layout_stamp(photo.size, selected.value, style)
                console.write0(f'{selected.value.isoformat()} [{selected.source}] -> {job.destination}\n')
                if args.dry_run:
                    console.write0(f'Dry run: {layout.pixel_size[0]}x{layout.pixel_size[1]} stamp at {layout.origin}\n')
                else:
                    overwrite = job.destination.exists()
                    if overwrite and not yesno(f"ATTENTION: File '{job.destination}' already exists. Overwrite it?", default=True):
                        console.write0('output not overwritten.\n')
                        skipped += 1
                        continue
                    with progress('Rendering stamp'):
                        result = stamp_photo(photo, selected.value, style)
                    with progress(f'Writing {job.destination}'):
                        save_photo(result, photo, container, job.destination, args.quality, overwrite=overwrite)
                succeeded += 1
            except (ValueError, OSError, OverflowError, SyntaxError, EOFError) as exc:
                failed += 1
                print(f'[fluxcapacitor] Failed {job.source}: {exc}', file=sys.stderr, flush=True)
            finally:
                if result is not None:
                    result.close()
                if photo is not None:
                    photo.close()
    except KeyboardInterrupt:
        console.write0(f'Cancelled; {succeeded} completed, {failed} failed. Completed copies remain.\n')
        return 130
    console.write0(f'{succeeded} {"validated" if args.dry_run else "written"}, {failed} failed, {skipped} skipped.\n')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
