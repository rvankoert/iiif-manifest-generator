"""End-to-end validation with the official IIIF Presentation Validator.

Skipped when the `iiif-validator` command is not installed. Install with:

    pip install git+https://github.com/IIIF/presentation-validator.git

Note: validating 2.0/2.1 may require network access (JSON-LD context
retrieval); 3.0/4.0 validate fully offline against bundled schemas.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from iiif_manifest_generator.config import GenerationConfig
from iiif_manifest_generator.generate import generate

VALIDATOR = shutil.which("iiif-validator")

CASES = [
    ("2.0", False),
    ("2.1", False),
    ("3.0", False),
    ("3.0", True),
    ("4.0", False),
    ("4.0", True),
]

pytestmark = pytest.mark.skipif(
    VALIDATOR is None, reason="iiif-validator not installed"
)


@pytest.mark.parametrize("version,image_api3", CASES)
def test_generated_tree_passes_official_validator(version, image_api3, image_tree):
    config = GenerationConfig(
        root=image_tree,
        version=version,
        base_url="http://localhost:8080",
        image_api3=image_api3,
    )
    generate(config)
    proc = subprocess.run(
        [VALIDATOR, "validate-dir", "--version", version, str(image_tree)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, (
        f"validator failed for {version} (image_api3={image_api3})\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
