"""Generation configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlsplit

VERSIONS: tuple[str, ...] = ("2.0", "2.1", "3.0", "4.0")


@dataclass
class GenerationConfig:
    """All user-supplied options for one generation run."""

    root: Path
    version: str
    base_url: str
    image_base_url: str | None = None
    attribution: str | None = None
    license: str | None = None
    include_hidden: bool = False
    keep_extension: bool = False
    thumbnails: bool = True
    image_api3: bool = False
    dry_run: bool = False

    def __post_init__(self) -> None:
        if self.version not in VERSIONS:
            raise ValueError(
                f"version must be one of {', '.join(VERSIONS)}, got {self.version!r}"
            )
        self.root = Path(self.root).expanduser().resolve()
        if not self.root.is_dir():
            raise NotADirectoryError(f"root is not a directory: {self.root}")
        self.base_url = self._normalize_url(self.base_url, "base_url")
        if self.image_base_url is None:
            self.image_base_url = self.base_url
        else:
            self.image_base_url = self._normalize_url(
                self.image_base_url, "image_base_url"
            )

    @property
    def image_api_version(self) -> str:
        """IIIF Image API version referenced by the generated documents.

        Presentation 2.x always references Image API 2. Presentation 3.0/4.0
        reference Image API 3 only when image_api3 is set; otherwise they
        reference Image API 2 (the default).
        """
        if self.version in ("2.0", "2.1"):
            return "2"
        return "3" if self.image_api3 else "2"

    @staticmethod
    def _normalize_url(value: str, name: str) -> str:
        """Validate and normalize a base URL (must be http(s); no trailing /).

        The URL path (and query, if any) is percent-encoded so that every
        document identifier built from the base URL is a valid IRI, even when
        the URL contains spaces or other unsafe characters (e.g. a scan
        directory whose name contains spaces). Already-percent-encoded
        sequences are left untouched (no double-encoding); the scheme,
        netloc and fragment are not modified.
        """
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must not be empty")
        for prefix in ("http://", "https://"):
            if value.startswith(prefix):
                parts = urlsplit(value)
                path = quote(parts.path, safe="/%")
                query = (
                    quote(parts.query, safe="=&%") if parts.query else parts.query
                )
                return parts._replace(path=path, query=query).geturl().rstrip("/")
        raise ValueError(f"{name} must start with http:// or https://, got {value!r}")
