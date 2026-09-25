"""IIIF Image API URL construction for IIPImage-served images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from urllib.parse import quote


def build_identifier(rel_path: PurePath, keep_extension: bool) -> str:
    """Build the IIPImage identifier from a path relative to the scan root.

    Default behaviour strips the file extension (at the last dot) and
    URL-quotes every path segment.
    """
    parts = list(rel_path.parts)
    if not keep_extension:
        name = parts[-1]
        if "." in name:
            name = name.rsplit(".", 1)[0]
        parts[-1] = name
    return "/".join(quote(part, safe="") for part in parts)


@dataclass(frozen=True)
class IipUrls:
    """All IIIF Image API URLs for one image."""

    info_url: str
    full_url: str
    thumbnail_url: str | None


def build_iip_urls(
    image_base_url: str,
    identifier: str,
    extension: str,
    image_api_version: str,
    thumbnails: bool,
) -> IipUrls:
    """Build the image service id, full-size render and thumbnail URLs.

    ``info_url`` is the IIIF Image API service id, i.e. the base URL
    ``{base}/{identifier}``; viewers fetch ``{info_url}/info.json`` from it.
    Image API 2.x and 3.x share the URL syntax
    {base}/{identifier}/{region}/{size}/{rotation}/{quality}.{format};
    thumbnails use the forced-size token ``!256,256``, which both versions
    (and IIPImage, via ``sizeByForcedWh``) support.
    """
    ext = extension.lstrip(".").lower()
    info_url = f"{image_base_url}/{identifier}"
    full_url = f"{image_base_url}/{identifier}/full/full/0/default.{ext}"
    thumbnail_url = None
    if thumbnails:
        thumbnail_url = f"{image_base_url}/{identifier}/full/!256,256/0/default.{ext}"
    return IipUrls(info_url=info_url, full_url=full_url, thumbnail_url=thumbnail_url)
