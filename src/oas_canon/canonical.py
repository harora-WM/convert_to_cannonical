"""Optional canonicalization of constructs that 3.2 deprecates.

These rewrites go beyond what the version upgrade requires, so they run
only when the user asks for them (``--canonicalize``).
"""

from __future__ import annotations

from typing import Any

from .schema import Warn


def canonicalize(node: Any, warn: Warn, path: str = "") -> None:
    if isinstance(node, dict):
        _rewrite_xml(node, warn, path)
        _drop_allow_empty_value(node, warn, path)
        for key, value in list(node.items()):
            canonicalize(value, warn, f"{path}/{key}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            canonicalize(item, warn, f"{path}/{i}")


def _rewrite_xml(node: dict, warn: Warn, path: str) -> None:
    xml = node.get("xml")
    if not isinstance(xml, dict):
        return
    if "nodeType" in xml:
        xml.pop("attribute", None)
        xml.pop("wrapped", None)
        return
    if xml.pop("attribute", False):
        xml["nodeType"] = "attribute"
        xml.pop("wrapped", None)
    elif xml.pop("wrapped", False):
        xml["nodeType"] = "element"


def _drop_allow_empty_value(node: dict, warn: Warn, path: str) -> None:
    # Only Parameter objects carry allowEmptyValue; identify them loosely
    # by the presence of name+in so we never touch example payloads.
    if "allowEmptyValue" in node and "name" in node and "in" in node:
        del node["allowEmptyValue"]
        warn(f"{path}: dropped deprecated 'allowEmptyValue'")
