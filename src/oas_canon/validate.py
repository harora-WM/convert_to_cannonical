"""Validation gate: check a document against the official OAS 3.2 JSON Schema.

The meta-schema is vendored from
https://spec.openapis.org/oas/3.2/schema/2025-09-17 (the OAI-published
schema that validates document structure without Schema Object dialect
validation).
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files

from jsonschema import Draft202012Validator

SCHEMA_RESOURCE = "data/oas-3.2-schema.json"


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    text = files("oas_canon").joinpath(SCHEMA_RESOURCE).read_text(encoding="utf-8")
    schema = json.loads(text)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _jsonify(node):
    """Coerce to the JSON data model: map keys become strings.

    Unquoted YAML scalars like ``200:`` parse as integer keys and would
    crash regex-based keyword checks in jsonschema.
    """
    if isinstance(node, dict):
        return {str(k): _jsonify(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_jsonify(v) for v in node]
    return node


def validate_document(document: dict, *, limit: int = 20) -> list[str]:
    """Validate against the OAS 3.2 schema; return human-readable errors.

    An empty list means the document is valid. At most ``limit`` errors are
    returned, deepest-instance-path first so the most specific problems
    surface before generic oneOf noise.
    """
    errors = sorted(
        _validator().iter_errors(_jsonify(document)),
        key=lambda e: len(e.absolute_path),
        reverse=True,
    )
    messages = []
    for error in errors[:limit]:
        where = "/" + "/".join(str(p) for p in error.absolute_path)
        messages.append(f"{where}: {error.message}")
    if len(errors) > limit:
        messages.append(f"... and {len(errors) - limit} more error(s)")
    return messages
