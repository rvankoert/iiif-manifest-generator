"""Allow running the package with `python -m iiif_manifest_generator`."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
