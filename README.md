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

## Usage

```bash
oas-canon api-3.0.yaml                     # convert, write YAML to stdout
oas-canon api-3.0.yaml -o api-3.2.yaml     # write to a file
oas-canon api.json --format yaml           # JSON in, YAML out
oas-canon api.yaml --validate -o out.yaml  # gate output on OAS 3.2 validity
cat api.yaml | oas-canon -                 # read from stdin
```

Warnings (lossy or ambiguous spots) go to stderr; `-q` silences them.

`--validate` checks the converted document against the official OAS 3.2
JSON Schema (vendored from
[spec.openapis.org/oas/3.2/schema/2025-09-17](https://spec.openapis.org/oas/3.2/schema/2025-09-17));
on failure it prints the errors, writes nothing, and exits 1. The same gate
is available programmatically via `oas_canon.validate_document(doc)`.

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
`converter.py` (orchestration), `io.py` (round-trip YAML/JSON), `cli.py`.
