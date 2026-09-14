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
    # NOTE (deviation from plan, line 1774): the plan's test asserted
    # `not nested.has_collection`, but that contradicts the plan's own
    # `DirectoryInfo.has_collection` model (produces_documents AND has
    # children) and Step 18's expected file set, which includes
    # alpha/nested/collection.json. `nested` contains deep/, so it gets a
    # collection (its own manifest + deep's manifest). The corrected
    # assertion is consistent with every other step in the plan.
    assert nested.has_collection
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
