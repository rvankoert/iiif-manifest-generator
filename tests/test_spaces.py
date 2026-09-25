"""Regression tests for scans with spaces in directory/file names.

Generic IIIF viewers require every document identifier to be a valid IRI.
Two things must hold:

* IIPImage identifiers are percent-encoded per path segment
  (``my scan/img 1.jpg`` -> ``my%20scan/img%201``);
* a ``--base-url`` containing raw spaces is percent-encoded by the
  configuration so no generated id contains an unencoded space.
"""

from __future__ import annotations

from urllib.parse import urlsplit

import pytest

from iiif_manifest_generator.config import GenerationConfig
from iiif_manifest_generator.generate import collect_documents
from iiif_manifest_generator.tree import scan_tree


def _all_images(node):
    yield from node.images
    for child in node.children:
        yield from _all_images(child)


def _all_ids(node, key, out):
    if isinstance(node, dict):
        if key in node:
            out.append(node[key])
        for value in node.values():
            _all_ids(value, key, out)
    elif isinstance(node, list):
        for item in node:
            _all_ids(item, key, out)


def test_spaced_tree_identifiers_are_encoded(image_tree_spaces):
    config = GenerationConfig(
        root=image_tree_spaces,
        version="3.0",
        base_url="http://localhost:8080",
    )
    root = scan_tree(config)
    images = list(_all_images(root))
    # identifiers are relative to the scan root, quoted per path segment
    assert {img.identifier for img in images} == {
        "my%20scan/img%201",
        "my%20scan/sub%20dir/page%202",
    }
    a = next(img for img in images if img.path.name == "img 1.jpg")
    assert a.iip.info_url == "http://localhost:8080/my%20scan/img%201"
    assert a.iip.full_url == (
        "http://localhost:8080/my%20scan/img%201/full/full/0/default.jpg"
    )
    assert a.iip.thumbnail_url == (
        "http://localhost:8080/my%20scan/img%201/full/!256,256/0/default.jpg"
    )


@pytest.mark.parametrize("version", ["2.0", "2.1", "3.0", "4.0"])
def test_all_document_ids_are_valid_iris(image_tree_spaces, version):
    config = GenerationConfig(
        root=image_tree_spaces,
        version=version,
        # a raw-space base URL (the scan root is served from a path that
        # contains spaces) must be normalized to a valid IRI
        base_url="http://localhost:8080/my scan",
    )
    assert config.base_url == "http://localhost:8080/my%20scan"
    assert config.image_base_url == "http://localhost:8080/my%20scan"
    root = scan_tree(config)
    docs = collect_documents(config, root)
    # gallery/collection.json + my scan/{manifest,collection}.json
    # + my scan/sub dir/manifest.json
    assert len(docs) == 4
    id_key = "@id" if version in ("2.0", "2.1") else "id"
    for doc in docs:
        ids = []
        _all_ids(doc.data, id_key, ids)
        assert ids, f"no ids found in {doc.kind}"
        for url in ids:
            assert isinstance(url, str)
            assert " " not in url, f"raw space in id: {url!r}"
            assert urlsplit(url).scheme in ("http", "https"), url
    manifest = next(
        d for d in docs if d.kind == "manifest" and d.dir_info.path.name == "my scan"
    )
    # first my%20scan = normalized base URL, second = the directory name
    assert manifest.data[id_key] == (
        "http://localhost:8080/my%20scan/my%20scan/manifest.json"
    )