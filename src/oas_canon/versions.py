"""OpenAPI version detection and validation."""

from __future__ import annotations

import re

from .errors import UnsupportedVersionError

TARGET_VERSION = "3.2.0"

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

# 3.1's default JSON Schema dialect. In a 3.2 document the 3.2 default
# dialect applies when jsonSchemaDialect is absent, so we drop this one.
OAS_31_BASE_DIALECT = "https://spec.openapis.org/oas/3.1/dialect/base"


def detect_version(document: dict) -> tuple[int, int, int]:
    """Return the (major, minor, patch) of a supported input document.

    Raises UnsupportedVersionError for Swagger 2.0, OpenAPI >= 3.3, malformed
    version strings, or a missing ``openapi`` field.
    """
    raw = document.get("openapi")
    if raw is None:
        if "swagger" in document:
            raise UnsupportedVersionError(
                "Swagger 2.0 documents are not supported; convert to OpenAPI 3.x first"
            )
        raise UnsupportedVersionError("document has no 'openapi' field")
    if not isinstance(raw, str):
        raise UnsupportedVersionError(
            f"'openapi' must be a string, got {type(raw).__name__}: {raw!r} "
            "(a YAML float here usually means the version was written unquoted)"
        )
    match = _VERSION_RE.match(raw)
    if not match:
        raise UnsupportedVersionError(f"malformed OpenAPI version string: {raw!r}")
    major, minor, patch = (int(g) for g in match.groups())
    if major != 3 or minor not in (0, 1, 2):
        raise UnsupportedVersionError(
            f"unsupported OpenAPI version {raw}; supported inputs are 3.0.x, 3.1.x and 3.2.x"
        )
    return major, minor, patch
