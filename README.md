# oas-canon

Convert any OpenAPI **3.0.x / 3.1.x / 3.2.x** document to canonical **3.2.0**.

The 3.1 → 3.2 hop is backward-compatible (version bump only), so the real work
is migrating 3.0's schema dialect to JSON Schema 2020-12. The converter is
**lossless by default** (`$ref`s are never dereferenced, `x-` extensions and
YAML comments/key order are preserved) and **idempotent** (running it on its
own output is a no-op).

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Usage (library)

This branch is the minimal integration build — no CLI; call the API:

```python
from oas_canon import convert_document, validate_document
from oas_canon.io import load, dump   # optional round-trip file helpers

doc, fmt = load("openapi.yaml")       # or any dict you already parsed
result = convert_document(doc)        # mutates in place; returns ConversionResult
for w in result.warnings:             # lossy/ambiguous spots, with exact paths
    log.info("oas-canon: %s", w)

errors = validate_document(result.document)   # [] means valid OAS 3.2.0
if not errors:
    open("openapi-3.2.yaml", "w").write(dump(result.document, fmt))
```

`convert_document` raises `UnsupportedVersionError` for Swagger 2.0,
malformed versions, or anything ≥ 3.3. `validate_document` checks against
the official OAS 3.2 JSON Schema (vendored from
[spec.openapis.org/oas/3.2/schema/2025-09-17](https://spec.openapis.org/oas/3.2/schema/2025-09-17))
and returns human-readable error strings.

The full-featured build (CLI, `--canonicalize`) lives on the `main` branch.

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
.venv/bin/pytest
```

### Corpus tests

Real-world specs (Swagger Petstore, Stripe, GitHub REST — both 3.0 and 3.1
flavours) are exercised end-to-end: converted, scanned for surviving 3.0
constructs, checked for idempotency, and validated against the OAS 3.2
schema. The corpus is large and gitignored; download it once with:

```bash
python scripts/fetch_corpus.py
.venv/bin/pytest tests/test_corpus.py
```

Without the download the corpus tests skip automatically.

Layout: `versions.py` (detection), `schema.py` (3.0-dialect → 2020-12 keyword
transforms), `document.py` (structural walk of every schema location),
`converter.py` (orchestration), `validate.py` (OAS 3.2 gate),
`io.py` (round-trip YAML/JSON).
