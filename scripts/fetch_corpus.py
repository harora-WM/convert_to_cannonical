#!/usr/bin/env python3
"""Download real-world OpenAPI specs into tests/corpus/ for corpus tests.

The corpus is gitignored; run this once locally (or in CI) before
`pytest tests/test_corpus.py`.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent / "tests" / "corpus"

SPECS = {
    # Swagger Petstore, OpenAPI 3.0
    "petstore-3.0.yaml": "https://raw.githubusercontent.com/swagger-api/swagger-petstore/master/src/main/resources/openapi.yaml",
    # Stripe's full API, OpenAPI 3.0 (~7 MB)
    "stripe-3.0.json": "https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json",
    # GitHub's REST API, OpenAPI 3.0 (~10 MB)
    "github-3.0.json": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json",
    # GitHub's REST API, OpenAPI 3.1 flavour
    "github-3.1.json": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions-next/api.github.com/api.github.com.json",
}


def main() -> int:
    CORPUS.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name, url in SPECS.items():
        dest = CORPUS / name
        if dest.exists():
            print(f"cached   {name} ({dest.stat().st_size // 1024} KiB)")
            continue
        print(f"fetching {name} <- {url}")
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                dest.write_bytes(resp.read())
            print(f"saved    {name} ({dest.stat().st_size // 1024} KiB)")
        except OSError as exc:
            failures += 1
            print(f"FAILED   {name}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
