# IIIF Manifest Generator — Implementation Plan

- **Date:** 2026-07-11
- **Plan version:** 1 (all Questions & Ambiguities resolved; decisions incorporated)
- **Target executor:** Qwen3.8-27B
- **Project root:** `/home/rutger/src/iiif-manifest-generator`
- **Goal:** Generate **valid** IIIF Presentation manifests (2.0, 2.1, 3.0, 4.0) for a tree of (nested) folders of images served via **IIPImage**.
  - Every folder containing images → its own IIIF Presentation **Manifest** (`manifest.json`).
  - Every folder containing subfolders → a IIIF **Collection** (`collection.json`).
  - The IIIF Presentation version (2.0 / 2.1 / 3.0 / 4.0) is selectable per run.
  - The base URL for the images (IIPImage) and for the document IDs is user-supplied (`--base-url`, required).
  - Output must pass the official validator: https://github.com/IIIF/presentation-validator

## Environment (verified 2026-07-11)

| Fact | Value |
| --- | --- |
| Python | 3.12.8 (miniforge3), pip 24.3.1, `venv` available |
| Preinstalled | Pillow 10.4.0, pytest 8.3.3, jsonschema 4.26.0 |
| Project directory | **empty** (no code, no git repo) |
| Network | available (GitHub, PyPI, iiif.io reachable) |
| Validator | `IIIF/presentation-validator` is a **Python package** (pip-installable). The CLI `iiif-validator` supports **local files** and directories: `iiif-validator validate --version {1.0,2.0,2.1,3.0,4.0} <url-or-file>` and `iiif-validator validate-dir --version <v> <dir>` (validates every `.json` recursively, exits non-zero when any document fails). 2.0/2.1 are validated by `iiif_prezi`'s ManifestReader (may need network to fetch the JSON-LD context); 3.0 via a bundled Draft-7 JSON schema (offline); 4.0 via bundled Draft-2020-12 schemas + a unique-ID check (offline). |

Key validator schema facts (verified against the repo's `schema/` files):
- 3.0 schema: resource `type` is a free `{"type": "string"}` → an annotation body with `type: "ImageService2"` in a 3.0 document is accepted.
- 4.0 schema: annotation body `type` is an **enum** `["Image", "Audio", "Video", "Model", "Dataset", "Text"]` (so 4.0 bodies are `type: "Image"` with a `service` array); `Service.json` accepts **both** 3-style service entries (`id` + `type`, any string) and 2-style entries (`@id` + `@type`, any string).

## Systematic analysis

### Deconstructing the problem

1. **Tree scanning & classification** — recursively walk a root folder; classify each directory: has images → needs a Manifest; has subdirectories that themselves produce documents → needs a Collection; both → both. Must handle: empty dirs, hidden dirs, symlinks, corrupt images, permission errors.
2. **Version-adaptive IIIF document generation** — the same logical model must serialize into 4 structurally different dialects:
   - **2.0**: `@id`/`@type`, `@context: http://iiif.io/api/presentation/2/context.json`, `sc:*` types, `sequences` → `canvases` → `images` → `resource`/`on`, `ImageService2` + 2.0 profile, `members` on collections, string labels.
   - **2.1**: `id`/`type` (but `@context` stays), 2.1 context, Image API 2.1 profile, otherwise as 2.0.
   - **3.0**: `https://iiif.io/api/presentation/3/context.json`, LanguageMap labels (`{"none": [...]}`), `items` (no sequences), Canvas → `AnnotationPage` → `Annotation` with `body`/`target`, `license`/`attribution` **removed** (use `rights`/`requiredStatement`), `members` → `items`, thumbnails as arrays.
   - **4.0**: `https://iiif.io/api/presentation/4/context.json`, plain-string labels allowed, `motivation` as an array per official examples, body = `Image` + `service` array (body `type` is an enum), canvas `width`/`height` required, all IDs in a document must be unique (official validator check).
3. **IIPImage integration** — map each image file to an IIPImage identifier and build Image API 2/3 URLs: `{base}/{id}/info.json`, `{base}/{id}/full/full/0/default.{ext}`, thumbnails with **Image-API-specific size syntax** (`square:256` is only valid in Image API 2.x; `square` in 3.x).
4. **Validation** — the official `iiif-validator` as the validity gate: structural unit tests + `validate-dir` e2e for every version (and both Image API modes for 3.0/4.0).

### Brainstormed alternatives

| Approach | Pros | Cons | Verdict |
| --- | --- | --- | --- |
| A. One big script | Fewest files | 4× copy-paste, untestable, hard for a 27B model to localize bugs | ❌ |
| B. Logical model + per-version builder modules (strategy pattern) | One scan, four thin serializers; each file small, explicit, unit-testable; duplication is *controlled* | More files | ✅ **Chosen** — explicit per-version builders are safest for Qwen (no clever abstraction to get wrong) |
| C. Jinja2/JSON templates per version | Flexible | Indirection hides errors; adds a dependency; template bugs hard to debug | ❌ |
| D. Generate via the `iiif_prezi` library | Reuses a library | Supports 2.1/3.0 well, **not 4.0**; fights our exact structural needs | ❌ |
### Pitfalls identified (and the design decisions taken)

- **Empty collections are invalid in 3.0/4.0** (`items` required) → a directory only gets a Collection when it has subfolders **and** it (or its subfolders) actually contains images; such dirs are also excluded from parent collection references (Section 4, items 1–2).
- **3.0/4.0 must not emit `license`/`attribution`** (not in their schemas) → use `rights` + `requiredStatement`.
- **4.0 unique-ID check** in the official validator → all IDs derive from globally-unique document-ID paths (`…/canvas/N`, `…/page/1`, `…/page/1/annotation/1`).
- **Thumbnail size syntax differs between Image API 2 and 3** → per-Image-API thumbnail URLs (`square:256` vs `square`); the thumbnail syntax follows the *image* API version, not the presentation version.
- **4.0 body type enum** (schema-verified: `Body.json` → `Resource.json`) → 4.0 bodies are always `type: "Image"` with a `service` array; the service `type` string is unconstrained.
- **4.0 2-style services** (schema-verified: `Service.json` `if/then/else`) → with the default Image API 2, the 4.0 service entry is `{"@id": info.json, "@type": "ImageService2", "profile": …}`.
- **2.x validator needs network** (JSON-LD context fetch) → the e2e test skips when `iiif-validator` is not installed; 3.0/4.0 validation stays fully offline.
- **IIPImage identifier scheme is unknown** → default = path relative to the scan root, extension stripped, URL-quoted; overridable with `--keep-extension` (Q2, resolved).
- Corrupt images, hidden dirs, symlink loops, trailing slashes, non-HTTP base URLs, multi-dot filenames, overwrite behavior — all handled explicitly (Section 4).

### Draft → critique → refine

- Draft 1 gave a Collection to *every* folder with images → violated "folders containing *another folder* must get a collection" → refined to the `produces_documents` rule.
- Draft 1 used `attribution`/`license` in 3.0 → schema-invalid → replaced with `requiredStatement`/`rights`.
- Draft 1 used a bare service as the 4.0 annotation body → the 4.0 schema's body type enum forces body = `Image` + `service` array (matching official 4.0 examples), with `motivation: ["painting"]`.
- Draft 1 used a single-object `thumbnail` in 3.0 → the 3.0 schema wants an array → arrays for 3.0/4.0.
- Plan v1 defaulted 3.0/4.0 manifests to `ImageService3` → the user chose **Image API 2 by default, opt-in `--image-api-3`** (Q3) → `GenerationConfig.image_api_version` + branching in the v30/v40 builders; both service forms verified acceptable by the official schemas (see Environment section).

# 1. Architectural Overview

A single recursive scan builds a version-neutral tree model (`DirectoryInfo`/`ImageInfo`); four small, deliberately explicit builder modules (one per IIIF version) serialize that model, so version quirks (property naming, contexts, sequences vs items, Image API profiles) are isolated in one place each and can be unit-tested and validator-tested independently. This is optimal because the scan, image probing (Pillow), and IIPImage URL logic are shared once, while the parts that actually differ between 2.0/2.1/3.0/4.0 are isolated in tiny, readable files — the shape of code a 27B model can implement and debug without losing track. Validation is built-in via the official `iiif-validator` (which supports local files and directory validation with a real exit code), making "must be valid" a repeatable, automatable guarantee.
# 2. File Modification Index

Project root: `/home/rutger/src/iiif-manifest-generator` (currently **empty** — every file is CREATE; nothing modified or deleted).

| # | File | Action |
| --- | --- | --- |
| 1 | `plans/2026-07-11_v1_iiif-manifest-generator-plan.md` | CREATE (this plan) |
| 2 | `pyproject.toml` | CREATE |
| 3 | `.gitignore` | CREATE |
| 4 | `README.md` | CREATE |
| 5 | `src/iiif_manifest_generator/__init__.py` | CREATE |
| 6 | `src/iiif_manifest_generator/__main__.py` | CREATE |
| 7 | `src/iiif_manifest_generator/config.py` | CREATE |
| 8 | `src/iiif_manifest_generator/images.py` | CREATE |
| 9 | `src/iiif_manifest_generator/iip.py` | CREATE |
| 10 | `src/iiif_manifest_generator/models.py` | CREATE |
| 11 | `src/iiif_manifest_generator/tree.py` | CREATE |
| 12 | `src/iiif_manifest_generator/builders/__init__.py` | CREATE |
| 13 | `src/iiif_manifest_generator/builders/base.py` | CREATE |
| 14 | `src/iiif_manifest_generator/builders/v20.py` | CREATE |
| 15 | `src/iiif_manifest_generator/builders/v21.py` | CREATE |
| 16 | `src/iiif_manifest_generator/builders/v30.py` | CREATE |
| 17 | `src/iiif_manifest_generator/builders/v40.py` | CREATE |
| 18 | `src/iiif_manifest_generator/writer.py` | CREATE |
| 19 | `src/iiif_manifest_generator/generate.py` | CREATE |
| 20 | `src/iiif_manifest_generator/cli.py` | CREATE |
| 21 | `tests/conftest.py` | CREATE |
| 22 | `tests/test_iip.py` | CREATE |
| 23 | `tests/test_tree.py` | CREATE |
| 24 | `tests/test_builders.py` | CREATE |
| 25 | `tests/test_generate.py` | CREATE |
| 26 | `tests/test_e2e_validator.py` | CREATE |

# 3. Step-by-Step Implementation Plan

> Global conventions for every step: files use `from __future__ import annotations`; 4-space indent; relative paths below are relative to `/home/rutger/src/iiif-manifest-generator`. All code blocks are **complete file contents** unless stated otherwise — copy them verbatim.

## Step 0: Save this plan document

- **Files to touch:** `plans/2026-07-11_v1_iiif-manifest-generator-plan.md`
- **Action:** Already satisfied by this file. If re-executing from scratch: `mkdir -p plans` and write the full plan text to this path.
- **Verification:** `ls -la plans/ && wc -l plans/2026-07-11_v1_iiif-manifest-generator-plan.md` — file exists and is non-empty.
## Step 1: Project scaffolding

- **Files to touch:** `pyproject.toml`, `.gitignore`, `src/iiif_manifest_generator/__init__.py`, `src/iiif_manifest_generator/__main__.py`
- **Action:**
  1. Create `pyproject.toml` with exactly:
```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "iiif-manifest-generator"
version = "0.1.0"
description = "Generate IIIF Presentation manifests (2.0, 2.1, 3.0, 4.0) for folders of images served via IIPImage"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
  "Pillow>=9.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=7.0",
]

[project.scripts]
iiif-manifest-generator = "iiif_manifest_generator.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```
  2. Create `.gitignore` with exactly:
```
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.pytest_cache/
tools/
build/
dist/
```
  3. Create `src/iiif_manifest_generator/__init__.py` with exactly:
```python
"""Generate IIIF Presentation manifests and collections for folders of images."""

__version__ = "0.1.0"
```
  4. Create `src/iiif_manifest_generator/__main__.py` with exactly:
```python
"""Allow running the package with `python -m iiif_manifest_generator`."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```
- **Verification:** `pip install -e .` succeeds and `python -c "import iiif_manifest_generator; print(iiif_manifest_generator.__version__)"` prints `0.1.0`. (Do **not** run `python -m iiif_manifest_generator` yet — `cli.py` comes in Step 13.)
## Step 2: Configuration module

- **Files to touch:** `src/iiif_manifest_generator/config.py`
- **Action:** Create with exactly:
```python
"""Generation configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must not be empty")
        for prefix in ("http://", "https://"):
            if value.startswith(prefix):
                return value.rstrip("/")
        raise ValueError(f"{name} must start with http:// or https://, got {value!r}")
```
- **Verification:**
```bash
python - <<'EOF'
from pathlib import Path
from iiif_manifest_generator.config import GenerationConfig
import tempfile
d = tempfile.mkdtemp()
c = GenerationConfig(root=Path(d), version="3.0", base_url="http://x.org/")
assert c.base_url == "http://x.org" and c.image_base_url == "http://x.org"
assert c.image_api_version == "2"
assert GenerationConfig(root=Path(d), version="4.0", base_url="http://x", image_api3=True).image_api_version == "3"
assert GenerationConfig(root=Path(d), version="2.1", base_url="http://x", image_api3=True).image_api_version == "2"
try:
    GenerationConfig(root=Path(d), version="9.9", base_url="http://x")
except ValueError as e:
    print("OK version:", e)
try:
    GenerationConfig(root=Path(d), version="3.0", base_url="ftp://x")
except ValueError as e:
    print("OK url:", e)
print("OK config")
EOF
```
Both `OK ...` lines print, then `OK config`, with no traceback.
## Step 3: Image detection & dimension probing

- **Files to touch:** `src/iiif_manifest_generator/images.py`
- **Action:** Create with exactly:
```python
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
```
- **Verification:**
```bash
python - <<'EOF'
import tempfile
from pathlib import Path
from PIL import Image
from iiif_manifest_generator.images import is_image_file, get_image_size, mime_type
d = Path(tempfile.mkdtemp())
assert is_image_file(Path("a.JPG")) and not is_image_file(Path("a.pdf"))
bad = d / "x.jpg"; bad.write_bytes(b"junk")
try:
    get_image_size(bad)
    raise SystemExit("should have raised")
except ValueError as e:
    print("OK corrupt:", e)
q = d / "ok.png"; Image.new("RGB", (11, 22), (0, 0, 0)).save(q)
assert get_image_size(q) == (11, 22) and mime_type(q) == "image/png"
print("OK images module")
EOF
```
Prints `OK corrupt: ...` then `OK images module`.
## Step 4: IIPImage URL construction

- **Files to touch:** `src/iiif_manifest_generator/iip.py`
- **Action:** Create with exactly (note: there is **no** presentation→image API mapping function here; the version comes from `GenerationConfig.image_api_version`, Step 2):
```python
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
    """Build info.json, full-size render and thumbnail URLs.

    Image API 2.x and 3.x share the URL syntax
    {base}/{identifier}/{region}/{size}/{rotation}/{quality}.{format};
    only the allowed size tokens differ ('square:256' vs 'square').
    """
    ext = extension.lstrip(".").lower()
    info_url = f"{image_base_url}/{identifier}/info.json"
    full_url = f"{image_base_url}/{identifier}/full/full/0/default.{ext}"
    thumbnail_url = None
    if thumbnails:
        if image_api_version == "2":
            thumbnail_url = f"{image_base_url}/{identifier}/full/square:256/0/default.{ext}"
        else:
            thumbnail_url = f"{image_base_url}/{identifier}/full/square/0/default.{ext}"
    return IipUrls(info_url=info_url, full_url=full_url, thumbnail_url=thumbnail_url)
```
- **Verification:**
```bash
python - <<'EOF'
from pathlib import PurePath
from iiif_manifest_generator.iip import build_identifier, build_iip_urls
assert build_identifier(PurePath("alpha/nested/d.jpg"), False) == "alpha/nested/d"
assert build_identifier(PurePath("a.jpg"), True) == "a.jpg"
assert build_identifier(PurePath("my folder/img 1.jpg"), False) == "my%20folder/img%201"
u = build_iip_urls("http://img", "a/b/c", ".jpg", "2", True)
assert u.info_url == "http://img/a/b/c/info.json"
assert u.full_url == "http://img/a/b/c/full/full/0/default.jpg"
assert u.thumbnail_url == "http://img/a/b/c/full/square:256/0/default.jpg"
v = build_iip_urls("http://img", "x", ".png", "3", True)
assert v.thumbnail_url == "http://img/x/full/square/0/default.png"
assert build_iip_urls("http://img", "x", ".png", "3", False).thumbnail_url is None
print("OK iip module")
EOF
```
Prints `OK iip module`.
## Step 5: Shared data model

- **Files to touch:** `src/iiif_manifest_generator/models.py`
- **Action:** Create with exactly:
```python
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
```
- **Verification:**
```bash
python - <<'EOF'
from pathlib import Path
from iiif_manifest_generator.models import DirectoryInfo
r = DirectoryInfo(path=Path("/x/y"), rel_path=Path(""), is_root=True)
assert r.label == "y" and not r.has_manifest and not r.has_collection
print("OK models")
EOF
```
Prints `OK models`.
## Step 6: Recursive tree scanner

- **Files to touch:** `src/iiif_manifest_generator/tree.py`
- **Action:** Create with exactly:
```python
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
```
- **Verification:**
```bash
python - <<'EOF'
import tempfile
from pathlib import Path
from PIL import Image
from iiif_manifest_generator.config import GenerationConfig
from iiif_manifest_generator.tree import scan_tree
d = Path(tempfile.mkdtemp()) / "root"
(d / "sub").mkdir(parents=True)
Image.new("RGB", (5, 5), (0, 0, 0)).save(d / "a.jpg")
Image.new("RGB", (6, 6), (0, 0, 0)).save(d / "sub" / "b.png")
root = scan_tree(GenerationConfig(root=d, version="3.0", base_url="http://h"))
assert root.has_manifest and root.has_collection
assert root.children[0].has_manifest and not root.children[0].has_collection
assert root.images[0].width == 5 and root.images[0].iip.info_url == "http://h/a/info.json"
assert root.images[0].iip.thumbnail_url == "http://h/a/full/square:256/0/default.jpg"
print("OK tree module")
EOF
```
Prints `OK tree module`.
## Step 7: Shared builder helpers

- **Files to touch:** `src/iiif_manifest_generator/builders/base.py`
- **Action:** Create the package directory `src/iiif_manifest_generator/builders/` and create `base.py` with exactly:
```python
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
```
- **Verification:**
```bash
python -c "from iiif_manifest_generator.builders.base import manifest_id, collection_id, child_document; print('OK base')"
```
Prints `OK base`.
## Step 8: IIIF 2.0 builder

- **Files to touch:** `src/iiif_manifest_generator/builders/v20.py`
- **Action:** Create with exactly (complete file):
```python
"""IIIF Presentation API 2.0 document builders."""

from __future__ import annotations

from ..config import GenerationConfig
from ..models import DirectoryInfo, GeneratedDocument, ImageInfo
from .base import (
    COLLECTION_FILENAME,
    MANIFEST_FILENAME,
    child_document,
    collection_id,
    manifest_id,
)

CONTEXT = "http://iiif.io/api/presentation/2/context.json"
TYPE_NAMES = {"manifest": "sc:Manifest", "collection": "sc:Collection"}
IMAGE_SERVICE_PROFILE = "http://iiif.io/api/image/2/level0.json"


def _metadata(label: str) -> list[dict[str, str]]:
    return [
        {
            "label": "Description",
            "value": (
                f"IIIF Presentation 2.0 manifest generated by "
                f"iiif-manifest-generator for {label}"
            ),
        }
    ]


def _canvas(
    config: GenerationConfig, dir_info: DirectoryInfo, info: ImageInfo, index: int
) -> dict:
    canvas_id = f"{manifest_id(config, dir_info)}/canvas/{index}"
    return {
        "@id": canvas_id,
        "@type": "sc:Canvas",
        "label": info.rel_path.name,
        "width": info.width,
        "height": info.height,
        "images": [
            {
                "@type": "oa:Annotation",
                "motivation": "sc:painting",
                "resource": {
                    "@id": info.iip.full_url,
                    "@type": "dctypes:Image",
                    "format": info.mime,
                    "width": info.width,
                    "height": info.height,
                    "service": {
                        "@id": info.iip.info_url,
                        "@type": "ImageService2",
                        "profile": IMAGE_SERVICE_PROFILE,
                    },
                    "on": canvas_id,
                },
            }
        ],
    }


def build_manifest(config: GenerationConfig, dir_info: DirectoryInfo) -> GeneratedDocument:
    doc_id = manifest_id(config, dir_info)
    doc: dict = {
        "@context": CONTEXT,
        "@id": doc_id,
        "@type": "sc:Manifest",
        "label": dir_info.label,
        "metadata": _metadata(dir_info.label),
        "sequences": [
            {
                "@id": f"{doc_id}/sequence/normal",
                "@type": "sc:Sequence",
                "canvases": [
                    _canvas(config, dir_info, info, i)
                    for i, info in enumerate(dir_info.images, start=1)
                ],
            }
        ],
    }
    if config.attribution:
        doc["attribution"] = config.attribution
    if config.license:
        doc["license"] = config.license
    if config.thumbnails and dir_info.images and dir_info.images[0].iip.thumbnail_url:
        first = dir_info.images[0]
        doc["thumbnail"] = {"@id": first.iip.thumbnail_url, "format": first.mime}
    return GeneratedDocument(
        dir_info=dir_info, kind="manifest", data=doc, filename=MANIFEST_FILENAME
    )


def build_collection(
    config: GenerationConfig, dir_info: DirectoryInfo
) -> GeneratedDocument:
    doc_id = collection_id(config, dir_info)
    members: list[dict] = []
    if dir_info.has_manifest:
        members.append(
            {
                "@id": manifest_id(config, dir_info),
                "@type": "sc:Manifest",
                "label": dir_info.label,
            }
        )
    for child in dir_info.documentable_children:
        child_id, kind = child_document(config, child)
        members.append(
            {"@id": child_id, "@type": TYPE_NAMES[kind], "label": child.label}
        )
    doc = {
        "@context": CONTEXT,
        "@id": doc_id,
        "@type": "sc:Collection",
        "label": dir_info.label,
        "metadata": _metadata(dir_info.label),
        "members": members,
    }
    return GeneratedDocument(
        dir_info=dir_info, kind="collection", data=doc, filename=COLLECTION_FILENAME
    )
```
- **Verification:**
```bash
python - <<'EOF'
import json, tempfile
from pathlib import Path
from PIL import Image
from iiif_manifest_generator.config import GenerationConfig
from iiif_manifest_generator.tree import scan_tree
from iiif_manifest_generator.builders.v20 import build_manifest, build_collection
d = Path(tempfile.mkdtemp()) / "root"
(d / "sub").mkdir(parents=True)
Image.new("RGB", (10, 20), (0, 0, 0)).save(d / "a.jpg")
Image.new("RGB", (30, 40), (0, 0, 0)).save(d / "sub" / "b.png")
config = GenerationConfig(root=d, version="2.0", base_url="http://h")
root = scan_tree(config)
m = build_manifest(config, root).data
assert m["@context"] == "http://iiif.io/api/presentation/2/context.json"
assert m["@type"] == "sc:Manifest" and m["@id"] == "http://h/manifest.json"
assert m["sequences"][0]["@type"] == "sc:Sequence"
assert len(m["sequences"][0]["canvases"]) == 1
json.dumps(m)
c = build_collection(config, root).data
assert c["@type"] == "sc:Collection"
assert len(c["members"]) == 2  # own manifest + sub/ manifest
print("OK v20")
EOF
```
Prints `OK v20` with no traceback.
## Step 9: IIIF 2.1 builder

- **Files to touch:** `src/iiif_manifest_generator/builders/v21.py`
- **Action:** Create with exactly (complete file; identical to Step 8's file except: `id`/`type` instead of `@id`/`@type` everywhere, the 2.1 context, the 2.1 image profile, and the metadata text says 2.1):
```python
"""IIIF Presentation API 2.1 document builders."""

from __future__ import annotations

from ..config import GenerationConfig
from ..models import DirectoryInfo, GeneratedDocument, ImageInfo
from .base import (
    COLLECTION_FILENAME,
    MANIFEST_FILENAME,
    child_document,
    collection_id,
    manifest_id,
)

CONTEXT = "http://iiif.io/api/presentation/2.1/context.json"
TYPE_NAMES = {"manifest": "sc:Manifest", "collection": "sc:Collection"}
IMAGE_SERVICE_PROFILE = "http://iiif.io/api/image/2.1/level0.json"


def _metadata(label: str) -> list[dict[str, str]]:
    return [
        {
            "label": "Description",
            "value": (
                f"IIIF Presentation 2.1 manifest generated by "
                f"iiif-manifest-generator for {label}"
            ),
        }
    ]


def _canvas(
    config: GenerationConfig, dir_info: DirectoryInfo, info: ImageInfo, index: int
) -> dict:
    canvas_id = f"{manifest_id(config, dir_info)}/canvas/{index}"
    return {
        "id": canvas_id,
        "type": "sc:Canvas",
        "label": info.rel_path.name,
        "width": info.width,
        "height": info.height,
        "images": [
            {
                "type": "oa:Annotation",
                "motivation": "sc:painting",
                "resource": {
                    "id": info.iip.full_url,
                    "type": "dctypes:Image",
                    "format": info.mime,
                    "width": info.width,
                    "height": info.height,
                    "service": {
                        "id": info.iip.info_url,
                        "type": "ImageService2",
                        "profile": IMAGE_SERVICE_PROFILE,
                    },
                    "on": canvas_id,
                },
            }
        ],
    }


def build_manifest(config: GenerationConfig, dir_info: DirectoryInfo) -> GeneratedDocument:
    doc_id = manifest_id(config, dir_info)
    doc: dict = {
        "@context": CONTEXT,
        "id": doc_id,
        "type": "sc:Manifest",
        "label": dir_info.label,
        "metadata": _metadata(dir_info.label),
        "sequences": [
            {
                "id": f"{doc_id}/sequence/normal",
                "type": "sc:Sequence",
                "canvases": [
                    _canvas(config, dir_info, info, i)
                    for i, info in enumerate(dir_info.images, start=1)
                ],
            }
        ],
    }
    if config.attribution:
        doc["attribution"] = config.attribution
    if config.license:
        doc["license"] = config.license
    if config.thumbnails and dir_info.images and dir_info.images[0].iip.thumbnail_url:
        first = dir_info.images[0]
        doc["thumbnail"] = {"id": first.iip.thumbnail_url, "format": first.mime}
    return GeneratedDocument(
        dir_info=dir_info, kind="manifest", data=doc, filename=MANIFEST_FILENAME
    )


def build_collection(
    config: GenerationConfig, dir_info: DirectoryInfo
) -> GeneratedDocument:
    doc_id = collection_id(config, dir_info)
    members: list[dict] = []
    if dir_info.has_manifest:
        members.append(
            {
                "id": manifest_id(config, dir_info),
                "type": "sc:Manifest",
                "label": dir_info.label,
            }
        )
    for child in dir_info.documentable_children:
        child_id, kind = child_document(config, child)
        members.append(
            {"id": child_id, "type": TYPE_NAMES[kind], "label": child.label}
        )
    doc = {
        "@context": CONTEXT,
        "id": doc_id,
        "type": "sc:Collection",
        "label": dir_info.label,
        "metadata": _metadata(dir_info.label),
        "members": members,
    }
    return GeneratedDocument(
        dir_info=dir_info, kind="collection", data=doc, filename=COLLECTION_FILENAME
    )
```
- **Verification:**
```bash
python - <<'EOF'
import tempfile
from pathlib import Path
from PIL import Image
from iiif_manifest_generator.config import GenerationConfig
from iiif_manifest_generator.tree import scan_tree
from iiif_manifest_generator.builders.v21 import build_manifest
d = Path(tempfile.mkdtemp()) / "root"; d.mkdir()
Image.new("RGB", (10, 20), (0, 0, 0)).save(d / "a.jpg")
config = GenerationConfig(root=d, version="2.1", base_url="http://h")
m = build_manifest(config, scan_tree(config)).data
assert m["@context"] == "http://iiif.io/api/presentation/2.1/context.json"
assert m["id"] == "http://h/manifest.json" and m["type"] == "sc:Manifest"
assert "@id" not in m and "@type" not in m
assert m["sequences"][0]["type"] == "sc:Sequence"
assert m["sequences"][0]["canvases"][0]["images"][0]["resource"]["service"]["profile"] \
    == "http://iiif.io/api/image/2.1/level0.json"
print("OK v21")
EOF
```
Prints `OK v21`.
## Step 10: IIIF 3.0 builder

- **Files to touch:** `src/iiif_manifest_generator/builders/v30.py`
- **Action:** Create with exactly (complete file; `_image_service` branches on `config.image_api_version` — Image API 2 by default, Image API 3 with `--image-api-3`):
```python
"""IIIF Presentation API 3.0 document builders."""

from __future__ import annotations

from ..config import GenerationConfig
from ..models import DirectoryInfo, GeneratedDocument, ImageInfo
from .base import (
    COLLECTION_FILENAME,
    MANIFEST_FILENAME,
    child_document,
    collection_id,
    manifest_id,
)

CONTEXT = "https://iiif.io/api/presentation/3/context.json"
TYPE_NAMES = {"manifest": "Manifest", "collection": "Collection"}
IMAGE_PROTOCOL = "http://iiif.io/api/image/3/1/context.json"
IMAGE_API_2_PROFILE = "http://iiif.io/api/image/2/level0.json"


def _label(text: str) -> dict:
    return {"none": [text]}


def _metadata(doc_id: str) -> list[dict]:
    return [
        {
            "id": f"{doc_id}/metadata/generated-by",
            "label": {"none": ["Generated by"]},
            "value": {"none": ["iiif-manifest-generator"]},
        }
    ]


def _image_service(info: ImageInfo, image_api_version: str) -> dict:
    if image_api_version == "3":
        return {
            "id": info.iip.info_url,
            "type": "ImageService3",
            "format": info.mime,
            "width": info.width,
            "height": info.height,
            "protocol": IMAGE_PROTOCOL,
            "profile": "level2",
            "maxWidth": info.width,
            "maxHeight": info.height,
        }
    return {
        "id": info.iip.info_url,
        "type": "ImageService2",
        "profile": IMAGE_API_2_PROFILE,
    }


def _canvas(
    config: GenerationConfig, dir_info: DirectoryInfo, info: ImageInfo, index: int
) -> dict:
    canvas_id = f"{manifest_id(config, dir_info)}/canvas/{index}"
    return {
        "id": canvas_id,
        "type": "Canvas",
        "label": _label(info.rel_path.name),
        "width": info.width,
        "height": info.height,
        "items": [
            {
                "id": f"{canvas_id}/page/1",
                "type": "AnnotationPage",
                "items": [
                    {
                        "id": f"{canvas_id}/page/1/annotation/1",
                        "type": "Annotation",
                        "motivation": "painting",
                        "body": _image_service(info, config.image_api_version),
                        "target": canvas_id,
                    }
                ],
            }
        ],
    }


def build_manifest(config: GenerationConfig, dir_info: DirectoryInfo) -> GeneratedDocument:
    doc_id = manifest_id(config, dir_info)
    doc: dict = {
        "@context": CONTEXT,
        "id": doc_id,
        "type": "Manifest",
        "label": _label(dir_info.label),
        "metadata": _metadata(doc_id),
        "items": [
            _canvas(config, dir_info, info, i)
            for i, info in enumerate(dir_info.images, start=1)
        ],
    }
    # 3.0 removed license/attribution: use rights + requiredStatement instead.
    if config.attribution:
        doc["requiredStatement"] = {
            "label": _label("Attribution"),
            "value": _label(config.attribution),
        }
    if config.license:
        doc["rights"] = config.license
    # 3.0 thumbnails are an array.
    if config.thumbnails and dir_info.images and dir_info.images[0].iip.thumbnail_url:
        first = dir_info.images[0]
        doc["thumbnail"] = [
            {"id": first.iip.thumbnail_url, "type": "Image", "format": first.mime}
        ]
    return GeneratedDocument(
        dir_info=dir_info, kind="manifest", data=doc, filename=MANIFEST_FILENAME
    )


def build_collection(
    config: GenerationConfig, dir_info: DirectoryInfo
) -> GeneratedDocument:
    doc_id = collection_id(config, dir_info)
    items: list[dict] = []
    if dir_info.has_manifest:
        items.append(
            {
                "id": manifest_id(config, dir_info),
                "type": "Manifest",
                "label": _label(dir_info.label),
            }
        )
    for child in dir_info.documentable_children:
        child_id, kind = child_document(config, child)
        items.append(
            {"id": child_id, "type": TYPE_NAMES[kind], "label": _label(child.label)}
        )
    doc = {
        "@context": CONTEXT,
        "id": doc_id,
        "type": "Collection",
        "label": _label(dir_info.label),
        "metadata": _metadata(doc_id),
        "items": items,
    }
    return GeneratedDocument(
        dir_info=dir_info, kind="collection", data=doc, filename=COLLECTION_FILENAME
    )
```
- **Verification (Step 10):**
```bash
python - <<'EOF'
import tempfile
from pathlib import Path
from PIL import Image
from iiif_manifest_generator.config import GenerationConfig
from iiif_manifest_generator.tree import scan_tree
from iiif_manifest_generator.builders.v30 import build_manifest, build_collection
d = Path(tempfile.mkdtemp()) / "root"
(d / "sub").mkdir(parents=True)
Image.new("RGB", (10, 20), (0, 0, 0)).save(d / "a.jpg")
Image.new("RGB", (30, 40), (0, 0, 0)).save(d / "sub" / "b.png")
config = GenerationConfig(root=d, version="3.0", base_url="http://h")
root = scan_tree(config)
m = build_manifest(config, root).data
assert m["@context"] == "https://iiif.io/api/presentation/3/context.json"
assert m["type"] == "Manifest" and m["id"] == "http://h/manifest.json"
assert m["label"] == {"none": ["root"]}
assert len(m["items"]) == 1
canvas = m["items"][0]
assert canvas["type"] == "Canvas" and (canvas["width"], canvas["height"]) == (10, 20)
page = canvas["items"][0]
assert page["type"] == "AnnotationPage"
anno = page["items"][0]
assert anno["type"] == "Annotation" and anno["motivation"] == "painting"
assert anno["target"] == canvas["id"]
body = anno["body"]
assert body["type"] == "ImageService2"
assert body["profile"] == "http://iiif.io/api/image/2/level0.json"
assert body["id"] == "http://h/a/info.json"
assert "protocol" not in body
assert isinstance(m["thumbnail"], list) and m["thumbnail"][0]["type"] == "Image"
c = build_collection(config, root).data
assert c["type"] == "Collection" and len(c["items"]) == 2
print("OK v30")
EOF
```
Prints `OK v30`.
## Step 11: IIIF 4.0 builder + builder registry

- **Files to touch:** `src/iiif_manifest_generator/builders/v40.py`, `src/iiif_manifest_generator/builders/__init__.py`
- **Action (1 of 2):** Create `v40.py` with exactly (complete file; follows the official 4.0 example shape — plain-string labels, `motivation` as an array, body = `Image` + `service` array; `_body` branches on `config.image_api_version`, and the 2-style service entry uses `@id`/`@type`, which the official 4.0 schema's Service definition explicitly accepts):
```python
"""IIIF Presentation API 4.0 document builders."""

from __future__ import annotations

from ..config import GenerationConfig
from ..models import DirectoryInfo, GeneratedDocument, ImageInfo
from .base import (
    COLLECTION_FILENAME,
    MANIFEST_FILENAME,
    child_document,
    collection_id,
    manifest_id,
)

CONTEXT = "https://iiif.io/api/presentation/4/context.json"
TYPE_NAMES = {"manifest": "Manifest", "collection": "Collection"}
IMAGE_PROTOCOL = "http://iiif.io/api/image/3/1/context.json"
IMAGE_API_2_PROFILE = "http://iiif.io/api/image/2/level0.json"


def _metadata(doc_id: str) -> list[dict]:
    # 4.0 allows plain strings for label/value.
    return [
        {
            "id": f"{doc_id}/metadata/generated-by",
            "label": "Generated by",
            "value": "iiif-manifest-generator",
        }
    ]


def _body(info: ImageInfo, image_api_version: str) -> dict:
    if image_api_version == "3":
        service = {
            "id": info.iip.info_url,
            "type": "ImageService3",
            "profile": "level2",
            "protocol": IMAGE_PROTOCOL,
        }
    else:
        # 4.0 documents may reference Image API 2 services using the
        # 2-style '@id'/'@type' service entry (accepted by the official
        # 4.0 schema's Service definition).
        service = {
            "@id": info.iip.info_url,
            "@type": "ImageService2",
            "profile": IMAGE_API_2_PROFILE,
        }
    return {
        "id": info.iip.full_url,
        "type": "Image",
        "format": info.mime,
        "service": [service],
    }


def _canvas(
    config: GenerationConfig, dir_info: DirectoryInfo, info: ImageInfo, index: int
) -> dict:
    canvas_id = f"{manifest_id(config, dir_info)}/canvas/{index}"
    return {
        "id": canvas_id,
        "type": "Canvas",
        "label": info.rel_path.name,
        "width": info.width,
        "height": info.height,
        "items": [
            {
                "id": f"{canvas_id}/page/1",
                "type": "AnnotationPage",
                "items": [
                    {
                        "id": f"{canvas_id}/page/1/annotation/1",
                        "type": "Annotation",
                        "motivation": ["painting"],
                        "body": _body(info, config.image_api_version),
                        "target": canvas_id,
                    }
                ],
            }
        ],
    }


def build_manifest(config: GenerationConfig, dir_info: DirectoryInfo) -> GeneratedDocument:
    doc_id = manifest_id(config, dir_info)
    doc: dict = {
        "@context": CONTEXT,
        "id": doc_id,
        "type": "Manifest",
        "label": dir_info.label,  # plain string is valid in 4.0
        "metadata": _metadata(doc_id),
        "items": [
            _canvas(config, dir_info, info, i)
            for i, info in enumerate(dir_info.images, start=1)
        ],
    }
    if config.attribution:
        doc["requiredStatement"] = {
            "label": "Attribution",
            "value": config.attribution,
        }
    if config.license:
        doc["rights"] = config.license
    if config.thumbnails and dir_info.images and dir_info.images[0].iip.thumbnail_url:
        first = dir_info.images[0]
        doc["thumbnail"] = [
            {"id": first.iip.thumbnail_url, "type": "Image", "format": first.mime}
        ]
    return GeneratedDocument(
        dir_info=dir_info, kind="manifest", data=doc, filename=MANIFEST_FILENAME
    )


def build_collection(
    config: GenerationConfig, dir_info: DirectoryInfo
) -> GeneratedDocument:
    doc_id = collection_id(config, dir_info)
    items: list[dict] = []
    if dir_info.has_manifest:
        items.append(
            {
                "id": manifest_id(config, dir_info),
                "type": "Manifest",
                "label": dir_info.label,
            }
        )
    for child in dir_info.documentable_children:
        child_id, kind = child_document(config, child)
        items.append(
            {"id": child_id, "type": TYPE_NAMES[kind], "label": child.label}
        )
    doc = {
        "@context": CONTEXT,
        "id": doc_id,
        "type": "Collection",
        "label": dir_info.label,
        "metadata": _metadata(doc_id),
        "items": items,
    }
    return GeneratedDocument(
        dir_info=dir_info, kind="collection", data=doc, filename=COLLECTION_FILENAME
    )
```
- **Action (2 of 2, Step 11):** Create `src/iiif_manifest_generator/builders/__init__.py` with exactly:
```python
"""Version registry for the document builders."""

from __future__ import annotations

from ..config import GenerationConfig
from ..models import DirectoryInfo, GeneratedDocument
from . import v20, v21, v30, v40

BUILDERS: dict[str, object] = {
    "2.0": v20,
    "2.1": v21,
    "3.0": v30,
    "4.0": v40,
}


def build_documents(config: GenerationConfig, dir_info: DirectoryInfo) -> list[GeneratedDocument]:
    """Build the manifest and/or collection for one directory (if applicable)."""
    builder = BUILDERS[config.version]
    docs: list[GeneratedDocument] = []
    if dir_info.has_manifest:
        docs.append(builder.build_manifest(config, dir_info))
    if dir_info.has_collection:
        docs.append(builder.build_collection(config, dir_info))
    return docs
```
- **Verification (Step 11):**
```bash
python - <<'EOF'
import json, tempfile
from pathlib import Path
from PIL import Image
from iiif_manifest_generator.config import GenerationConfig
from iiif_manifest_generator.tree import scan_tree
from iiif_manifest_generator.builders import BUILDERS, build_documents
assert set(BUILDERS) == {"2.0", "2.1", "3.0", "4.0"}
d = Path(tempfile.mkdtemp()) / "root"; d.mkdir()
Image.new("RGB", (10, 20), (0, 0, 0)).save(d / "a.jpg")
expected_contexts = {
    "2.0": "http://iiif.io/api/presentation/2/context.json",
    "2.1": "http://iiif.io/api/presentation/2.1/context.json",
    "3.0": "https://iiif.io/api/presentation/3/context.json",
    "4.0": "https://iiif.io/api/presentation/4/context.json",
}
for version, expected in expected_contexts.items():
    config = GenerationConfig(root=d, version=version, base_url="http://h")
    docs = build_documents(config, scan_tree(config))
    manifest = next(doc for doc in docs if doc.kind == "manifest")
    assert manifest.data["@context"] == expected, version
    json.dumps(manifest.data)
    print(version, "OK ->", manifest.data["@context"])
print("OK builders registry")
EOF
```
Prints four `... OK -> ...` lines plus `OK builders registry`.

## Step 12: Writer + generation orchestration

- **Files to touch:** `src/iiif_manifest_generator/writer.py`, `src/iiif_manifest_generator/generate.py`
- **Action:**
  1. Create `writer.py` with exactly:
```python
"""Write generated documents to disk."""

from __future__ import annotations

import json
from pathlib import Path

from .config import GenerationConfig
from .models import GeneratedDocument


def write_documents(
    config: GenerationConfig, documents: list[GeneratedDocument]
) -> list[Path]:
    """Write each document to <dir>/<filename>.

    In dry-run mode the JSON is printed to stdout instead of being written.
    Re-running overwrites previously generated files (deterministic output).
    """
    written: list[Path] = []
    for doc in documents:
        target = doc.dir_info.path / doc.filename
        text = json.dumps(doc.data, indent=2, ensure_ascii=False) + "\n"
        if config.dry_run:
            print(f"# {target}")
            print(text, end="")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        written.append(target)
    return written
```
  2. Create `generate.py` with exactly:
```python
"""End-to-end generation orchestration."""

from __future__ import annotations

from .builders import build_documents
from .config import GenerationConfig
from .models import DirectoryInfo, GeneratedDocument
from .tree import scan_tree
from .writer import write_documents


def generate(config: GenerationConfig) -> list[GeneratedDocument]:
    """Scan config.root, build every document, and write them to disk."""
    root_info = scan_tree(config)
    docs = collect_documents(config, root_info)
    write_documents(config, docs)
    return docs


def collect_documents(
    config: GenerationConfig, root_info: DirectoryInfo
) -> list[GeneratedDocument]:
    """Recursively build all documents for the tree (pre-order traversal)."""
    docs: list[GeneratedDocument] = []
    _collect(config, root_info, docs)
    return docs


def _collect(
    config: GenerationConfig, info: DirectoryInfo, docs: list[GeneratedDocument]
) -> None:
    docs.extend(build_documents(config, info))
    for child in info.children:
        _collect(config, child, docs)
```
- **Verification (Step 12):**
```bash
python - <<'EOF'
import tempfile
from pathlib import Path
from PIL import Image
from iiif_manifest_generator.config import GenerationConfig
from iiif_manifest_generator.generate import generate
d = Path(tempfile.mkdtemp()) / "root"
(d / "sub").mkdir(parents=True)
Image.new("RGB", (10, 20), (0, 0, 0)).save(d / "a.jpg")
Image.new("RGB", (30, 40), (0, 0, 0)).save(d / "sub" / "b.png")
docs = generate(GenerationConfig(root=d, version="3.0", base_url="http://h"))
files = sorted(p.relative_to(d).as_posix() for p in d.rglob("*.json"))
assert files == ["collection.json", "manifest.json", "sub/manifest.json"], files
print("OK generate:", files)
EOF
```
Prints `OK generate: ['collection.json', 'manifest.json', 'sub/manifest.json']`.
## Step 13: CLI

- **Files to touch:** `src/iiif_manifest_generator/cli.py`
- **Action:** Create with exactly (complete file; `--base-url` is **required** — Q5; new `--image-api-3` switch — Q3):
```python
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
```
- **Verification:**
```bash
pip install -e .   # (re)register the console script
iiif-manifest-generator --help | head -8
tmp=$(mktemp -d)
python -c "from PIL import Image; Image.new('RGB',(10,10),(0,0,0)).save('$tmp/a.jpg')"
iiif-manifest-generator "$tmp" --version 3.0 --base-url http://localhost:8080; echo "exit=$?"
test -f "$tmp/manifest.json" && echo "manifest written"
iiif-manifest-generator "$tmp" --version 2.0 --base-url http://localhost:8080 --dry-run | head -4
iiif-manifest-generator /nonexistent --version 3.0 --base-url http://x; echo "exit=$?"
iiif-manifest-generator "$tmp" --version 9.9 --base-url http://x; echo "exit=$?"
iiif-manifest-generator "$tmp" --version 3.0; echo "exit=$?"
iiif-manifest-generator "$tmp" --version 3.0 --base-url http://localhost:8080 --image-api-3
python -c "import json; d=json.load(open('$tmp/manifest.json')); b=d['items'][0]['items'][0]['items'][0]['body']; assert b['type']=='ImageService3', b; print('OK api3')"
```
Expected: help text shows all options; first run `exit=0` + `manifest written`; dry-run prints JSON (file content stays the 3.0 default-API-2 version); the three error cases (`/nonexistent`, `--version 9.9`, missing `--base-url`) all exit 2; the `--image-api-3` run prints `OK api3`.
## Step 14: Install the official IIIF Presentation Validator

- **Files to touch:** `tools/presentation-validator/` (cloned, gitignored)
- **Action:** Run:
```bash
mkdir -p tools
git clone --depth 1 https://github.com/IIIF/presentation-validator.git tools/presentation-validator
pip install ./tools/presentation-validator
```
- **Verification:**
```bash
iiif-validator validate --help | grep -A2 "\-\-version"
python -c "import presentation_validator; print('OK validator import')"
```
Expected: the help shows `--version` with choices `1.0, 2.0, 2.1, 3.0, 4.0`, and the import prints `OK validator import`. (If the clone or install fails due to network restrictions, note it and continue — the e2e tests in Step 19 will skip, and the structural unit tests still guarantee correctness.)

## Step 15: Test fixtures

- **Files to touch:** `tests/conftest.py`
- **Action:** Create `tests/` and `conftest.py` with exactly:
```python
"""Shared fixtures: a small image tree with real raster files."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def image_tree(tmp_path: Path) -> Path:
    """Create:

    gallery/
    ├── a.jpg            (64x32)
    ├── b.png            (48x48)
    ├── empty/           (produces no documents)
    ├── alpha/
    │   ├── c.tif        (32x32)
    │   └── nested/
    │       ├── d.jpg    (100x50)
    │       └── deep/
    │           └── e.png (20x40)
    └── mixed/
        ├── f.png        (33x33)
        └── sub/
            └── g.jpg    (55x55)
    """
    root = tmp_path / "gallery"
    (root / "alpha" / "nested" / "deep").mkdir(parents=True)
    (root / "mixed" / "sub").mkdir(parents=True)
    (root / "empty").mkdir()

    def make(rel: str, size: tuple[int, int], color: tuple[int, int, int]) -> Path:
        path = root / rel
        Image.new("RGB", size, color).save(path)
        return path

    make("a.jpg", (64, 32), (200, 30, 30))
    make("b.png", (48, 48), (30, 200, 30))
    make("alpha/c.tif", (32, 32), (30, 30, 200))
    make("alpha/nested/d.jpg", (100, 50), (200, 200, 30))
    make("alpha/nested/deep/e.png", (20, 40), (128, 0, 128))
    make("mixed/f.png", (33, 33), (0, 128, 128))
    make("mixed/sub/g.jpg", (55, 55), (128, 128, 0))
    return root


@pytest.fixture()
def make_config(image_tree: Path):
    from iiif_manifest_generator.config import GenerationConfig

    def _make(**overrides) -> GenerationConfig:
        kwargs = dict(
            root=image_tree,
            version="3.0",
            base_url="http://localhost:8080",
        )
        kwargs.update(overrides)
        return GenerationConfig(**kwargs)

    return _make
```
- **Verification:** `python -m pytest --collect-only -q 2>&1 | tail -3` — no collection errors (0 tests collected is fine; no test files exist yet).
## Step 16: Unit tests — IIPImage URLs and tree scanning

- **Files to touch:** `tests/test_iip.py`, `tests/test_tree.py`
- **Action:**
  1. Create `tests/test_iip.py` with exactly (note: there is **no** test for a presentation→image API mapping — that logic lives in `GenerationConfig.image_api_version`):
```python
"""Unit tests for IIPImage identifier and URL construction."""

from __future__ import annotations

from pathlib import PurePath

from iiif_manifest_generator.iip import build_identifier, build_iip_urls


def test_identifier_strips_extension_by_default():
    assert build_identifier(PurePath("alpha/nested/d.jpg"), False) == "alpha/nested/d"


def test_identifier_keeps_extension_when_asked():
    assert build_identifier(PurePath("a.jpg"), True) == "a.jpg"


def test_identifier_quotes_special_characters():
    assert build_identifier(PurePath("my folder/img 1.jpg"), False) == "my%20folder/img%201"


def test_iip_urls_image_api_2():
    urls = build_iip_urls("http://images.example.org", "a/b/c", ".jpg", "2", True)
    assert urls.info_url == "http://images.example.org/a/b/c/info.json"
    assert urls.full_url == "http://images.example.org/a/b/c/full/full/0/default.jpg"
    assert urls.thumbnail_url == "http://images.example.org/a/b/c/full/square:256/0/default.jpg"


def test_iip_urls_image_api_3_and_no_thumbnails():
    urls = build_iip_urls("http://images.example.org", "a/b/c", ".png", "3", False)
    assert urls.info_url == "http://images.example.org/a/b/c/info.json"
    assert urls.full_url == "http://images.example.org/a/b/c/full/full/0/default.png"
    assert urls.thumbnail_url is None
    urls3 = build_iip_urls("http://images.example.org", "x", ".png", "3", True)
    assert urls3.thumbnail_url == "http://images.example.org/x/full/square/0/default.png"
```
  2. Create `tests/test_tree.py` with exactly:
```python
"""Unit tests for the recursive tree scanner."""

from __future__ import annotations

from PIL import Image

from iiif_manifest_generator.tree import scan_tree


def test_scan_classifies_directories(make_config):
    root = scan_tree(make_config())
    assert root.has_manifest
    assert root.has_collection
    assert [c.path.name for c in root.children] == ["alpha", "empty", "mixed"]
    assert {img.path.name for img in root.images} == {"a.jpg", "b.png"}


def test_scan_dimensions_and_identifier(make_config):
    root = scan_tree(make_config())
    a = next(img for img in root.images if img.path.name == "a.jpg")
    assert (a.width, a.height) == (64, 32)
    assert a.mime == "image/jpeg"
    assert a.identifier == "a"
    assert a.iip.info_url == "http://localhost:8080/a/info.json"


def test_nested_structure(make_config):
    root = scan_tree(make_config())
    alpha = next(c for c in root.children if c.path.name == "alpha")
    assert alpha.has_manifest          # contains c.tif
    assert alpha.has_collection        # contains nested/
    nested = alpha.children[0]
    assert nested.path.name == "nested"
    assert nested.has_manifest
    assert not nested.has_collection
    deep = nested.children[0]
    assert deep.path.name == "deep"
    assert deep.has_manifest
    assert not deep.has_collection


def test_empty_directory_produces_nothing(make_config):
    root = scan_tree(make_config())
    empty = next(c for c in root.children if c.path.name == "empty")
    assert not empty.has_manifest
    assert not empty.has_collection
    assert not empty.produces_documents


def test_mixed_folder_gets_both(make_config):
    root = scan_tree(make_config())
    mixed = next(c for c in root.children if c.path.name == "mixed")
    assert mixed.has_manifest
    assert mixed.has_collection


def test_unreadable_image_is_skipped(make_config, image_tree):
    (image_tree / "broken.jpg").write_bytes(b"not a real image")
    root = scan_tree(make_config())
    assert all(img.path.name != "broken.jpg" for img in root.images)


def test_hidden_entries_skipped_by_default(make_config, image_tree):
    hidden = image_tree / ".hidden"
    hidden.mkdir()
    Image.new("RGB", (10, 10), (0, 0, 0)).save(hidden / "h.jpg")
    root = scan_tree(make_config())
    assert ".hidden" not in [c.path.name for c in root.children]
    assert all(img.path.name != "h.jpg" for img in root.images)
```
- **Verification:** `python -m pytest tests/test_iip.py tests/test_tree.py -v` — all 12 tests pass, no errors.
## Step 17: Unit tests — all four builders

- **Files to touch:** `tests/test_builders.py`
- **Action (1 of 2):** Create `tests/test_builders.py`. The file is the concatenation of this part and the next; it starts with exactly:
```python
"""Structural tests for the four version builders."""

from __future__ import annotations

from iiif_manifest_generator.builders import BUILDERS, build_documents
from iiif_manifest_generator.tree import scan_tree


def _build(make_config, version, **overrides):
    config = make_config(version=version, **overrides)
    root = scan_tree(config)
    docs = build_documents(config, root)
    manifest = next(d for d in docs if d.kind == "manifest")
    collection = next(d for d in docs if d.kind == "collection")
    return config, root, manifest, collection


def _collect_ids(node, key, out):
    if isinstance(node, dict):
        if key in node:
            out.append(node[key])
        for value in node.values():
            _collect_ids(value, key, out)
    elif isinstance(node, list):
        for item in node:
            _collect_ids(item, key, out)


def test_registry_has_all_versions():
    assert set(BUILDERS) == {"2.0", "2.1", "3.0", "4.0"}


def test_root_document_ids_and_filenames(make_config):
    _, _, manifest, collection = _build(make_config, "3.0")
    assert manifest.data["id"] == "http://localhost:8080/manifest.json"
    assert collection.data["id"] == "http://localhost:8080/collection.json"
    assert manifest.filename == "manifest.json"
    assert collection.filename == "collection.json"


def test_v20_manifest_structure(make_config):
    _, _, manifest, _ = _build(make_config, "2.0")
    data = manifest.data
    assert data["@context"] == "http://iiif.io/api/presentation/2/context.json"
    assert data["@id"] == "http://localhost:8080/manifest.json"
    assert data["@type"] == "sc:Manifest"
    assert "id" not in data and "type" not in data
    assert data["label"] == "gallery"
    seq = data["sequences"][0]
    assert seq["@type"] == "sc:Sequence"
    assert seq["@id"] == "http://localhost:8080/manifest.json/sequence/normal"
    canvases = seq["canvases"]
    assert len(canvases) == 2
    first = canvases[0]
    assert first["@type"] == "sc:Canvas"
    assert (first["width"], first["height"]) in {(64, 32), (48, 48)}
    anno = first["images"][0]
    assert anno["@type"] == "oa:Annotation"
    assert anno["motivation"] == "sc:painting"
    resource = anno["resource"]
    assert resource["@type"] == "dctypes:Image"
    assert resource["service"]["@type"] == "ImageService2"
    assert resource["service"]["profile"] == "http://iiif.io/api/image/2/level0.json"
    assert resource["on"] == first["@id"]
    assert data["thumbnail"]["@id"].endswith("square:256/0/default.")


def test_v21_manifest_structure(make_config):
    _, _, manifest, _ = _build(make_config, "2.1")
    data = manifest.data
    assert data["@context"] == "http://iiif.io/api/presentation/2.1/context.json"
    assert data["id"] == "http://localhost:8080/manifest.json"
    assert data["type"] == "sc:Manifest"
    assert "@id" not in data and "@type" not in data
    seq = data["sequences"][0]
    assert seq["type"] == "sc:Sequence"
    resource = seq["canvases"][0]["images"][0]["resource"]
    assert resource["service"]["type"] == "ImageService2"
    assert resource["service"]["profile"] == "http://iiif.io/api/image/2.1/level0.json"
    assert data["thumbnail"]["id"].endswith("square:256/0/default.")


def test_v30_manifest_structure_defaults_to_image_api_2(make_config):
    _, _, manifest, _ = _build(make_config, "3.0")
    data = manifest.data
    assert data["@context"] == "https://iiif.io/api/presentation/3/context.json"
    assert data["type"] == "Manifest"
    assert data["label"] == {"none": ["gallery"]}
    assert "@id" not in data and "@type" not in data
    assert len(data["items"]) == 2
    canvas = data["items"][0]
    assert canvas["type"] == "Canvas"
    assert (canvas["width"], canvas["height"]) in {(64, 32), (48, 48)}
    page = canvas["items"][0]
    assert page["type"] == "AnnotationPage"
    anno = page["items"][0]
    assert anno["type"] == "Annotation"
    assert anno["motivation"] == "painting"
    assert anno["target"] == canvas["id"]
    body = anno["body"]
    assert body["type"] == "ImageService2"
    assert body["profile"] == "http://iiif.io/api/image/2/level0.json"
    assert body["id"].endswith("/info.json")
    assert "protocol" not in body
    assert isinstance(data["thumbnail"], list)
    assert data["thumbnail"][0]["type"] == "Image"
    assert data["thumbnail"][0]["id"].endswith("square:256/0/default.")


def test_v30_manifest_structure_image_api_3(make_config):
    _, _, manifest, _ = _build(make_config, "3.0", image_api3=True)
    data = manifest.data
    anno = data["items"][0]["items"][0]["items"][0]
    body = anno["body"]
    assert body["type"] == "ImageService3"
    assert body["profile"] == "level2"
    assert body["protocol"] == "http://iiif.io/api/image/3/1/context.json"
    assert body["maxWidth"] == body["width"]
    assert body["maxHeight"] == body["height"]
    assert data["thumbnail"][0]["id"].endswith("square/0/default.")


def test_v40_manifest_structure_defaults_to_image_api_2(make_config):
    _, _, manifest, _ = _build(make_config, "4.0")
    data = manifest.data
    assert data["@context"] == "https://iiif.io/api/presentation/4/context.json"
    assert data["type"] == "Manifest"
    assert data["label"] == "gallery"  # plain string in 4.0
    assert len(data["items"]) == 2
    canvas = data["items"][0]
    assert canvas["type"] == "Canvas"
    page = canvas["items"][0]
    assert page["type"] == "AnnotationPage"
    anno = page["items"][0]
    assert anno["type"] == "Annotation"
    assert anno["motivation"] == ["painting"]
    body = anno["body"]
    assert body["type"] == "Image"
    service = body["service"][0]
    assert service["@type"] == "ImageService2"
    assert service["@id"].endswith("/info.json")
    assert service["profile"] == "http://iiif.io/api/image/2/level0.json"
    assert "id" not in service and "type" not in service
    assert isinstance(data["thumbnail"], list)
    assert data["thumbnail"][0]["id"].endswith("square:256/0/default.")


def test_v40_manifest_structure_image_api_3(make_config):
    _, _, manifest, _ = _build(make_config, "4.0", image_api3=True)
    data = manifest.data
    body = data["items"][0]["items"][0]["items"][0]["body"]
    service = body["service"][0]
    assert service["type"] == "ImageService3"
    assert service["profile"] == "level2"
    assert service["protocol"] == "http://iiif.io/api/image/3/1/context.json"
    assert data["thumbnail"][0]["id"].endswith("square/0/default.")


def test_v30_collection_items(make_config):
    _, _, _, collection = _build(make_config, "3.0")
    data = collection.data
    assert data["type"] == "Collection"
    items = data["items"]
    ids = {item["id"] for item in items}
    assert "http://localhost:8080/manifest.json" in ids
    assert "http://localhost:8080/alpha/collection.json" in ids
    assert "http://localhost:8080/mixed/collection.json" in ids
    assert not any("empty" in i for i in ids)
    assert {item["type"] for item in items} == {"Manifest", "Collection"}


def test_v20_collection_members(make_config):
    _, _, _, collection = _build(make_config, "2.0")
    data = collection.data
    assert data["@type"] == "sc:Collection"
    members = data["members"]
    pairs = {(m["@id"], m["@type"]) for m in members}
    assert ("http://localhost:8080/manifest.json", "sc:Manifest") in pairs
    assert ("http://localhost:8080/alpha/collection.json", "sc:Collection") in pairs
    assert ("http://localhost:8080/mixed/collection.json", "sc:Collection") in pairs
    assert len(members) == 3  # empty/ is not referenced


def test_ids_unique_within_every_document(make_config):
    for version in ("2.0", "2.1", "3.0", "4.0"):
        for overrides in ({}, {"image_api3": True}):
            _, _, manifest, collection = _build(make_config, version, **overrides)
            id_key = "@id" if version == "2.0" else "id"
            for doc in (manifest, collection):
                ids = []
                _collect_ids(doc.data, id_key, ids)
                assert len(ids) == len(set(ids)), (
                    f"duplicate ids in {version} {doc.kind} {overrides}"
                )
```
- **Verification (Step 17):** `python -m pytest tests/test_builders.py -v` — **11 passed**.
## Step 18: Unit tests — full generate/write pipeline

- **Files to touch:** `tests/test_generate.py`
- **Action:** Create with exactly:
```python
"""End-to-end tests of the generate/write pipeline (no external validator)."""

from __future__ import annotations

import json

from iiif_manifest_generator.generate import generate


def test_generate_writes_expected_files(make_config, image_tree):
    docs = generate(make_config())
    expected = {
        image_tree / "manifest.json",
        image_tree / "collection.json",
        image_tree / "alpha" / "manifest.json",
        image_tree / "alpha" / "collection.json",
        image_tree / "alpha" / "nested" / "manifest.json",
        image_tree / "alpha" / "nested" / "collection.json",
        image_tree / "alpha" / "nested" / "deep" / "manifest.json",
        image_tree / "mixed" / "manifest.json",
        image_tree / "mixed" / "collection.json",
        image_tree / "mixed" / "sub" / "manifest.json",
    }
    actual = {d.dir_info.path / d.filename for d in docs}
    assert actual == expected
    for path in expected:
        assert path.is_file()
        json.loads(path.read_text(encoding="utf-8"))


def test_generate_skips_empty_dirs(make_config, image_tree):
    generate(make_config())
    assert not (image_tree / "empty" / "manifest.json").exists()
    assert not (image_tree / "empty" / "collection.json").exists()


def test_generate_is_idempotent(make_config, image_tree):
    generate(make_config())
    first = {p: p.read_bytes() for p in image_tree.rglob("*.json")}
    generate(make_config())
    second = {p: p.read_bytes() for p in image_tree.rglob("*.json")}
    assert first == second


def test_dry_run_writes_nothing(make_config, image_tree, capsys):
    generate(make_config(dry_run=True))
    assert not list(image_tree.rglob("*.json"))
    out = capsys.readouterr().out
    assert "manifest.json" in out
```
- **Verification:** `python -m pytest tests/test_generate.py -v` — all 4 tests pass.

## Step 19: End-to-end tests with the official validator

- **Files to touch:** `tests/test_e2e_validator.py`
- **Action:** Create with exactly (six cases: both Image API modes for 3.0/4.0):
```python
"""End-to-end validation with the official IIIF Presentation Validator.

Skipped when the `iiif-validator` command is not installed. Install with:

    pip install git+https://github.com/IIIF/presentation-validator.git

Note: validating 2.0/2.1 may require network access (JSON-LD context
retrieval); 3.0/4.0 validate fully offline against bundled schemas.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from iiif_manifest_generator.config import GenerationConfig
from iiif_manifest_generator.generate import generate

VALIDATOR = shutil.which("iiif-validator")

CASES = [
    ("2.0", False),
    ("2.1", False),
    ("3.0", False),
    ("3.0", True),
    ("4.0", False),
    ("4.0", True),
]

pytestmark = pytest.mark.skipif(
    VALIDATOR is None, reason="iiif-validator not installed"
)


@pytest.mark.parametrize("version,image_api3", CASES)
def test_generated_tree_passes_official_validator(version, image_api3, image_tree):
    config = GenerationConfig(
        root=image_tree,
        version=version,
        base_url="http://localhost:8080",
        image_api3=image_api3,
    )
    generate(config)
    proc = subprocess.run(
        [VALIDATOR, "validate-dir", "--version", version, str(image_tree)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, (
        f"validator failed for {version} (image_api3={image_api3})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
```
- **Verification:** `python -m pytest tests/test_e2e_validator.py -v` — 6 passed (or 6 skipped if the validator was not installed in Step 14). **This is the key validity gate: the official validator must accept every generated document in all four versions (and both Image API modes for 3.0/4.0).** If a case fails, read the printed validator output, fix the corresponding builder, and re-run until green.
## Step 20: README

- **Files to touch:** `README.md`
- **Action:** Create `README.md` with exactly the content between the four-backtick fence below:
````markdown
# iiif-manifest-generator

Generate valid [IIIF Presentation](https://iiif.io/api/presentation/) manifests
(2.0, 2.1, 3.0, 4.0) for a tree of folders of images that is served through
[IIPImage](https://github.com/samvera/image).

## How it works

- Every folder containing images gets its own `manifest.json`
  (IIIF Presentation Manifest with one canvas per image).
- Every folder containing subfolders gets a `collection.json`
  (IIIF Collection) that references the documents of its subfolders — and its
  own manifest when the folder also contains images.
- Folders with neither images nor document-producing subfolders produce nothing
  (and are not referenced by their parent collection).
- Documents are written next to the folder they describe:
  `<dir>/manifest.json` and `<dir>/collection.json`. Re-running is
  idempotent (files are deterministically overwritten).

Document identifiers are built from `--base-url`:
`{base_url}/{path/below/root}/manifest.json`. The same base URL (or
`--image-base-url`) is used for the IIPImage image-service URLs.

## Install

```bash
pip install -e .
# with test dependencies:
pip install -e ".[dev]"
```

## Usage

```bash
# Generate IIIF Presentation 3.0 manifests/collections:
iiif-manifest-generator /path/to/images --version 3.0 \
    --base-url https://example.org/images

# The image server (IIPImage) lives somewhere else:
iiif-manifest-generator /path/to/images --version 2.1 \
    --base-url https://example.org/manifests \
    --image-base-url https://images.example.org

# 3.0 manifests referencing IIIF Image API 3 services:
iiif-manifest-generator /path/to/images --version 3.0 \
    --base-url https://example.org/images --image-api-3

# Preview without writing files:
iiif-manifest-generator /path/to/images --version 4.0 \
    --base-url http://localhost:8080 --dry-run
```

| Option | Default | Description |
| --- | --- | --- |
| `root` | (required) | Root directory to scan recursively. |
| `--version` | (required) | One of `2.0`, `2.1`, `3.0`, `4.0`. |
| `--base-url` | (required) | Base URL for document identifiers and (by default) images. |
| `--image-base-url` | value of `--base-url` | Base URL of the IIPImage server. |
| `--attribution` | none | Attribution statement (2.0/2.1: `attribution`; 3.0/4.0: `requiredStatement`). |
| `--license` | none | License URL (2.0/2.1: `license`; 3.0/4.0: `rights`). |
| `--include-hidden` | off | Include hidden files/directories (leading `.`). |
| `--keep-extension` | off | Keep the file extension in IIPImage identifiers. |
| `--no-thumbnails` | off | Do not emit `thumbnail` properties. |
| `--image-api-3` | off | Reference IIIF Image API 3 services (ImageService3) in 3.0/4.0 manifests instead of Image API 2. Requires IIPImage with `iiif3 = true`. No effect for 2.0/2.1. |
| `--dry-run` | off | Print documents to stdout instead of writing files. |
| `-v/--verbose` | off | Debug logging. |

## IIPImage requirements

- The IIPImage IIIF module must be enabled.
- Identifier mapping: by default the IIPImage identifier of an image is its
  path relative to the scan root, with the extension removed and URL-encoded:
  `alpha/nested/d.jpg` → `{image-base-url}/alpha/nested/d/info.json`.
  Use `--keep-extension` to keep the extension. Adjust to match your IIPImage
  identifier configuration.
- By default, **all** manifests reference an IIIF Image API 2 service
  (`ImageService2`, level0), which works with a standard IIPImage IIIF
  configuration. For 3.0/4.0 manifests you can pass `--image-api-3` to
  reference an IIIF Image API 3 service (`ImageService3`, level2) instead;
  that requires IIPImage to be configured with `iiif3 = true`.

## Validating your output

The official [IIIF Presentation
Validator](https://github.com/IIIF/presentation-validator):

```bash
pip install git+https://github.com/IIIF/presentation-validator.git
iiif-validator validate-dir --version 3.0 /path/to/images
```

`validate-dir` recursively validates every `.json` file in the directory and
exits non-zero when any document fails. Note: validating 2.0/2.1 may require
network access (JSON-LD context retrieval); 3.0/4.0 validate fully offline.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

End-to-end tests run the official validator on the generated output for all
four versions (both Image API modes for 3.0/4.0) and are skipped when
`iiif-validator` is not installed.
````
- **Verification:** `test -f README.md && grep -c "iiif-manifest-generator" README.md` prints a count ≥ 5.
## Step 21: Final end-to-end verification (all versions)

- **Files to touch:** none (verification only)
- **Action:** Run the complete check:
```bash
cd /home/rutger/src/iiif-manifest-generator
python -m pytest -q

# Demo tree:
rm -rf /tmp/demo-images
mkdir -p /tmp/demo-images/books/vol1
python - <<'EOF'
from PIL import Image
Image.new("RGB", (800, 600), (120, 20, 20)).save("/tmp/demo-images/cover.jpg")
for i in range(1, 4):
    Image.new("RGB", (700, 1000), (20, 120, 20)).save(
        f"/tmp/demo-images/books/vol1/page{i}.png")
EOF

for v in 2.0 2.1 3.0 4.0; do
    iiif-manifest-generator /tmp/demo-images --version "$v" \
        --base-url http://localhost:8080
    iiif-validator validate-dir --version "$v" /tmp/demo-images || break
done
echo "--- generated files ---"
find /tmp/demo-images -name '*.json' | sort
```
- **Verification:**
  - `pytest -q` reports **33 passed** (or 27 passed + 6 skipped if the validator was not installed in Step 14).
  - For each version: generation logs `Generated N IIIF document(s)` and `iiif-validator validate-dir` prints `Failed: 0` (exit code 0).
  - `find` shows exactly: `/tmp/demo-images/collection.json`, `/tmp/demo-images/manifest.json`, `/tmp/demo-images/books/collection.json`, `/tmp/demo-images/books/vol1/manifest.json`.
  - Spot-check one document, e.g. `python -m json.tool /tmp/demo-images/manifest.json | head -30` — structure matches the version's spec.
# 4. Edge Cases & Error Handling

The executor must implement/verify each of these (most are already encoded in the code above — the tests in Steps 16–18 prove them):

1. **Root with no images anywhere** → zero documents; log warning `No images found under ...`; CLI still exits 0 (not an error state).
2. **Directory whose subfolders contain no images anywhere** → nothing is generated for it, and its parent collection must **not** reference it (the `documentable_children` filter in `models.py`/`tree.py`). This prevents an empty `items` array, which would be invalid in IIIF 3.0/4.0 (required property). Proven by `test_empty_directory_produces_nothing` and `test_v30_collection_items`.
3. **Folder with images but no subfolders** → manifest only, **no** collection (matches the requirement "each folder containing *another folder* must get a collection"). Proven by `test_nested_structure` (`deep`/`sub` get no `collection.json`).
4. **Folder with both images and subfolders** → gets **both** documents; its collection lists its own manifest first, then documentable children in case-insensitive name order. Proven by `test_mixed_folder_gets_both` and `test_generate_writes_expected_files`.
5. **Corrupt/undecodable file with an image extension** (e.g. `broken.jpg` containing text) → `get_image_size` raises `ValueError`; the scanner logs a warning (`skipping <path>: ...`) and continues — the file produces no canvas and the run does not crash. Proven by `test_unreadable_image_is_skipped`.
6. **Non-image files** (`.pdf`, `.txt`, `.xml`, even pre-existing `.json`) → silently ignored by `is_image_file`.
7. **Hidden files/directories** (leading `.`) → skipped by default; included with `--include-hidden`. Proven by `test_hidden_entries_skipped_by_default`.
8. **Symlinks** (files and directories, including cycles pointing back up the tree) → skipped entirely in `_populate` (`entry.is_symlink()` check), so the walk cannot loop.
9. **Unreadable directory (PermissionError)** → `log.warning("cannot read directory ...")` and the subtree is skipped; the run continues.
10. **Names with spaces / unicode / URL-special characters** → every path segment is quoted with `quote(part, safe="")` in IIPImage identifiers and in document IDs; JSON is written UTF-8 with `ensure_ascii=False`. Proven by `test_identifier_quotes_special_characters`.
11. **`--base-url`/`--image-base-url` with a trailing slash** → normalized with `rstrip("/")`; **empty or non-`http(s)://` value** → `ValueError` at config time → CLI prints `error: ...` to stderr and exits **2**.
12. **Missing or invalid `--version`**, or missing required `--base-url` → argparse rejects it, exit code 2.
13. **`root` does not exist or is not a directory** → `NotADirectoryError` → CLI prints `error: ...`, exit code 2.
14. **Pre-existing `manifest.json`/`collection.json` in a folder** → overwritten on every run. Output is deterministic, so re-running is idempotent (byte-identical). Proven by `test_generate_is_idempotent`. Documented in the README.
15. **Multi-dot filenames** (`archive.tar.jpg`) → extension is split at the **last** dot (`rsplit(".", 1)`), so the identifier is `archive.tar` and the format extension is `.jpg`.
16. **Uppercase extensions** (`.JPG`, `.PNG`) → recognized via case-insensitive suffix comparison; the URL format token is lowercased.
17. **Duplicate-ID risk** — the official 4.0 validator fails a document containing duplicate `id` values → all IDs are derived from globally-unique document-ID paths (`…/canvas/N`, `…/page/1`, `…/page/1/annotation/1`), so they are unique within each document. Proven by `test_ids_unique_within_every_document`.
18. **2.x-only properties leaking into 3.0/4.0** (`license`, `attribution`, `@id`, `@type`, `sequences`, `members`) → the v30/v40 builders deliberately emit `rights`/`requiredStatement` and `id`/`type` only; the builder unit tests assert the forbidden keys are **absent** (e.g. `assert "@id" not in data`).
19. **`--image-api-3` used while IIPImage runs without Image API 3** (`iiif3` disabled) → the referenced `info.json` URLs would 404. The default (Image API 2) has no such requirement, so it works with any standard IIPImage configuration; the README documents the `iiif3 = true` requirement for `--image-api-3`. The generator does not call the image server, so this cannot be detected at runtime.
20. **Very deep nesting** → the scanner is recursive; fine for realistic depths (Python default recursion limit ≈ 1000 directory levels). No action needed beyond this note.
# 5. Testing & Validation

**Automated (run in this order):**
1. `pip install -e ".[dev]"` — install the package with test extras.
2. `python -m pytest -q` — full suite: 5 (`test_iip`) + 7 (`test_tree`) + 11 (`test_builders`) + 4 (`test_generate`) = **27 unit tests**, all green; plus **6 e2e tests** (Step 19) that run the **official** `iiif-validator validate-dir` against the generated tree and assert exit code 0. **Total: 33 tests** (or 27 passed + 6 skipped if the validator was not installed in Step 14).
3. The e2e test is the authoritative validity gate: the user-specified validator (https://github.com/IIIF/presentation-validator) must accept **every** generated `manifest.json` and `collection.json` in **all four** versions, and both Image API modes for 3.0/4.0. 3.0 is checked against the bundled official Draft-7 JSON schema and 4.0 against the bundled Draft-2020-12 schemas plus the unique-ID check (both fully offline); 2.0/2.1 are checked by `iiif_prezi`'s `ManifestReader` (may fetch the JSON-LD context from iiif.io — if the sandbox is offline and only the 2.x e2e cases fail for connectivity reasons, record that and rely on the structural unit tests for 2.x).

**Manual verification (perform at least the first two):**
1. **URL-mode validation** (also checks that each document's `id` matches its served URL — the validator only enforces this for URLs):
   ```bash
   cd /tmp/demo-images && python -m http.server 8080 &
   iiif-validator validate --version 3.0 http://localhost:8080/manifest.json
   iiif-validator validate --version 4.0 http://localhost:8080/collection.json
   # kill %1 when done
   ```
2. **Viewer smoke test** — open https://iiif.io/viewer (Mirador) and load `http://localhost:8080/manifest.json`; the canvas should appear (the image itself will 404 unless IIPImage is running, which is expected in the sandbox).
3. **Against a real IIPImage** (user's environment, optional): `curl -s <image-base>/alpha/nested/d/info.json | python -m json.tool` and open `<image-base>/alpha/nested/d/full/full/0/default.jpg` in a browser to confirm the identifier mapping matches the IIPImage configuration (this is exactly what Q2 is about).
4. **Cross-version spot check** — after regenerating the demo tree for 2.1 vs 2.0, the only differences should be `id` vs `@id` naming, the context URL, and the image profile URL.
5. **Dry-run check** — `--dry-run` must print documents and create no files (`find <root> -name '*.json'` stays empty).

---

# Questions and Ambiguities — RESOLVED

All questions were asked to the user on 2026-07-11 and resolved. The plan (Steps 0–21) already reflects these decisions.

| # | Question | **Decision** | Alternatives considered |
| --- | --- | --- | --- |
| Q1 | Where should the generated files be written? | **In-place** — `manifest.json` / `collection.json` written directly inside each folder; documents are served from the same web root as the images, so document IDs `{base_url}/…/manifest.json` match file locations exactly. | B: mirrored `--output-dir`; C: flat output dir with prefixed names. |
| Q2 | How are images mapped to IIPImage identifiers? | **Path-derived** — identifier = path relative to scan root, extension stripped, URL-quoted (`alpha/nested/d.jpg` → `alpha/nested/d`). `--keep-extension` remains available. | B: keep extension; C: explicit `--identifier-map` JSON file for custom identifier schemes. |
| Q3 | Which IIIF Image API should 3.0/4.0 manifests reference? | **Image API 2 by default** (`ImageService2`, level0) for *all* versions; **`--image-api-3` CLI switch** opts 3.0/4.0 manifests into `ImageService3` (level2; requires IIPImage `iiif3 = true`). No effect for 2.0/2.1. Both forms verified acceptable by the official validator schemas. | Alternative: Image API 3 by default for 3.0/4.0. |
| Q4 | Labels and metadata content? | **Minimal** — `label` = folder name verbatim (root: its directory name), plus a single "Generated by" metadata entry (and "Description" in 2.x). | B: humanized title-case labels + per-folder `METADATA.json`. |
| Q5 | Should `--base-url` have a default? | **Required flag, no default** — forces an explicit base URL on every run (avoids silently-generated localhost IDs in production output). | A: default `http://localhost:8080`. |
| Q6 | Thumbnails by default? | **On** — manifest-level `thumbnail` from the first image (`full/square:256/0/default.{ext}` for Image API 2; `full/square/0/default.{ext}` for Image API 3); disable with `--no-thumbnails`. | B: off by default with a `--thumbnails` opt-in flag. |

---

## Execution note

This plan is self-contained: Steps 0–21 each state the files to touch, the exact file contents, and a verification command. Steps 1–13 build and smoke-test the code incrementally; Steps 14–19 add the test suite and the official-validator e2e gate; Step 20 documents the tool; Step 21 runs the full validation matrix. If any e2e case fails, the validator output names the exact document and property — fix the corresponding builder module (Step 8–11) and re-run.
