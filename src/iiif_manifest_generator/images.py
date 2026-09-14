"""Image file detection and metadata extraction."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, UnidentifiedImageError

IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".webp", ".bmp"}
)

MIME_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


def is_image_file(path: Path) -> bool:
    """Return True if path has a recognized image extension (case-insensitive)."""
    return path.suffix.lower() in IMAGE_EXTENSIONS


def get_image_size(path: Path) -> tuple[int, int]:
    """Return (width, height) in pixels.

    Raises:
        ValueError: if the file cannot be opened as an image.
    """
    try:
        with Image.open(path) as img:
            return int(img.width), int(img.height)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"could not read image dimensions for {path}: {exc}") from exc


def mime_type(path: Path) -> str:
    """Return the MIME type for the file's extension."""
    return MIME_TYPES[path.suffix.lower()]
