"""oas-canon: convert OpenAPI 3.0.x / 3.1.x documents to canonical 3.2.0."""

from .converter import ConversionResult, convert_document
from .errors import UnsupportedVersionError
from .validate import validate_document

__all__ = [
    "convert_document",
    "ConversionResult",
    "UnsupportedVersionError",
    "validate_document",
]

__version__ = "0.1.0"
