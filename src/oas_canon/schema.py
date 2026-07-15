"""Schema Object transforms: OpenAPI 3.0 schema dialect -> JSON Schema 2020-12.

All functions take and return plain mapping objects. Transforms mutate in
place where possible (to preserve key order and, with ruamel round-trip
maps, comments) and return the node, which may be a replacement dict when
the shape has to change (e.g. wrapping in ``anyOf`` for nullable refs).
"""

from __future__ import annotations

from typing import Any, Callable

Warn = Callable[[str], None]

# Keywords whose value is a single subschema.
_SUBSCHEMA_KEYS = (
    "additionalProperties",
    "items",
    "not",
    "if",
    "then",
    "else",
    "contains",
    "propertyNames",
    "unevaluatedItems",
    "unevaluatedProperties",
    "contentSchema",
)

# Keywords whose value is a map of subschemas.
_SUBSCHEMA_MAP_KEYS = (
    "properties",
    "patternProperties",
    "dependentSchemas",
    "$defs",
    "definitions",
)

# Keywords whose value is a list of subschemas.
_SUBSCHEMA_LIST_KEYS = ("allOf", "anyOf", "oneOf", "prefixItems")


def transform_schema(
    schema: Any,
    warn: Warn,
    path: str = "",
    *,
    at_media_root: bool = False,
) -> Any:
    """Recursively upgrade a 3.0-dialect Schema Object to the 3.2 dialect.

    Safe to run on schemas that are already 3.1/3.2 — every transform is a
    no-op on already-converted input, which keeps the converter idempotent.
    """
    if isinstance(schema, bool) or not isinstance(schema, dict):
        return schema

    _recurse_children(schema, warn, path)

    _convert_exclusive_bounds(schema, warn, path)
    _convert_format(schema)
    _convert_example(schema)
    schema = _convert_nullable(schema, warn, path)

    if at_media_root and _is_bare_binary(schema):
        # A raw binary body needs no schema in 3.1+; signal removal.
        warn(f"{path}: removed 'type: string, format: binary' schema (raw binary bodies need no schema in 3.2)")
        return None

    return schema


def _recurse_children(schema: dict, warn: Warn, path: str) -> None:
    for key in _SUBSCHEMA_KEYS:
        if key in schema:
            schema[key] = transform_schema(schema[key], warn, f"{path}/{key}")
    for key in _SUBSCHEMA_MAP_KEYS:
        value = schema.get(key)
        if isinstance(value, dict):
            for name in list(value):
                value[name] = transform_schema(value[name], warn, f"{path}/{key}/{name}")
    for key in _SUBSCHEMA_LIST_KEYS:
        value = schema.get(key)
        if isinstance(value, list):
            for i, item in enumerate(value):
                value[i] = transform_schema(item, warn, f"{path}/{key}/{i}")


def _convert_exclusive_bounds(schema: dict, warn: Warn, path: str) -> None:
    for exclusive_key, bound_key in (
        ("exclusiveMinimum", "minimum"),
        ("exclusiveMaximum", "maximum"),
    ):
        value = schema.get(exclusive_key)
        if not isinstance(value, bool):
            continue
        if value:
            if bound_key in schema:
                schema[exclusive_key] = schema.pop(bound_key)
            else:
                del schema[exclusive_key]
                warn(f"{path}: dropped '{exclusive_key}: true' with no paired '{bound_key}'")
        else:
            del schema[exclusive_key]


# 3.0-era format values naming a content encoding; contentEncoding accepts
# all RFC 4648 encodings plus quoted-printable from RFC 2045. `byte` is the
# official 3.0 spelling of base64; the rest were common unofficial usage.
_ENCODING_FORMATS = {
    "byte": "base64",
    "base64": "base64",
    "base64url": "base64url",
    "base16": "base16",
    "base32": "base32",
    "quoted-printable": "quoted-printable",
}


def _convert_format(schema: dict) -> None:
    fmt = schema.get("format")
    if fmt in _ENCODING_FORMATS:
        del schema["format"]
        schema.setdefault("contentEncoding", _ENCODING_FORMATS[fmt])
    elif fmt == "binary":
        del schema["format"]
        schema.setdefault("contentMediaType", "application/octet-stream")


def _convert_example(schema: dict) -> None:
    if "example" in schema and "examples" not in schema:
        schema["examples"] = [schema.pop("example")]


def _convert_nullable(schema: dict, warn: Warn, path: str) -> dict:
    if "nullable" not in schema:
        return schema
    nullable = schema.pop("nullable")
    if not nullable:
        return schema

    enum = schema.get("enum")
    if isinstance(enum, list) and None not in enum:
        enum.append(None)

    type_value = schema.get("type")
    if type_value is not None:
        if isinstance(type_value, list):
            if "null" not in type_value:
                type_value.append("null")
        elif type_value != "null":
            schema["type"] = [type_value, "null"]
        return schema

    if isinstance(enum, list):
        # enum-only schema: appending null above is sufficient.
        return schema

    for key in ("anyOf", "oneOf"):
        branches = schema.get(key)
        if isinstance(branches, list):
            if not any(isinstance(b, dict) and b.get("type") == "null" for b in branches):
                branches.append({"type": "null"})
            return schema

    if "$ref" in schema or "allOf" in schema:
        # 3.0 authors wrote `nullable: true` next to a $ref (or an allOf
        # wrapper around one). Express "X or null" with anyOf, keeping
        # annotation keywords on the parent where they remain valid.
        annotations = {}
        inner = {}
        for key in list(schema):
            if key in ("title", "description", "deprecated", "examples", "default"):
                annotations[key] = schema.pop(key)
            else:
                inner[key] = schema.pop(key)
        schema.update(annotations)
        schema["anyOf"] = [inner, {"type": "null"}]
        return schema

    warn(f"{path}: dropped 'nullable: true' on a schema with no type, ref or composition")
    return schema


def _is_bare_binary(schema: Any) -> bool:
    return (
        isinstance(schema, dict)
        and set(schema) == {"type", "contentMediaType"}
        and schema.get("type") == "string"
        and schema.get("contentMediaType") == "application/octet-stream"
    )
