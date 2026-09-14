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
