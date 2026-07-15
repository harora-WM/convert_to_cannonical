import copy

from oas_canon import convert_document


def petstore_30():
    return {
        "openapi": "3.0.3",
        "info": {"title": "Pets", "version": "1.0.0"},
        "paths": {
            "/pets": {
                "get": {
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "schema": {
                                "type": "integer",
                                "minimum": 0,
                                "exclusiveMinimum": True,
                                "nullable": True,
                            },
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Pets"}
                                }
                            },
                        }
                    },
                },
                "post": {
                    "requestBody": {
                        "content": {
                            "application/octet-stream": {
                                "schema": {"type": "string", "format": "binary"}
                            },
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "avatar": {"type": "string", "format": "binary"},
                                        "token": {"type": "string", "format": "byte"},
                                    },
                                }
                            },
                        }
                    },
                    "responses": {"201": {"description": "created"}},
                },
            }
        },
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "example": "Rex"},
                        "owner": {
                            "allOf": [{"$ref": "#/components/schemas/Person"}],
                            "nullable": True,
                        },
                    },
                },
                "Pets": {"type": "array", "items": {"$ref": "#/components/schemas/Pet"}},
                "Person": {"type": "object"},
            }
        },
    }


def make_doc():
    return petstore_30()


def test_version_bumped():
    result = convert_document(make_doc())
    assert result.document["openapi"] == "3.2.0"
    assert result.source_version == "3.0.3"


def test_parameter_schema_converted():
    doc = convert_document(make_doc()).document
    schema = doc["paths"]["/pets"]["get"]["parameters"][0]["schema"]
    assert schema == {"type": ["integer", "null"], "exclusiveMinimum": 0}


def test_binary_body_schema_removed():
    doc = convert_document(make_doc()).document
    content = doc["paths"]["/pets"]["post"]["requestBody"]["content"]
    assert "schema" not in content["application/octet-stream"]


def test_multipart_binary_property_converted():
    doc = convert_document(make_doc()).document
    props = doc["paths"]["/pets"]["post"]["requestBody"]["content"][
        "multipart/form-data"
    ]["schema"]["properties"]
    assert props["avatar"] == {
        "type": "string",
        "contentMediaType": "application/octet-stream",
    }
    assert props["token"] == {"type": "string", "contentEncoding": "base64"}


def test_component_schemas_converted():
    doc = convert_document(make_doc()).document
    pet = doc["components"]["schemas"]["Pet"]
    assert pet["properties"]["name"] == {"type": "string", "examples": ["Rex"]}
    assert pet["properties"]["owner"] == {
        "anyOf": [
            {"allOf": [{"$ref": "#/components/schemas/Person"}]},
            {"type": "null"},
        ]
    }


def test_idempotent():
    once = convert_document(make_doc()).document
    frozen = copy.deepcopy(once)
    twice = convert_document(once).document
    assert twice == frozen


def test_31_dialect_dropped():
    doc = {
        "openapi": "3.1.0",
        "info": {"title": "t", "version": "1"},
        "jsonSchemaDialect": "https://spec.openapis.org/oas/3.1/dialect/base",
        "paths": {},
    }
    result = convert_document(doc)
    assert "jsonSchemaDialect" not in result.document


def test_custom_dialect_kept_with_warning():
    doc = {
        "openapi": "3.1.0",
        "info": {"title": "t", "version": "1"},
        "jsonSchemaDialect": "https://example.com/my-dialect",
        "paths": {},
    }
    result = convert_document(doc)
    assert result.document["jsonSchemaDialect"] == "https://example.com/my-dialect"
    assert any("jsonSchemaDialect" in w for w in result.warnings)


def test_webhooks_walked():
    doc = {
        "openapi": "3.1.0",
        "info": {"title": "t", "version": "1"},
        "webhooks": {
            "newPet": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"type": "string", "nullable": True}
                            }
                        }
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }
    result = convert_document(doc)
    schema = result.document["webhooks"]["newPet"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert schema == {"type": ["string", "null"]}


def test_canonicalize_xml_and_allow_empty_value():
    doc = {
        "openapi": "3.1.0",
        "info": {"title": "t", "version": "1"},
        "paths": {
            "/a": {
                "get": {
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "allowEmptyValue": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
        "components": {
            "schemas": {
                "Thing": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "xml": {"attribute": True}},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "xml": {"wrapped": True},
                        },
                    },
                }
            }
        },
    }
    result = convert_document(doc, canonical=True)
    props = result.document["components"]["schemas"]["Thing"]["properties"]
    assert props["id"]["xml"] == {"nodeType": "attribute"}
    assert props["tags"]["xml"] == {"nodeType": "element"}
    param = result.document["paths"]["/a"]["get"]["parameters"][0]
    assert "allowEmptyValue" not in param


def test_integer_response_code_keys_stringified():
    doc = {
        "openapi": "3.0.0",
        "info": {"title": "t", "version": "1"},
        "paths": {
            "/a": {
                "get": {
                    "responses": {
                        200: {"description": "ok"},
                        "default": {"description": "err"},
                    }
                }
            }
        },
    }
    result = convert_document(doc)
    responses = result.document["paths"]["/a"]["get"]["responses"]
    assert list(responses) == ["200", "default"]
    assert any("non-string map keys" in w for w in result.warnings)
