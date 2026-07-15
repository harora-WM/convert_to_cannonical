"""Command-line interface: oas-canon INPUT [-o OUTPUT]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .converter import convert_document
from .errors import UnsupportedVersionError
from .io import dump, load


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="oas-canon",
        description="Convert an OpenAPI 3.0.x/3.1.x/3.2.x document to canonical 3.2.0.",
    )
    parser.add_argument("input", help="input spec file (YAML or JSON), or '-' for stdin")
    parser.add_argument("-o", "--output", help="output file (default: stdout)")
    parser.add_argument(
        "--format",
        choices=["yaml", "json"],
        help="output format (default: same as input)",
    )
    parser.add_argument(
        "--canonicalize",
        action="store_true",
        help="also rewrite constructs 3.2 deprecates (xml attribute/wrapped, allowEmptyValue)",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="suppress conversion warnings on stderr"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    try:
        document, in_format = load(args.input)
    except FileNotFoundError:
        print(f"error: no such file: {args.input}", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"error: could not parse {args.input}: {exc}", file=sys.stderr)
        return 2

    try:
        result = convert_document(document, canonical=args.canonicalize)
    except UnsupportedVersionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        for warning in result.warnings:
            print(f"warning: {warning}", file=sys.stderr)
        print(
            f"converted OpenAPI {result.source_version} -> 3.2.0"
            + (f" ({len(result.warnings)} warning(s))" if result.warnings else ""),
            file=sys.stderr,
        )

    text = dump(result.document, args.format or in_format)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
