"""Atomic file I/O for Phase 4 semantic maps."""

import json
import os
from pathlib import Path
import tempfile

from .semantic_model import SemanticMap
from .semantic_validation import validate_semantic_map


class SemanticFileError(ValueError):
    pass


def load_semantic_map(path):
    path = Path(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    return SemanticMap.from_geojson(document)


def save_semantic_map(semantic_map, path, validate=True):
    if validate:
        report = validate_semantic_map(semantic_map)
        if not report.valid:
            codes = ", ".join(issue.code for issue in report.issues)
            raise SemanticFileError(f"semantic map validation failed: {codes}")
    text = json.dumps(semantic_map.to_geojson(), ensure_ascii=False, indent=2) + "\n"
    _atomic_write_text(Path(path), text)


def _atomic_write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
