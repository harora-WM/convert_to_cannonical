"""Top-level conversion orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field

from .document import walk_document
from .versions import OAS_31_BASE_DIALECT, TARGET_VERSION, detect_version


@dataclass
class ConversionResult:
    document: dict
    source_version: str
    warnings: list[str] = field(default_factory=list)


def convert_document(document: dict) -> ConversionResult:
    """Convert a parsed OpenAPI 3.0.x/3.1.x/3.2.x document to 3.2.0 in place.

    Idempotent: converting an already-converted document changes nothing.
    """
    detect_version(document)
    source_version = document["openapi"]

    warnings: list[str] = []
    warn = warnings.append

    walk_document(document, warn)

    dialect = document.get("jsonSchemaDialect")
    if dialect == OAS_31_BASE_DIALECT:
        # Absent jsonSchemaDialect means the 3.2 default dialect applies.
        del document["jsonSchemaDialect"]
    elif dialect is not None:
        warn(
            f"jsonSchemaDialect is a custom dialect ({dialect}); kept as-is — "
            "verify it is what you want in a 3.2 document"
        )

    document["openapi"] = TARGET_VERSION
    return ConversionResult(document=document, source_version=source_version, warnings=warnings)
