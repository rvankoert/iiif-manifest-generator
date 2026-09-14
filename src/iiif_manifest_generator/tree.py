"""Recursive directory scanning."""

from __future__ import annotations

import logging
from pathlib import Path

from .config import GenerationConfig
from .images import get_image_size, is_image_file, mime_type
from .iip import build_identifier, build_iip_urls
from .models import DirectoryInfo, ImageInfo

log = logging.getLogger("iiif-manifest-generator")


def scan_tree(config: GenerationConfig) -> DirectoryInfo:
    """Walk config.root and return the root DirectoryInfo.

    Entries are processed in case-insensitive name order. Hidden entries
    (leading '.') are skipped unless config.include_hidden is set.
    Symlinks are skipped to avoid loops. Unreadable image files are
    skipped with a warning.
    """
    root = DirectoryInfo(path=config.root, rel_path=Path(""), is_root=True)
    _populate(config, root, config.root, Path(""))
    _finalize(root)
    return root


def _populate(
    config: GenerationConfig, info: DirectoryInfo, dir_path: Path, rel_path: Path
) -> None:
    try:
        entries = sorted(dir_path.iterdir(), key=lambda p: (p.name.lower(), p.name))
    except PermissionError as exc:
        log.warning("cannot read directory %s: %s", dir_path, exc)
        return

    for entry in entries:
        if entry.name.startswith(".") and not config.include_hidden:
            continue
        if entry.is_symlink():
            continue
        if entry.is_dir():
            child = DirectoryInfo(
                path=entry, rel_path=rel_path / entry.name, is_root=False
            )
            info.children.append(child)
            _populate(config, child, entry, rel_path / entry.name)
        elif entry.is_file():
            if not is_image_file(entry):
                continue
            try:
                width, height = get_image_size(entry)
            except ValueError as exc:
                log.warning("skipping %s: %s", entry, exc)
                continue
            rel = rel_path / entry.name
            ext = entry.suffix.lower()
            info.images.append(
                ImageInfo(
                    path=entry,
                    rel_path=rel,
                    identifier=build_identifier(rel, config.keep_extension),
                    width=width,
                    height=height,
                    format_ext=ext,
                    mime=mime_type(entry),
                    iip=build_iip_urls(
                        image_base_url=config.image_base_url,
                        identifier=build_identifier(rel, config.keep_extension),
                        extension=ext,
                        image_api_version=config.image_api_version,
                        thumbnails=config.thumbnails,
                    ),
                )
            )


def _finalize(info: DirectoryInfo) -> None:
    """Post-order: a directory produces documents iff it has images or a
    subdirectory that produces documents (and it has subdirectories to wrap)."""
    for child in info.children:
        _finalize(child)
    info.produces_documents = bool(info.images) or bool(
        info.children and info.documentable_children
    )
