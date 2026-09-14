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
