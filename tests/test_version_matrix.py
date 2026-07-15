"""Full input-range matrix: every published 3.0.x and 3.1.x version must
convert to a document that validates against the official OAS 3.2 schema."""

import copy

import pytest

from oas_canon import convert_document, validate_document
from test_corpus import find_30_leftovers

ALL_30 = ["3.0.0", "3.0.1", "3.0.2", "3.0.3", "3.0.4"]
ALL_31 = ["3.1.0", "3.1.1", "3.1.2"]


def doc_30(version):
    """A 3.0-flavoured document exercising every 3.0-only construct."""
    return {
        "openapi": version,
        "info": {"title": "Matrix", "version": "1.0.0"},
        "paths": {
            "/things/{id}": {
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "example": "abc"},
                    }
                ],
                "get": {
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {
                                "type": "integer",
                                "minimum": 0,
                                "exclusiveMinimum": True,
                                "maximum": 100,
                                "exclusiveMaximum": False,
                                "nullable": True,
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Thing"}
                                }
                            },
                        }
                    },
                },
                "put": {
                    "requestBody": {
                        "content": {
                            "application/octet-stream": {
                                "schema": {"type": "string", "format": "binary"}
                            },
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "blob": {"type": "string", "format": "binary"},
                                        "sig": {"type": "string", "format": "byte"},
                                    },
                                }
                            },
                        }
                    },
                    "responses": {"204": {"description": "done"}},
                },
            }
        },
        "components": {
            "schemas": {
                "Thing": {
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["on", "off"],
                            "nullable": True,
                        },
                        "owner": {
                            "allOf": [{"$ref": "#/components/schemas/Owner"}],
                            "nullable": True,
                        },
                        "score": {
                            "oneOf": [{"type": "integer"}, {"type": "string"}],
                            "nullable": True,
                        },
                    },
                },
                "Owner": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        },
    }


def doc_31(version):
    """A 3.1-flavoured document using 3.1-only features (must pass through)."""
    return {
        "openapi": version,
        "info": {
            "title": "Matrix31",
            "version": "1.0.0",
            "summary": "3.1 features",
            "license": {"name": "MIT", "identifier": "MIT"},
        },
        "jsonSchemaDialect": "https://spec.openapis.org/oas/3.1/dialect/base",
        "webhooks": {
            "ping": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Event",
                                    "description": "ref with sibling, legal in 3.1",
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
        "components": {
            "schemas": {
                "Event": {
                    "type": ["object", "null"],
                    "properties": {
                        "kind": {"type": "string", "examples": ["created"]},
                        "size": {"type": "integer", "exclusiveMinimum": 0},
                        "payload": {
                            "type": "string",
                            "contentEncoding": "base64",
                            "contentMediaType": "application/octet-stream",
                        },
                    },
                    "$defs": {"Inner": {"type": ["string", "null"]}},
                }
            },
            "pathItems": {
                "reusable": {
                    "get": {"responses": {"200": {"description": "ok"}}}
                }
            },
        },
    }


def assert_qualified_32(doc):
    result = convert_document(doc)
    converted = result.document

    assert converted["openapi"] == "3.2.0"

    leftovers = find_30_leftovers(converted)
    assert leftovers == [], f"3.0 constructs survived: {leftovers}"

    frozen = copy.deepcopy(converted)
    assert convert_document(converted).document == frozen, "not idempotent"

    errors = validate_document(converted)
    assert errors == [], f"not a valid OAS 3.2 document: {errors[:5]}"
    return converted


@pytest.mark.parametrize("version", ALL_30)
def test_every_30_patch_converts_to_valid_32(version):
    converted = assert_qualified_32(doc_30(version))

    limit = converted["paths"]["/things/{id}"]["get"]["parameters"][0]["schema"]
    assert limit == {
        "type": ["integer", "null"],
        "exclusiveMinimum": 0,
        "maximum": 100,
    }
    props = converted["components"]["schemas"]["Thing"]["properties"]
    assert props["status"] == {
        "type": ["string", "null"],
        "enum": ["on", "off", None],
    }
    assert props["score"]["oneOf"][-1] == {"type": "null"}


@pytest.mark.parametrize("version", ALL_31)
def test_every_31_patch_converts_to_valid_32(version):
    converted = assert_qualified_32(doc_31(version))

    # 3.1 content must pass through unchanged apart from the version and
    # the now-redundant jsonSchemaDialect.
    assert "jsonSchemaDialect" not in converted
    expected = doc_31(version)
    del expected["jsonSchemaDialect"]
    expected["openapi"] = "3.2.0"
    assert converted == expected


def test_already_32_is_untouched():
    doc = doc_31("3.2.0")
    del doc["jsonSchemaDialect"]
    expected = copy.deepcopy(doc)
    converted = convert_document(doc).document
    assert converted == expected
    assert validate_document(converted) == []
