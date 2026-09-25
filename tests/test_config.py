"""Unit tests for GenerationConfig base-URL normalization."""

from __future__ import annotations

import pytest

from iiif_manifest_generator.config import GenerationConfig


def _norm(value: str) -> str:
    return GenerationConfig._normalize_url(value, "base_url")


def test_normalize_url_strips_trailing_slash():
    assert _norm("http://host:8080/a/b/") == "http://host:8080/a/b"
    assert _norm("http://host:8080/") == "http://host:8080"


def test_normalize_url_percent_encodes_spaces():
    assert _norm("http://host:8080/my scan") == "http://host:8080/my%20scan"
    assert _norm("http://host:8080/my scan/deep scan") == (
        "http://host:8080/my%20scan/deep%20scan"
    )


def test_normalize_url_does_not_double_encode():
    assert _norm("http://host:8080/my%20scan") == "http://host:8080/my%20scan"
    assert _norm("http://host:8080/my%20scan/") == "http://host:8080/my%20scan"


def test_normalize_url_encodes_unicode():
    assert _norm("https://host/scans/é") == "https://host/scans/%C3%A9"


def test_normalize_url_keeps_scheme_and_netloc():
    assert _norm("https://user@host:8443/a b") == "https://user@host:8443/a%20b"


def test_normalize_url_invalid_values_raise():
    with pytest.raises(ValueError, match="base_url must start with"):
        _norm("ftp://host/a")
    with pytest.raises(ValueError, match="must not be empty"):
        _norm("   ")