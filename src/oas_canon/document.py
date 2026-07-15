"""Structural walk of an OpenAPI document, applying schema transforms at
every location a Schema Object may appear (3.0 through 3.2 layouts)."""

from __future__ import annotations

from typing import Any

from .schema import Warn, transform_schema

_HTTP_METHODS = ("get", "put", "post", "delete", "options", "head", "patch", "trace", "query")

# Media types whose payload is the raw bytes themselves; a bare
# `type: string, format: binary` schema there should simply be removed.
_JSONISH = ("json", "xml", "x-www-form-urlencoded", "text/")


def walk_document(doc: dict, warn: Warn) -> None:
    for name, path_item in _items(doc.get("paths"), "paths"):
        _walk_path_item(path_item, warn, f"paths/{name}")
    for name, path_item in _items(doc.get("webhooks"), "webhooks"):
        _walk_path_item(path_item, warn, f"webhooks/{name}")
    _walk_components(doc.get("components"), warn)


def _walk_components(components: Any, warn: Warn) -> None:
    if not isinstance(components, dict):
        return
    for name, schema in _items(components.get("schemas"), "components/schemas"):
        components["schemas"][name] = transform_schema(schema, warn, f"components/schemas/{name}")
    for name, param in _items(components.get("parameters"), "components/parameters"):
        _walk_parameter(param, warn, f"components/parameters/{name}")
    for name, header in _items(components.get("headers"), "components/headers"):
        _walk_parameter(header, warn, f"components/headers/{name}")
    for name, response in _items(components.get("responses"), "components/responses"):
        _walk_response(response, warn, f"components/responses/{name}")
    for name, body in _items(components.get("requestBodies"), "components/requestBodies"):
        _walk_content_holder(body, warn, f"components/requestBodies/{name}")
    for name, callback in _items(components.get("callbacks"), "components/callbacks"):
        _walk_callback(callback, warn, f"components/callbacks/{name}")
    for name, path_item in _items(components.get("pathItems"), "components/pathItems"):
        _walk_path_item(path_item, warn, f"components/pathItems/{name}")
    for name, media in _items(components.get("mediaTypes"), "components/mediaTypes"):
        _walk_media_type(media, name, warn, f"components/mediaTypes/{name}")


def _walk_path_item(path_item: Any, warn: Warn, path: str) -> None:
    if not isinstance(path_item, dict) or "$ref" in path_item:
        return
    _walk_parameter_list(path_item.get("parameters"), warn, f"{path}/parameters")
    for method in _HTTP_METHODS:
        _walk_operation(path_item.get(method), warn, f"{path}/{method}")
    for name, op in _items(path_item.get("additionalOperations"), f"{path}/additionalOperations"):
        _walk_operation(op, warn, f"{path}/additionalOperations/{name}")


def _walk_operation(op: Any, warn: Warn, path: str) -> None:
    if not isinstance(op, dict):
        return
    _walk_parameter_list(op.get("parameters"), warn, f"{path}/parameters")
    _walk_content_holder(op.get("requestBody"), warn, f"{path}/requestBody")
    for code, response in _items(op.get("responses"), f"{path}/responses"):
        _walk_response(response, warn, f"{path}/responses/{code}")
    for name, callback in _items(op.get("callbacks"), f"{path}/callbacks"):
        _walk_callback(callback, warn, f"{path}/callbacks/{name}")


def _walk_callback(callback: Any, warn: Warn, path: str) -> None:
    if not isinstance(callback, dict) or "$ref" in callback:
        return
    for expr, path_item in callback.items():
        _walk_path_item(path_item, warn, f"{path}/{expr}")


def _walk_response(response: Any, warn: Warn, path: str) -> None:
    if not isinstance(response, dict) or "$ref" in response:
        return
    for name, header in _items(response.get("headers"), f"{path}/headers"):
        _walk_parameter(header, warn, f"{path}/headers/{name}")
    _walk_content_holder(response, warn, path)


def _walk_parameter_list(params: Any, warn: Warn, path: str) -> None:
    if isinstance(params, list):
        for i, param in enumerate(params):
            _walk_parameter(param, warn, f"{path}/{i}")


def _walk_parameter(param: Any, warn: Warn, path: str) -> None:
    """Parameter and Header objects: carry either `schema` or `content`."""
    if not isinstance(param, dict) or "$ref" in param:
        return
    if "schema" in param:
        result = transform_schema(param["schema"], warn, f"{path}/schema")
        if result is not None:
            param["schema"] = result
    _walk_content_holder(param, warn, path)


def _walk_content_holder(holder: Any, warn: Warn, path: str) -> None:
    """Anything with a `content` map: request bodies, responses, parameters."""
    if not isinstance(holder, dict) or "$ref" in holder:
        return
    for media_name, media in _items(holder.get("content"), f"{path}/content"):
        _walk_media_type(media, media_name, warn, f"{path}/content/{media_name}")


def _walk_media_type(media: Any, media_name: str, warn: Warn, path: str) -> None:
    if not isinstance(media, dict):
        return
    binaryish = not any(marker in media_name for marker in _JSONISH)
    if "schema" in media:
        result = transform_schema(
            media["schema"], warn, f"{path}/schema", at_media_root=binaryish
        )
        if result is None:
            del media["schema"]
        else:
            media["schema"] = result
    if "itemSchema" in media:
        media["itemSchema"] = transform_schema(media["itemSchema"], warn, f"{path}/itemSchema")
    for enc_name, encoding in _items(media.get("encoding"), f"{path}/encoding"):
        if isinstance(encoding, dict):
            for h_name, header in _items(encoding.get("headers"), f"{path}/encoding/{enc_name}/headers"):
                _walk_parameter(header, warn, f"{path}/encoding/{enc_name}/headers/{h_name}")


def _items(node: Any, path: str):
    if isinstance(node, dict):
        return [(k, v) for k, v in node.items() if not str(k).startswith("x-")]
    return []
