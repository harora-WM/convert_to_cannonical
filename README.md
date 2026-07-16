# oas-canon

Convert any OpenAPI **3.0.x / 3.1.x / 3.2.x** document to canonical **3.2.0**.

The 3.1 → 3.2 hop is backward-compatible (version bump only), so the real work
is migrating 3.0's schema dialect to JSON Schema 2020-12. The converter is
**lossless by default** (`$ref`s are never dereferenced, `x-` extensions and
key order are preserved) and **idempotent** (running it on its own output is
a no-op). This branch is the minimal JSON-only integration build: it operates
on already-parsed dicts and has a single dependency (`jsonschema`).

## Integration (vendor the folder)

This branch is not pip-installable by design — copy the package folder into
your project and add its single dependency:

1. Copy `src/oas_canon/` (keep the folder intact, including `data/`)
   anywhere in your package tree, e.g. `yourapp/oas_canon/`.
2. Add `jsonschema>=4.18` to your `requirements.txt`.
3. Import it like your own code:
   `from yourapp.oas_canon import convert_document, validate_document`

The folder works at any nesting depth (resources are resolved via
`__package__`, not a hardcoded name).

The public API is exactly three names, always imported from the package top
level (submodules are internals and may change):

```python
from yourapp.oas_canon import convert_document, validate_document, UnsupportedVersionError
```

| Name | Purpose |
|---|---|
| `convert_document(spec: dict)` | converts in place; returns a `ConversionResult` with `.document` (the 3.2.0 dict), `.warnings` (list of audit strings — log them), `.source_version` |
| `validate_document(doc: dict)` | returns `[]` if the dict is a valid OAS 3.2.0 document, else human-readable error strings |
| `UnsupportedVersionError` | raised by `convert_document` for Swagger 2.0, malformed versions, or ≥ 3.3 |

> **⚠️ Before wiring this in:** any downstream code that reads OpenAPI
> 3.0-style keywords will silently misbehave on canonical 3.2 documents.
> The classic case is nullability: `schema.get("nullable")` is always
> absent after conversion — check `"null" in schema.get("type", [])`
> (when `type` is a list) instead. Audit consumers for `nullable`,
> boolean `exclusiveMinimum`/`exclusiveMaximum`, schema-level `example`,
> and `format: byte`/`binary` before switching them to converted specs,
> and ship those updates in the same change as the integration.

## Usage (library)

No CLI, no file I/O — pass a parsed spec dict, get a converted dict back:

```python
import json
from oas_canon import convert_document, validate_document

doc = json.loads(spec_bytes)          # any dict works, however you parsed it
result = convert_document(doc)        # mutates in place; returns ConversionResult
for w in result.warnings:             # lossy/ambiguous spots, with exact paths
    log.info("oas-canon: %s", w)

errors = validate_document(result.document)   # [] means valid OAS 3.2.0
if not errors:
    open("openapi-3.2.json", "w").write(json.dumps(result.document, indent=2))
```

`convert_document` raises `UnsupportedVersionError` for Swagger 2.0,
malformed versions, or anything ≥ 3.3. `validate_document` checks against
the official OAS 3.2 JSON Schema (vendored from
[spec.openapis.org/oas/3.2/schema/2025-09-17](https://spec.openapis.org/oas/3.2/schema/2025-09-17))
and returns human-readable error strings.

The full-featured build (CLI, YAML round-trip with comment preservation,
`--canonicalize`) lives on the `main` branch.

## What it transforms (3.0.x input)

| 3.0.x | 3.2.0 |
|---|---|
| `nullable: true` + `type: T` | `type: [T, "null"]` |
| `nullable: true` + `$ref` / `allOf` wrapper | `anyOf: [<inner>, {type: "null"}]` |
| `nullable: true` + `enum` | `null` appended to the enum |
| `nullable: true` + `anyOf`/`oneOf` | `{type: "null"}` branch appended |
| `exclusiveMinimum: true` + `minimum: N` | `exclusiveMinimum: N` (same for maximum) |
| `example: v` (schema keyword) | `examples: [v]` |
| `format: byte` | `contentEncoding: base64` |
| `format: binary` (property level) | `contentMediaType: application/octet-stream` |
| `format: binary` as the whole schema of a binary media type | schema removed (3.1+ raw binary bodies need none) |
| `jsonSchemaDialect` equal to the 3.1 base dialect | removed (3.2 default applies) |

Schemas are found everywhere they can occur: `components.schemas`, parameters,
headers, request bodies, responses, callbacks, webhooks, `pathItems`,
`mediaTypes`, `itemSchema`, encodings, and all nested JSON Schema keywords.

Not supported: Swagger 2.0 input (rejected with a clear error), resolving or
converting external `$ref` targets (convert each file separately).

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/pytest tests
```

(`PYTHONPATH=src` because the package is not installed — the repo runs it
vendor-style, same as an integrating project would.)

Real-world corpus tests (Stripe, GitHub, Discord, Plaid, …) live on the
`main` branch alongside the CLI; this branch keeps the unit and
version-matrix suites only.

Layout: `versions.py` (detection), `schema.py` (3.0-dialect → 2020-12 keyword
transforms), `document.py` (structural walk of every schema location),
`converter.py` (orchestration), `validate.py` (OAS 3.2 gate).
