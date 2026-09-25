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
def image_tree_spaces(tmp_path: Path) -> Path:
    """Create:

    gallery/
    └── my scan/
        ├── img 1.jpg    (64x32)
        └── sub dir/
            └── page 2.jpg (48x48)
    """
    root = tmp_path / "gallery"
    nested = root / "my scan" / "sub dir"
    nested.mkdir(parents=True)

    def make(rel: str, size: tuple[int, int], color: tuple[int, int, int]) -> None:
        Image.new("RGB", size, color).save(root / rel)

    make("my scan/img 1.jpg", (64, 32), (200, 30, 30))
    make("my scan/sub dir/page 2.jpg", (48, 48), (30, 200, 30))
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
