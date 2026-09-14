"""Command line interface."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import VERSIONS, GenerationConfig
from .generate import generate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="iiif-manifest-generator",
        description=(
            "Generate IIIF Presentation manifests (2.0, 2.1, 3.0, 4.0) and "
            "collections for a tree of image folders served through IIPImage."
        ),
    )
    parser.add_argument("root", type=Path, help="Root directory to scan (recursively).")
    parser.add_argument(
        "--version",
        required=True,
        choices=VERSIONS,
        help="IIIF Presentation API version to generate.",
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="Base URL used for manifest/collection identifiers and, by default, for the IIPImage server.",
    )
    parser.add_argument(
        "--image-base-url",
        default=None,
        help="Base URL of the IIPImage server. Defaults to --base-url.",
    )
    parser.add_argument(
        "--attribution",
        default=None,
        help="Attribution statement to embed in manifests.",
    )
    parser.add_argument(
        "--license",
        default=None,
        help="License URL to embed in manifests.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files/directories (leading '.').",
    )
    parser.add_argument(
        "--keep-extension",
        action="store_true",
        help="Keep the file extension in IIPImage identifiers.",
    )
    parser.add_argument(
        "--no-thumbnails",
        action="store_true",
        help="Do not emit thumbnail properties.",
    )
    parser.add_argument(
        "--image-api-3",
        action="store_true",
        help=(
            "Reference IIIF Image API 3 services (ImageService3) in 3.0/4.0 "
            "manifests instead of the default Image API 2 (ImageService2). "
            "Requires IIPImage configured with iiif3 = true. No effect for "
            "2.0/2.1, which always reference Image API 2."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print documents to stdout instead of writing files.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    log = logging.getLogger("iiif-manifest-generator")
    try:
        config = GenerationConfig(
            root=args.root,
            version=args.version,
            base_url=args.base_url,
            image_base_url=args.image_base_url,
            attribution=args.attribution,
            license=args.license,
            include_hidden=args.include_hidden,
            keep_extension=args.keep_extension,
            thumbnails=not args.no_thumbnails,
            image_api3=args.image_api_3,
            dry_run=args.dry_run,
        )
    except (ValueError, NotADirectoryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    docs = generate(config)
    if not docs:
        log.warning("No images found under %s; nothing was generated.", config.root)
        return 0
    log.info("Generated %d IIIF document(s) (Presentation %s).", len(docs), config.version)
    return 0
