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
