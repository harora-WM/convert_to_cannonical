import json
from pathlib import Path

from oas_canon import convert_document, validate_document

FIXTURES = Path(__file__).parent / "fixtures"


def test_minimal_valid_document():
    doc = {
        "openapi": "3.2.0",
        "info": {"title": "t", "version": "1"},
        "paths": {},
    }
    assert validate_document(doc) == []


def test_converted_fixture_is_valid():
    doc = json.loads((FIXTURES / "petstore-3.0.json").read_text())
    result = convert_document(doc)
    assert validate_document(result.document) == []


def test_invalid_document_reports_errors():
    doc = {
        "openapi": "3.2.0",
        "info": {"title": "t"},  # missing required 'version'
        "paths": {},
    }
    errors = validate_document(doc)
    assert errors
    assert any("version" in e for e in errors)


def test_error_paths_point_at_instance_location():
    doc = {
        "openapi": "3.2.0",
        "info": {"title": "t", "version": "1"},
        "paths": {"/x": {"get": {"parameters": [{"schema": {"type": "string"}}]}}},
    }
    errors = validate_document(doc)
    assert any(
        "/paths//x/get/parameters/0" in e and "'name' is a required property" in e
        for e in errors
    )


def test_invalid_input_reports_instead_of_writing():
    # library-level equivalent of the old CLI --validate gate
    doc = {"openapi": "3.0.3", "info": {"title": "t"}, "paths": {}}  # version missing
    result = convert_document(doc)
    errors = validate_document(result.document)
    assert any("version" in e for e in errors)
