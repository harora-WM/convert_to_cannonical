"""Corpus tests: convert real-world specs and validate the result.

Run ``python scripts/fetch_corpus.py`` first; each spec found in
tests/corpus/ is converted, checked for idempotency, and validated
against the official OAS 3.2 schema. Skipped when the corpus is absent.
"""

import copy
import json
from pathlib import Path

import pytest

from oas_canon import convert_document, validate_document

CORPUS = Path(__file__).parent / "corpus"


def corpus_files():
    if not CORPUS.is_dir():
        return []
    return sorted(p for p in CORPUS.iterdir() if p.suffix in (".json", ".yaml", ".yml"))


def load_plain(path: Path):
    """Plain-dict load (no round-trip overhead) — corpus specs are large."""
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    from ruamel.yaml import YAML

    return YAML(typ="safe").load(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "spec_path", corpus_files() or [pytest.param(None, marks=pytest.mark.skip(
        reason="corpus not downloaded; run scripts/fetch_corpus.py"))],
    ids=lambda p: p.name if p else "corpus",
)
def test_corpus_spec_converts_and_validates(spec_path):
    doc = load_plain(spec_path)

    result = convert_document(doc)
    converted = result.document
    assert converted["openapi"] == "3.2.0"

    # No 3.0-isms may survive anywhere in the document.
    leftovers = find_30_leftovers(converted)
    assert leftovers == [], f"3.0 constructs survived conversion: {leftovers[:10]}"

    # Idempotent: converting the converted document changes nothing.
    frozen = copy.deepcopy(converted)
    again = convert_document(converted).document
    assert again == frozen, "second conversion changed the document"

    # The output must be a valid OAS 3.2 document.
    errors = validate_document(converted)
    assert errors == [], f"validation errors: {errors[:10]}"


def find_30_leftovers(node, path="", acc=None):
    """Scan for nullable / boolean exclusive bounds outside example values."""
    if acc is None:
        acc = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("example", "examples", "default", "enum", "const"):
                continue  # payload values may legitimately contain these words
            if str(key).startswith("x-"):
                continue  # extension content is opaque; the converter leaves it alone
            if key == "nullable":
                acc.append(f"{path}/nullable")
            if key in ("exclusiveMinimum", "exclusiveMaximum") and isinstance(value, bool):
                acc.append(f"{path}/{key}")
            find_30_leftovers(value, f"{path}/{key}", acc)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            find_30_leftovers(item, f"{path}/{i}", acc)
    return acc
