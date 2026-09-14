"""Shared helpers for the per-version document builders."""

from __future__ import annotations

from pathlib import PurePath
from urllib.parse import quote

from ..config import GenerationConfig
from ..models import DirectoryInfo

MANIFEST_FILENAME = "manifest.json"
COLLECTION_FILENAME = "collection.json"


def _url_path(rel_path: PurePath) -> str:
    return "/".join(quote(part, safe="") for part in rel_path.parts)


def manifest_id(config: GenerationConfig, dir_info: DirectoryInfo) -> str:
    """Absolute identifier for the manifest of dir_info."""
    if not dir_info.rel_path.parts:
        return f"{config.base_url}/{MANIFEST_FILENAME}"
    return f"{config.base_url}/{_url_path(dir_info.rel_path)}/{MANIFEST_FILENAME}"


def collection_id(config: GenerationConfig, dir_info: DirectoryInfo) -> str:
    """Absolute identifier for the collection of dir_info."""
    if not dir_info.rel_path.parts:
        return f"{config.base_url}/{COLLECTION_FILENAME}"
    return f"{config.base_url}/{_url_path(dir_info.rel_path)}/{COLLECTION_FILENAME}"


def child_document(config: GenerationConfig, child: DirectoryInfo) -> tuple[str, str]:
    """Return (id, kind) of the document a parent collection references for child.

    kind is "collection" or "manifest"; each builder maps it to its
    version-specific type value (e.g. "sc:Collection" in 2.x).
    """
    if child.has_collection:
        return collection_id(config, child), "collection"
    return manifest_id(config, child), "manifest"
