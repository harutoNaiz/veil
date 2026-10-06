"""Structure and convention checks on the 16 schema files (AC-1.1-04)."""

from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator

from workshop.contracts import (
    CONTRACT_VERSION,
    CONVENTIONS,
    FINGERPRINT_TYPES,
    SPACE_RULE,
    TYPE_FILES,
    TYPES,
)
from workshop.contracts.validate import SCHEMA_DIR, load_schema

EXTRA_FILES = {"tape.schema.json"}  # tape v1 is not one of the 16 contract types
DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"


def contract_objects(schema: dict) -> list[dict]:
    """The object schemas that carry `contractVersion`: the schema itself, or every variant."""
    if "oneOf" in schema:
        return [schema["$defs"][variant["$ref"].rsplit("/", 1)[-1]] for variant in schema["oneOf"]]
    return [schema]


def walk(node: object):
    """Yield every dict inside a JSON structure."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def test_exactly_16_schema_files():
    on_disk = {p.name for p in SCHEMA_DIR.glob("*.schema.json")}
    assert on_disk - EXTRA_FILES == set(TYPE_FILES.values())
    assert len(on_disk - EXTRA_FILES) == 16
    assert len(TYPES) == 16


def test_version_file():
    assert (SCHEMA_DIR / "VERSION").read_text(encoding="utf-8") == f"{CONTRACT_VERSION}\n"


@pytest.mark.parametrize("type_name", TYPES)
def test_valid_draft_2020_12(type_name):
    schema = load_schema(type_name)
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == DRAFT_2020_12
    assert "$id" not in schema
    assert schema["title"] == type_name


@pytest.mark.parametrize("type_name", TYPES)
def test_contract_version_defined(type_name):
    for obj in contract_objects(load_schema(type_name)):
        prop = obj["properties"]["contractVersion"]
        assert prop["type"] == "string"
        assert prop["const"] == CONTRACT_VERSION == "1.0"


@pytest.mark.parametrize("type_name", TYPES)
def test_contract_version_required_except_rect(type_name):
    for obj in contract_objects(load_schema(type_name)):
        if type_name == "Rect":
            assert "contractVersion" not in obj["required"]
        else:
            assert "contractVersion" in obj["required"]


@pytest.mark.parametrize("type_name", FINGERPRINT_TYPES)
def test_fingerprint_types_require_space_id(type_name):
    schema = load_schema(type_name)
    assert "spaceId" in schema["required"]
    assert "spaceId" in schema["properties"]


@pytest.mark.parametrize("type_name", TYPES)
def test_conventions_stated(type_name):
    assert CONVENTIONS in load_schema(type_name)["description"]


@pytest.mark.parametrize("type_name", (*FINGERPRINT_TYPES, "ModelManifest"))
def test_space_rule_stated(type_name):
    assert SPACE_RULE in load_schema(type_name)["description"]


@pytest.mark.parametrize("type_name", TYPES)
def test_defs_titles(type_name):
    schema = load_schema(type_name)
    for key, sub in schema.get("$defs", {}).items():
        assert sub["title"] == schema["title"] + key


@pytest.mark.parametrize("type_name", TYPES)
def test_no_null_anywhere(type_name):
    for node in walk(load_schema(type_name)):
        declared = node.get("type")
        types = declared if isinstance(declared, list) else [declared]
        assert "null" not in types
        assert "null" not in node.get("enum", [])
        assert not ("const" in node and node["const"] is None)


@pytest.mark.parametrize("type_name", TYPES)
def test_objects_closed(type_name):
    for node in walk(load_schema(type_name)):
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False, node.get("title")


@pytest.mark.parametrize("type_name", TYPES)
def test_no_inline_objects(type_name):
    """Every nested object lives in `$defs`, never inline in a property or array item."""
    schema = load_schema(type_name)
    for obj in [*contract_objects(schema), *schema.get("$defs", {}).values()]:
        for prop in obj.get("properties", {}).values():
            for sub in (prop, prop.get("items", {})):
                assert sub.get("type") != "object"
                assert "properties" not in sub


@pytest.mark.parametrize("type_name", TYPES)
def test_enums_are_lower_camel_case(type_name):
    # Names fixed by the spec: tensor layouts, channel orders and the runtime identifiers.
    allowed_exceptions = {
        "RGB",
        "BGR",
        "NCHW",
        "NHWC",
        "onnxruntime-qnn",
        "onnxruntime-cpu",
        "litert-npu",
        "litert-cpu",
        "null-quantile-v1",
        "null-quantile-v2",
    }
    for node in walk(load_schema(type_name)):
        for value in node.get("enum", []):
            if isinstance(value, str) and value not in allowed_exceptions:
                assert value[0].islower() and all(c.isalnum() for c in value), value
