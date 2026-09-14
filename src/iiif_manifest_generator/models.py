"""Data model shared by the scanner and the document builders."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .iip import IipUrls


@dataclass
class ImageInfo:
    """One image file found in a directory."""

    path: Path
    rel_path: Path          # relative to the scan root
    identifier: str         # IIPImage identifier (URL-quoted, extension stripped by default)
    width: int
    height: int
    format_ext: str         # e.g. ".jpg"
    mime: str               # e.g. "image/jpeg"
    iip: IipUrls


@dataclass
class DirectoryInfo:
    """One directory in the scan tree."""

    path: Path
    rel_path: Path          # relative to the scan root; Path("") for the root itself
    is_root: bool
    images: list[ImageInfo] = field(default_factory=list)
    children: list[DirectoryInfo] = field(default_factory=list)
    produces_documents: bool = False  # filled in post-order by the scanner

    @property
    def label(self) -> str:
        return self.path.name or str(self.path)

    @property
    def has_manifest(self) -> bool:
        return bool(self.images)

    @property
    def documentable_children(self) -> list[DirectoryInfo]:
        return [c for c in self.children if c.produces_documents]

    @property
    def has_collection(self) -> bool:
        # A collection is created only when the directory contains other
        # directories AND something in it (itself or its subdirectories)
        # produces a document. This guarantees the collection is never empty
        # (an empty 'items' would be invalid in IIIF 3.0/4.0).
        return self.produces_documents and bool(self.children)


@dataclass
class GeneratedDocument:
    """A finished IIIF document ready to be written to disk."""

    dir_info: DirectoryInfo
    kind: str               # "manifest" or "collection"
    data: dict              # the JSON-serializable IIIF document
    filename: str           # "manifest.json" or "collection.json"
