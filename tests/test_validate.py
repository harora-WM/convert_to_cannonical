from pathlib import Path

from oas_canon import convert_document, validate_document
from oas_canon.cli import main
from oas_canon.io import load

FIXTURES = Path(__file__).parent / "fixtures"


def test_minimal_valid_document():
    doc = {
        "openapi": "3.2.0",
        "info": {"title": "t", "version": "1"},
        "paths": {},
    }
    assert validate_document(doc) == []


def test_converted_fixture_is_valid():
    doc, _ = load(str(FIXTURES / "petstore-3.0.yaml"))
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


def test_cli_validate_pass(tmp_path):
    out = tmp_path / "out.yaml"
    code = main([str(FIXTURES / "petstore-3.0.yaml"), "-o", str(out), "--validate", "-q"])
    assert code == 0
    assert out.exists()


def test_cli_validate_fail_writes_nothing(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text('openapi: "3.0.3"\ninfo:\n  title: t\npaths: {}\n')  # info.version missing
    out = tmp_path / "out.yaml"
    code = main([str(bad), "-o", str(out), "--validate"])
    assert code == 1
    assert not out.exists()
    assert "failed OAS 3.2 validation" in capsys.readouterr().err
