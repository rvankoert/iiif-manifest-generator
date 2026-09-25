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
    # NOTE (deviation from plan): the official 4.0 validator's unique-id check
    # (presentation_validator/v4/unique_ids.py) skips reference fields
    # (['target', 'lookAt', 'range', 'structures', 'first', 'last', 'start',
    #  'source', 'body', 'scope']) because 4.0 annotation targets are typed
    # objects that legitimately reuse the referenced resource's id. We mirror
    # 'target' and 'body' here so this test matches official validator semantics.
    if isinstance(node, dict):
        if key in node:
            out.append(node[key])
        for k, value in node.items():
            if k in ("target", "body"):
                continue
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
    # NOTE (deviation from plan line 1880): the plan asserted
    # endswith("square:256/0/default."), which is impossible because the
    # thumbnail URL includes the file extension. Using `in` keeps the intent:
    # verify the forced-size (!256,256) token in the thumbnail URL.
    assert "!256,256/0/default." in data["thumbnail"]["@id"]


def test_v21_manifest_structure(make_config):
    _, _, manifest, _ = _build(make_config, "2.1")
    data = manifest.data
    # NOTE (deviation from plan): the official validator (iiif_prezi) rejects
    # the 2.1 context string ("Top level @context is not known") and requires
    # @id/@type key style ("Every resource must have @type"); see the NOTE in
    # builders/v21.py. Assertions below use the 2.0-style keys accordingly.
    assert data["@context"] == "http://iiif.io/api/presentation/2/context.json"
    assert data["@id"] == "http://localhost:8080/manifest.json"
    assert data["@type"] == "sc:Manifest"
    assert "id" not in data and "type" not in data
    seq = data["sequences"][0]
    assert seq["@type"] == "sc:Sequence"
    resource = seq["canvases"][0]["images"][0]["resource"]
    assert resource["service"]["@type"] == "ImageService2"
    assert resource["service"]["profile"] == "http://iiif.io/api/image/2.1/level0.json"
    # NOTE (deviation from plan line 1895): see test_v20_manifest_structure —
    # `in` instead of endswith (URL includes the file extension).
    assert "!256,256/0/default." in data["thumbnail"]["@id"]


def test_v30_manifest_structure_defaults_to_image_api_2(make_config):
    _, _, manifest, _ = _build(make_config, "3.0")
    data = manifest.data
    # NOTE (deviation from plan): the official validator's 3.0 schema requires
    # the http (not https) context; see the NOTE in builders/v30.py.
    assert data["@context"] == "http://iiif.io/api/presentation/3/context.json"
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
    # NOTE (deviation from plan): the body is the full-size render (Image)
    # carrying the image service (mirrors builders/v40.py); see v30.py.
    assert body["type"] == "Image"
    assert body["id"].endswith(
        "/full/full/0/default.jpg"
    ) or body["id"].endswith("/full/full/0/default.png")
    service = body["service"][0]
    assert service["type"] == "ImageService2"
    assert service["profile"] == "http://iiif.io/api/image/2/level0.json"
    # NOTE (deviation from plan): the service id is the Image API base URL
    # (viewers fetch {id}/info.json), so there is no /info.json suffix.
    assert service["id"] == "http://localhost:8080/a"
    assert "protocol" not in service
    assert isinstance(data["thumbnail"], list)
    assert data["thumbnail"][0]["type"] == "Image"
    # NOTE (deviation from plan line 1922): see test_v20_manifest_structure —
    # `in` instead of endswith (URL includes the file extension).
    assert "!256,256/0/default." in data["thumbnail"][0]["id"]


def test_v30_manifest_structure_image_api_3(make_config):
    _, _, manifest, _ = _build(make_config, "3.0", image_api3=True)
    data = manifest.data
    anno = data["items"][0]["items"][0]["items"][0]
    body = anno["body"]
    # NOTE (deviation from plan): the body is the full-size render (Image)
    # carrying the image service; see test_v30_manifest_structure_defaults_to_image_api_2.
    assert body["type"] == "Image"
    service = body["service"][0]
    assert service["type"] == "ImageService3"
    assert service["profile"] == "level2"
    assert service["protocol"] == "http://iiif.io/api/image/3/1/context.json"
    assert service["maxWidth"] == service["width"]
    assert service["maxHeight"] == service["height"]
    # NOTE (deviation from plan line 1935): see test_v20_manifest_structure —
    # `in` instead of endswith (URL includes the file extension).
    assert "!256,256/0/default." in data["thumbnail"][0]["id"]


def test_v40_manifest_structure_defaults_to_image_api_2(make_config):
    _, _, manifest, _ = _build(make_config, "4.0")
    data = manifest.data
    # NOTE (deviation from plan): the official validator's 4.0 schema requires
    # the http (not https) context and lngString labels ({"none": [...]}), not
    # plain strings; see the NOTEs in builders/v40.py.
    assert data["@context"] == "http://iiif.io/api/presentation/4/context.json"
    assert data["type"] == "Manifest"
    assert data["label"] == {"none": ["gallery"]}  # lngString in 4.0
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
    # NOTE (deviation from plan): the service id is the Image API base URL
    # (viewers fetch {id}/info.json), so there is no /info.json suffix.
    assert service["@id"] == "http://localhost:8080/a"
    assert service["profile"] == "http://iiif.io/api/image/2/level0.json"
    assert "id" not in service and "type" not in service
    assert isinstance(data["thumbnail"], list)
    # NOTE (deviation from plan line 1960): see test_v20_manifest_structure —
    # `in` instead of endswith (URL includes the file extension).
    assert "!256,256/0/default." in data["thumbnail"][0]["id"]


def test_v40_manifest_structure_image_api_3(make_config):
    _, _, manifest, _ = _build(make_config, "4.0", image_api3=True)
    data = manifest.data
    body = data["items"][0]["items"][0]["items"][0]["body"]
    service = body["service"][0]
    assert service["type"] == "ImageService3"
    assert service["profile"] == "level2"
    assert service["protocol"] == "http://iiif.io/api/image/3/1/context.json"
    # NOTE (deviation from plan line 1971): see test_v20_manifest_structure —
    # `in` instead of endswith (URL includes the file extension).
    assert "!256,256/0/default." in data["thumbnail"][0]["id"]


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
            # NOTE (deviation from plan): 2.1 documents use the @id/@type key
            # style (see test_v21_manifest_structure), so 2.1 uses "@id" too.
            id_key = "@id" if version in ("2.0", "2.1") else "id"
            for doc in (manifest, collection):
                ids = []
                _collect_ids(doc.data, id_key, ids)
                assert len(ids) == len(set(ids)), (
                    f"duplicate ids in {version} {doc.kind} {overrides}"
                )
