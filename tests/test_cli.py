import json
from pathlib import Path

from oas_canon.cli import main
from oas_canon.io import make_yaml

FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_yaml_roundtrip(tmp_path, capsys):
    out = tmp_path / "out.yaml"
    code = main([str(FIXTURES / "petstore-3.0.yaml"), "-o", str(out), "-q"])
    assert code == 0

    doc = make_yaml().load(out.read_text())
    assert doc["openapi"] == "3.2.0"
    param = doc["paths"]["/pets"]["get"]["parameters"][0]["schema"]
    assert list(param["type"]) == ["integer", "null"]
    assert param["exclusiveMinimum"] == 0
    assert "minimum" not in param
    pet = doc["components"]["schemas"]["Pet"]["properties"]
    assert list(pet["name"]["examples"]) == ["Rex"]
    assert pet["photo"]["contentEncoding"] == "base64"

    # comments survive the round trip
    assert out.read_text().startswith("# A small 3.0 spec")


def test_cli_json_output(tmp_path):
    out = tmp_path / "out.json"
    code = main(
        [str(FIXTURES / "petstore-3.0.yaml"), "-o", str(out), "--format", "json", "-q"]
    )
    assert code == 0
    doc = json.loads(out.read_text())
    assert doc["openapi"] == "3.2.0"


def test_cli_rejects_swagger2(tmp_path, capsys):
    bad = tmp_path / "swagger.json"
    bad.write_text(json.dumps({"swagger": "2.0", "info": {}}))
    assert main([str(bad)]) == 2
    assert "Swagger 2.0" in capsys.readouterr().err


def test_cli_missing_file(capsys):
    assert main(["nope.yaml"]) == 2
