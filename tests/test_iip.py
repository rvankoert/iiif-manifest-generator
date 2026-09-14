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
