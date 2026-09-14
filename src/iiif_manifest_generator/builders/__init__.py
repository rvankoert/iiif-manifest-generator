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
