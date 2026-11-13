"""Input expansion, output containment and atomic photo export."""

from dataclasses import dataclass
import glob
import os
from pathlib import Path
import struct
import tempfile

from PIL import ExifTags, Image, ImageOps, PngImagePlugin


SUPPORTED_FORMATS = ('JPEG', 'PNG')
COMMON_METADATA = ('icc_profile', 'dpi')
JPEG_METADATA = ('comment', 'xmp')
# Pillow exposes these PNG color chunks as parsed numeric values.
PNG_COLOR_CHUNKS = {'gamma': (b'gAMA', 100000), 'chromaticity': (b'cHRM', 100000), 'srgb': (b'sRGB', 1)}


@dataclass(frozen=True)
class PhotoJob:
    source: Path
    destination: Path


def output_filename(filename, prefix):
    """Insert the stamp suffix before the original extension."""
    name = Path(filename)
    return f'{prefix}{name.stem}_flux{name.suffix}'


def plan_jobs(patterns, output_directory, prefix):
    """Resolve every path once and reject an ambiguous batch before writing."""
    if prefix and (Path(prefix).name != prefix or '/' in prefix or '\\' in prefix or prefix in ('.', '..')):
        raise ValueError('--prefix must be a filename prefix, not a path')
    override_root = Path(output_directory).expanduser().resolve() if output_directory is not None else None
    if override_root is not None and override_root.exists() and not override_root.is_dir():
        raise ValueError(f'output directory is not a directory: {override_root}')
    sources = {}
    for pattern in patterns:
        literal = Path(pattern).expanduser()
        matches = [str(literal)] if literal.is_file() else sorted(glob.glob(str(literal)))
        if not matches:
            raise ValueError(f'no files match: {pattern}')
        for match in matches:
            path = Path(match)
            if not path.is_file():
                raise ValueError(f'input is not a file: {path}')
            sources.setdefault(path.resolve(), path.absolute())
    jobs = []
    destinations = set()
    for source, input_path in sources.items():
        root = override_root if override_root is not None else input_path.parent.resolve()
        destination = root / output_filename(input_path.name, prefix)
        if destination.is_symlink() or not destination.resolve().is_relative_to(root):
            raise ValueError(f'unsafe output path: {destination}')
        if destination in sources:
            raise ValueError(f'output would replace an input: {destination}; choose another directory or --prefix')
        if destination in destinations:
            raise ValueError(f'inputs have the same output filename: {destination}; process them into separate directories')
        if destination.exists() and not destination.is_file():
            raise ValueError(f'output path is not a file: {destination}')
        destinations.add(destination)
        jobs.append(PhotoJob(source, destination))
    return tuple(jobs)


def open_photo(path):
    """Return an independent, oriented image and its original container format."""
    with Image.open(path) as source:
        if source.format not in SUPPORTED_FORMATS:
            raise ValueError(f'unsupported format {source.format}; supported formats: {", ".join(SUPPORTED_FORMATS)}')
        if getattr(source, 'n_frames', 1) != 1:
            raise ValueError('animated or multi-frame photos are not supported')
        if source.mode not in ('RGB', 'RGBA', 'L', 'LA', 'P', '1'):
            raise ValueError(f'unsupported image mode {source.mode}; convert a copy to RGB first')
        if source.info.get('icc_profile') and source.mode not in ('RGB', 'RGBA'):
            raise ValueError('profiled non-RGB images need conversion to RGB before stamping')
        source.load()
        # Unsupported metadata must be reported before writing a partial copy.
        # JPEG encoder bookkeeping is regenerated; PNG transparency is baked
        # into RGBA pixels rather than copied as a palette/color-key chunk.
        handled = set(COMMON_METADATA) | {'exif', 'transparency'}
        if source.format == 'JPEG':
            handled.update(JPEG_METADATA)
            handled.update(('jfif', 'jfif_version', 'jfif_unit', 'jfif_density', 'progressive', 'progression', 'adobe', 'adobe_transform'))
        else:
            handled.update(PNG_COLOR_CHUNKS)
            handled.update(key for key, value in source.info.items() if isinstance(value, str))
        unknown = set(source.info) - handled
        if unknown:
            raise ValueError(f'cannot preserve metadata fields: {", ".join(sorted(unknown))}')
        photo = ImageOps.exif_transpose(source)
        photo.load()
        return photo, source.format


def save_photo(result, original, container, destination, quality, overwrite=False):
    """Publish a complete file, replacing an existing output only when approved."""
    kwargs = {}
    for key in COMMON_METADATA:
        if key in original.info:
            kwargs[key] = original.info[key]
    source_exif = original.getexif()
    if source_exif:
        exif = Image.Exif()
        exif.load(source_exif.tobytes())
        # The orientation was normalized before rendering. Update existing
        # dimension tags to describe the resulting pixels, not the camera raster.
        for tag, value in ((ExifTags.Base.ImageWidth, result.width), (ExifTags.Base.ImageLength, result.height)):
            if tag in exif:
                exif[tag] = value
        if ExifTags.IFD.Exif in exif:
            nested = exif.get_ifd(ExifTags.IFD.Exif)
            for tag, value in ((ExifTags.Base.ExifImageWidth, result.width), (ExifTags.Base.ExifImageHeight, result.height)):
                if tag in nested:
                    nested[tag] = value
        kwargs['exif'] = exif.tobytes()
    if container == 'JPEG':
        result = result.convert('RGB')
        kwargs.update(quality=quality, subsampling=0)
        for key in JPEG_METADATA:
            if key in original.info:
                kwargs[key] = original.info[key]
    else:
        text = PngImagePlugin.PngInfo()
        for key, (chunk, factor) in PNG_COLOR_CHUNKS.items():
            if key in original.info:
                value = original.info[key]
                values = value if isinstance(value, tuple) else (value,)
                binary_format = '>B' if chunk == b'sRGB' else '>' + 'I' * len(values)
                text.add(chunk, struct.pack(binary_format, *(round(component * factor) for component in values)))
        for key, value in original.info.items():
            if isinstance(value, PngImagePlugin.iTXt):
                text.add_itxt(key, value, lang=value.lang, tkey=value.tkey)
            elif isinstance(value, str):
                text.add_itxt(key, value)
        kwargs['pnginfo'] = text
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.fluxcapacitor-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            result.save(stream, format=container, **kwargs)
        if overwrite:
            os.replace(temporary, destination)
        else:
            # Do not replace a file created after the overwrite decision.
            os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
