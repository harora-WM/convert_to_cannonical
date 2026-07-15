from oas_canon.schema import transform_schema


def convert(schema, **kwargs):
    warnings = []
    result = transform_schema(schema, warnings.append, **kwargs)
    return result, warnings


def test_nullable_with_type():
    result, _ = convert({"type": "string", "nullable": True})
    assert result == {"type": ["string", "null"]}


def test_nullable_false_is_just_removed():
    result, _ = convert({"type": "string", "nullable": False})
    assert result == {"type": "string"}


def test_nullable_with_type_list_already_null():
    result, _ = convert({"type": ["string", "null"], "nullable": True})
    assert result == {"type": ["string", "null"]}


def test_nullable_with_enum_and_type():
    result, _ = convert({"type": "string", "enum": ["a", "b"], "nullable": True})
    assert result == {"type": ["string", "null"], "enum": ["a", "b", None]}


def test_nullable_with_enum_only():
    result, _ = convert({"enum": ["a", "b"], "nullable": True})
    assert result == {"enum": ["a", "b", None]}


def test_nullable_with_ref():
    result, _ = convert({"$ref": "#/components/schemas/Pet", "nullable": True})
    assert result == {
        "anyOf": [{"$ref": "#/components/schemas/Pet"}, {"type": "null"}]
    }


def test_nullable_with_allof_wrapper_keeps_description_outside():
    result, _ = convert(
        {
            "allOf": [{"$ref": "#/components/schemas/Pet"}],
            "description": "maybe a pet",
            "nullable": True,
        }
    )
    assert result == {
        "description": "maybe a pet",
        "anyOf": [
            {"allOf": [{"$ref": "#/components/schemas/Pet"}]},
            {"type": "null"},
        ],
    }


def test_nullable_with_oneof_appends_null_branch():
    result, _ = convert({"oneOf": [{"type": "string"}], "nullable": True})
    assert result == {"oneOf": [{"type": "string"}, {"type": "null"}]}


def test_nullable_without_type_warns():
    result, warnings = convert({"nullable": True})
    assert result == {}
    assert len(warnings) == 1


def test_exclusive_minimum_true():
    result, _ = convert({"type": "number", "minimum": 5, "exclusiveMinimum": True})
    assert result == {"type": "number", "exclusiveMinimum": 5}


def test_exclusive_maximum_false():
    result, _ = convert({"type": "number", "maximum": 5, "exclusiveMaximum": False})
    assert result == {"type": "number", "maximum": 5}


def test_exclusive_minimum_true_without_minimum_warns():
    result, warnings = convert({"type": "number", "exclusiveMinimum": True})
    assert result == {"type": "number"}
    assert len(warnings) == 1


def test_numeric_exclusive_bounds_untouched():
    result, _ = convert({"type": "number", "exclusiveMinimum": 3})
    assert result == {"type": "number", "exclusiveMinimum": 3}


def test_example_to_examples():
    result, _ = convert({"type": "string", "example": "hi"})
    assert result == {"type": "string", "examples": ["hi"]}


def test_example_not_clobbering_existing_examples():
    result, _ = convert({"type": "string", "example": "hi", "examples": ["yo"]})
    assert result == {"type": "string", "example": "hi", "examples": ["yo"]}


def test_format_byte():
    result, _ = convert({"type": "string", "format": "byte"})
    assert result == {"type": "string", "contentEncoding": "base64"}


def test_format_binary_property_level():
    result, _ = convert(
        {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}
    )
    assert result["properties"]["file"] == {
        "type": "string",
        "contentMediaType": "application/octet-stream",
    }


def test_format_binary_at_media_root_removed():
    result, warnings = convert(
        {"type": "string", "format": "binary"}, at_media_root=True
    )
    assert result is None
    assert len(warnings) == 1


def test_other_formats_untouched():
    result, _ = convert({"type": "string", "format": "date-time"})
    assert result == {"type": "string", "format": "date-time"}


def test_nested_recursion():
    result, _ = convert(
        {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "nullable": True},
                }
            },
            "additionalProperties": {"type": "integer", "nullable": True},
        }
    )
    assert result["properties"]["tags"]["items"] == {"type": ["string", "null"]}
    assert result["additionalProperties"] == {"type": ["integer", "null"]}


def test_boolean_schema_passthrough():
    result, _ = convert({"type": "object", "additionalProperties": False})
    assert result == {"type": "object", "additionalProperties": False}
