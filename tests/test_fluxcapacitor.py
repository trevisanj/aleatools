"""Observable timestamp, rendering and export contracts using isolated photos."""

from dataclasses import replace
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import ExifTags, Image, ImageChops, ImageCms, PngImagePlugin


SCRIPTS = Path(__file__).resolve().parents[1] / 'aleatools' / 'scripts'
sys.path.insert(0, str(SCRIPTS))

from _flux_files import open_photo, plan_jobs, save_photo
from _flux_metadata import capture_time, parse_timestamp
from _flux_render import display_fields, layout_stamp, render_stamp, stamp_photo
from _flux_style import StampStyle, length


def photo_exif(date='1985:10:26 01:21:00', offset='-04:00', orientation=None):
    exif = Image.Exif()
    nested = {}
    if date is not None:
        nested[ExifTags.Base.DateTimeOriginal] = date
    if offset is not None:
        nested[ExifTags.Base.OffsetTimeOriginal] = offset
    if nested:
        exif[ExifTags.IFD.Exif] = nested
    if orientation is not None:
        exif[ExifTags.Base.Orientation] = orientation
    loaded = Image.Exif()
    loaded.load(exif.tobytes())
    return loaded


class TimestampTests(unittest.TestCase):
    def test_capture_offset_and_subseconds(self):
        exif = photo_exif()
        exif.get_ifd(ExifTags.IFD.Exif)[ExifTags.Base.SubsecTimeOriginal] = '1234'
        result = capture_time(exif)
        self.assertEqual(result.value.isoformat(), '1985-10-26T01:21:00.123400-04:00')

    def test_missing_offset_stays_unknown(self):
        self.assertIsNone(capture_time(photo_exif(offset=None)).value.tzinfo)

    def test_digitization_date_is_not_a_capture_fallback(self):
        exif = Image.Exif()
        exif[ExifTags.Base.DateTimeDigitized] = '2026:01:01 00:00:00'
        with self.assertRaisesRegex(ValueError, 'missing DateTimeOriginal'):
            capture_time(exif)

    def test_invalid_capture_time_and_offset_are_reported(self):
        for exif in (photo_exif('0000:00:00 00:00:00'), photo_exif(offset='+04:99')):
            with self.subTest(exif=exif), self.assertRaises(ValueError):
                capture_time(exif)

    def test_explicit_time_and_clock_shift_cross_midnight(self):
        value = parse_timestamp('1985-10-26T23:21:00-04:00')
        selected = capture_time(Image.Exif(), value, 3600)
        self.assertEqual(selected.value.isoformat(), '1985-10-27T00:21:00-04:00')
        self.assertIn('shifted', selected.source)
        self.assertEqual(value.day, 26)
        with self.assertRaises(ValueError):
            parse_timestamp('1985-10-26')


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.timestamp = datetime(1985, 10, 26, 1, 21)
        self.style = StampStyle()

    def test_bottom_right_margin_and_height(self):
        layout = layout_stamp((1600, 1000), self.timestamp, self.style)
        self.assertEqual(layout.pixel_size[1], 60)
        self.assertEqual(layout.origin, (1600 - 20 - layout.pixel_size[0], 920))

    def test_no_flux_removes_icon_space(self):
        full = layout_stamp((1600, 1000), self.timestamp, replace(self.style, flux=True))
        plain = layout_stamp((1600, 1000), self.timestamp, self.style)
        self.assertLess(plain.pixel_size[0], full.pixel_size[0])

    def test_render_is_transparent_and_changes_only_its_rectangle(self):
        photo = Image.new('RGB', (1600, 1000), '#dddddd')
        original = photo.tobytes()
        layout = layout_stamp(photo.size, self.timestamp, self.style)
        rendered = render_stamp(layout, self.style)
        self.assertEqual(rendered.size, layout.pixel_size)
        self.assertEqual(rendered.getpixel((0, 0))[3], 0)
        stamped = stamp_photo(photo, self.timestamp, self.style)
        changed = ImageChops.difference(photo, stamped.convert('RGB')).getbbox()
        self.assertIsNotNone(changed)
        self.assertGreaterEqual(changed[0], layout.origin[0])
        self.assertGreaterEqual(changed[1], layout.origin[1])
        self.assertLessEqual(changed[2], layout.origin[0] + layout.pixel_size[0])
        self.assertLessEqual(changed[3], layout.origin[1] + layout.pixel_size[1])
        self.assertEqual(photo.tobytes(), original)

    def test_all_months_and_optional_fields_render(self):
        style = replace(self.style, labels=True, seconds=True, clock='12', panel=True)
        for month in range(1, 13):
            timestamp = self.timestamp.replace(month=month)
            layout = layout_stamp((2000, 1000), timestamp, style)
            self.assertIsNotNone(render_stamp(layout, style).getbbox())

    def test_12_hour_boundary_and_numeric_date_order(self):
        style = replace(self.style, date_order='ymd', clock='12')
        fields = display_fields(self.timestamp.replace(hour=0), style)
        self.assertEqual([item.text for item in fields], ['1985', '10', '26', '12', ':', '21', 'AM'])
        self.assertEqual(display_fields(self.timestamp.replace(hour=12), style)[-1].text, 'PM')

    def test_default_spaces_and_slash_option_share_date_field_positions(self):
        slashes = replace(self.style, date_separator='slash')
        fields = display_fields(self.timestamp, slashes)
        self.assertEqual([item.text for item in fields], ['26', '/', 'OCT', '/', '1985', '01', ':', '21'])
        spaces = self.style
        spaced_fields = display_fields(self.timestamp, spaces)
        self.assertEqual([item.text for item in spaced_fields], ['26', 'OCT', '1985', '01', ':', '21'])
        self.assertEqual(spaced_fields[1].gap_before, spaced_fields[2].gap_before)
        self.assertEqual(spaced_fields[3].gap_before, 2 * spaced_fields[1].gap_before)
        slash_layout = layout_stamp((1600, 1000), self.timestamp, slashes)
        space_layout = layout_stamp((1600, 1000), self.timestamp, spaces)
        self.assertEqual(slash_layout.pixel_size, space_layout.pixel_size)
        self.assertEqual(slash_layout.origin, space_layout.origin)
        self.assertNotEqual(render_stamp(slash_layout, slashes).tobytes(), render_stamp(space_layout, spaces).tobytes())

    def test_digits_have_a_continuous_middle_bar(self):
        style = replace(self.style, flux=False, outline_width=0, glow=0, size=length('104px'))
        for digit in (2, 3, 4, 5, 6, 8, 9):
            with self.subTest(digit=digit):
                timestamp = self.timestamp.replace(day=digit)
                layout = layout_stamp((2000, 1000), timestamp, style)
                rendered = render_stamp(layout, style)
                # At this scale the second day digit's center is (81, 52).
                # Its middle must remain illuminated across the former split.
                self.assertTrue(all(rendered.getpixel((x, 52))[3] > 240 for x in range(76, 87)))

    def test_capacitor_and_digits_share_color_outline_and_glow(self):
        style = replace(self.style, flux=True, color='#ff0000', outline_color='#0000ff', size=length('120px'))
        layout = layout_stamp((2000, 1000), self.timestamp, style)
        rendered = render_stamp(layout, style)
        split = round(layout.display_x * rendered.width / layout.logical_size[0])
        for region in ((0, 0, split, rendered.height), (split, 0, rendered.width, rendered.height)):
            cropped = rendered.crop(region)
            pixels = [pixel for count, pixel in cropped.getcolors(cropped.width * cropped.height)]
            visible = [pixel for pixel in pixels if pixel[3] > 32]
            self.assertTrue(visible)
            self.assertTrue(all(pixel[1] == 0 for pixel in visible))
            self.assertTrue(any(pixel[0] > 200 and pixel[2] < 30 for pixel in visible))
            self.assertTrue(any(pixel[2] > 200 and pixel[0] < 30 for pixel in visible))

    def test_fit_errors_and_zero_opacity(self):
        with self.assertRaisesRegex(ValueError, 'does not fit'):
            layout_stamp((100, 100), self.timestamp, replace(self.style, size=length('50px')))
        layout = layout_stamp((1600, 1000), self.timestamp, self.style)
        self.assertIsNone(render_stamp(layout, replace(self.style, opacity=0)).getbbox())


class FileTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source.jpg'
        self.profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        Image.new('RGB', (1000, 1600), '#7b8b94').save(self.source, exif=photo_exif(orientation=6), icc_profile=self.profile)

    def tearDown(self):
        self.temporary.cleanup()

    def cli(self, *args, input_text=''):
        return subprocess.run([sys.executable, str(SCRIPTS / 'fluxcapacitor.py'), *map(str, args)],
                              capture_output=True, text=True, input=input_text, cwd=self.root)

    def test_cli_help_and_invalid_values(self):
        self.assertEqual(self.cli('--help').returncode, 0)
        for args in (('--size', 'nan%'), ('--color', 'bad-color'), ('--glow', '2'), ('--quality', '0')):
            result = self.cli(self.source, *args)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_dry_run_writes_nothing(self):
        output = self.root / 'dry'
        result = self.cli(self.source, '-o', output, '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('1985-10-26T01:21:00-04:00', result.stdout)
        self.assertIn('EXIF DateTimeOriginal', result.stdout)
        self.assertFalse(output.exists())

    def test_export_orients_pixels_preserves_capture_and_profile_and_original(self):
        before = hashlib.sha256(self.source.read_bytes()).digest()
        result = self.cli(self.source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).digest(), before)
        destination = self.root / 'source_flux.jpg'
        with Image.open(destination) as output:
            self.assertEqual(output.size, (1600, 1000))
            self.assertNotIn(ExifTags.Base.Orientation, output.getexif())
            self.assertEqual(capture_time(output.getexif()).value.isoformat(), '1985-10-26T01:21:00-04:00')
            self.assertEqual(output.info['icc_profile'], self.profile)
        output_before = destination.read_bytes()
        again = self.cli(self.source, input_text='n\n')
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn('output not overwritten', again.stdout)
        self.assertIn('1 skipped', again.stdout)
        self.assertEqual(destination.read_bytes(), output_before)

    def test_existing_output_accepts_enter_and_dry_run_never_prompts(self):
        destination = self.root / 'source_flux.jpg'
        destination.write_bytes(b'previous output')
        dry = self.cli(self.source, '--dry-run')
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertNotIn('Overwrite', dry.stdout)
        self.assertEqual(destination.read_bytes(), b'previous output')
        result = self.cli(self.source, input_text='\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('(Y/n)', result.stdout)
        with Image.open(destination) as output:
            self.assertEqual(output.size, (1600, 1000))
        self.assertFalse(list(self.root.glob('.fluxcapacitor-*.tmp')))

    def test_batch_continues_and_reports_missing_metadata(self):
        missing = self.root / 'missing.png'
        Image.new('RGB', (1000, 1000)).save(missing)
        result = self.cli(missing, self.source)
        self.assertEqual(result.returncode, 1)
        self.assertIn('missing DateTimeOriginal', result.stderr)
        self.assertIn('1 written, 1 failed', result.stdout)
        self.assertFalse((self.root / 'missing_flux.png').exists())

    def test_source_output_collisions_and_prefix_containment(self):
        stamped_input = self.root / 'source_flux.jpg'
        stamped_input.write_bytes(self.source.read_bytes())
        with self.assertRaisesRegex(ValueError, 'replace an input'):
            plan_jobs([str(self.source), str(stamped_input)], None, '')
        with self.assertRaisesRegex(ValueError, 'prefix'):
            plan_jobs([str(self.source)], self.root / 'output', '../')
        other = self.root / 'other'
        other.mkdir()
        copy = other / self.source.name
        copy.write_bytes(self.source.read_bytes())
        with self.assertRaisesRegex(ValueError, 'same output filename'):
            plan_jobs([str(self.source), str(copy)], self.root / 'output', '')
        jobs = plan_jobs([str(self.source), str(self.source)], self.root / 'output', '')
        self.assertEqual(len(jobs), 1)

    def test_symlink_output_is_rejected(self):
        output = self.root / 'output'
        output.mkdir()
        (output / 'source_flux.jpg').symlink_to(self.root / 'unrelated.jpg')
        with self.assertRaisesRegex(ValueError, 'unsafe output'):
            plan_jobs([str(self.source)], output, '')

    def test_interrupted_write_cleans_up_and_keeps_original(self):
        photo, container = open_photo(self.source)
        destination = self.root / 'output' / self.source.name
        with patch.object(Image.Image, 'save', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                save_photo(photo, photo, container, destination, 95)
        self.assertEqual(list(destination.parent.iterdir()), [])
        self.assertTrue(self.source.exists())
        photo.close()

    def test_png_alpha_and_source_metadata_are_immutable(self):
        source = self.root / 'alpha.png'
        Image.new('RGBA', (1600, 1000), (80, 90, 100, 100)).save(source, exif=photo_exif())
        photo, container = open_photo(source)
        metadata_before = photo.getexif().tobytes()
        destination = self.root / 'output' / source.name
        result = stamp_photo(photo, capture_time(photo.getexif()).value, StampStyle())
        save_photo(result, photo, container, destination, 95)
        self.assertEqual(photo.getexif().tobytes(), metadata_before)
        with Image.open(destination) as output:
            self.assertEqual(output.getpixel((0, 0)), photo.getpixel((0, 0)))
            self.assertEqual(capture_time(output.getexif()).value.utcoffset(), timedelta(hours=-4))
        photo.close()
        result.close()

    def test_png_text_and_color_metadata_survive_export(self):
        source = self.root / 'text.png'
        metadata = PngImagePlugin.PngInfo()
        metadata.add_itxt('Description', 'Original photo — descrição', lang='pt')
        metadata.add(b'gAMA', struct.pack('>I', 45455))
        metadata.add(b'sRGB', b'\x00')
        Image.new('RGB', (1000, 1000)).save(source, pnginfo=metadata, exif=photo_exif())
        result = self.cli(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(self.root / 'text_flux.png') as output:
            self.assertEqual(output.info['Description'], 'Original photo — descrição')
            self.assertEqual(output.info['Description'].lang, 'pt')
            self.assertAlmostEqual(output.info['gamma'], 0.45455)
            self.assertEqual(output.info['srgb'], 0)

    def test_jpeg_xmp_and_comment_survive_export(self):
        xmp = b'<x:xmpmeta xmlns:x="adobe:ns:meta/"><description>Original</description></x:xmpmeta>'
        Image.new('RGB', (1000, 1000)).save(self.source, exif=photo_exif(), xmp=xmp, comment=b'Original comment')
        result = self.cli(self.source)
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(self.root / 'source_flux.jpg') as output:
            self.assertEqual(output.info['xmp'], xmp)
            self.assertEqual(output.info['comment'], b'Original comment')

    def test_concurrent_destination_is_not_overwritten(self):
        photo, container = open_photo(self.source)
        destination = self.root / 'existing.jpg'
        destination.write_bytes(b'keep this file')
        with self.assertRaises(FileExistsError):
            save_photo(photo, photo, container, destination, 95)
        self.assertEqual(destination.read_bytes(), b'keep this file')
        self.assertFalse(list(self.root.glob('.fluxcapacitor-*.tmp')))
        photo.close()

    def test_basename_suffix_beside_source_and_directory_override(self):
        directory = self.root / 'photos'
        directory.mkdir()
        source = directory / 'beach.sunset.JPG'
        source.write_bytes(self.source.read_bytes())
        default = self.cli(source)
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertTrue((directory / 'beach.sunset_flux.JPG').is_file())
        self.assertFalse((self.root / 'beach.sunset_flux.JPG').exists())
        output = self.root / 'dated'
        explicit = self.cli(source, '-o', output, '--prefix', 'copy-')
        self.assertEqual(explicit.returncode, 0, explicit.stderr)
        self.assertTrue((output / 'copy-beach.sunset_flux.JPG').is_file())


if __name__ == '__main__':
    unittest.main()
