"""Round-trip loading and dumping of YAML/JSON OpenAPI documents.

YAML input keeps key order and comments (ruamel round-trip mode); JSON
input keeps key order. Output format follows input unless overridden.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from ruamel.yaml import YAML


def make_yaml() -> YAML:
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def load(path: str) -> tuple[dict, str]:
    """Load a document, returning (parsed, format) where format is 'yaml' or 'json'."""
    text = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("{"):
        return json.loads(text), "json"
    doc = make_yaml().load(text)
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: expected a mapping at the document root")
    return doc, "yaml"


def dump(document: dict, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    buf = io.StringIO()
    make_yaml().dump(document, buf)
    return buf.getvalue()
