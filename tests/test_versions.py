import pytest

from oas_canon.errors import UnsupportedVersionError
from oas_canon.versions import detect_version


@pytest.mark.parametrize(
    "version, expected",
    [
        ("3.0.0", (3, 0, 0)),
        ("3.0.4", (3, 0, 4)),
        ("3.1.1", (3, 1, 1)),
        ("3.2.0", (3, 2, 0)),
    ],
)
def test_supported_versions(version, expected):
    assert detect_version({"openapi": version}) == expected


@pytest.mark.parametrize(
    "doc",
    [
        {"swagger": "2.0"},
        {},
        {"openapi": "4.0.0"},
        {"openapi": "3.3.0"},
        {"openapi": "2.0"},
        {"openapi": "3.0"},
        {"openapi": 3.0},
        {"openapi": "3.0.x"},
    ],
)
def test_unsupported_versions(doc):
    with pytest.raises(UnsupportedVersionError):
        detect_version(doc)
