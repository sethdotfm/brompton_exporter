# tessera_exporter SCHEMA WALKER // Version 1.0
# https://github.com/sethdotfm/tessera_exporter
"""Schema loading and path matching for the Tessera API (firmware 3.5.2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

_DEFAULT_SCHEMA = Path(__file__).parent / "schema" / "schema_tessera_3.5.2.json"

# Base types that map to Prometheus gauges
_GAUGE_TYPES = frozenset({"Float", "Integer", "Boolean"})

# Base types that produce info metrics (value in label)
_INFO_TYPES = frozenset({"Enum", "String", "TestPatternType"})

# Types that are silently dropped (not representable as metrics)
_DROP_TYPES = frozenset({"ByteArray", "Array"})


def load(path: Optional[str] = None) -> dict:
    """Load the schema file and return the subtree under the 'api' key.

    Never fetches ?help=1 at runtime — the schema is a static repo file.
    """
    p = Path(path) if path else _DEFAULT_SCHEMA
    with open(p) as f:
        data = json.load(f)
    return data["api"]


def match(
    value_path: str,
    schema_root: dict,
) -> tuple[Optional[list[str]], Optional[list[tuple[str, str]]]]:
    """Match a concrete value path against the schema tree.

    Walks value_path segments against the schema. When a segment has no
    literal match, looks for exactly one {placeholder} key and captures
    (sanitised_name, concrete_value) as a label.

    Returns:
        (schema_parts, labels) on success, where:
            schema_parts — list of path segments, placeholders included
            labels       — list of (label_name, label_value); hyphens in
                           label names are replaced with underscores
        (None, None) on any mismatch.
    """
    parts = value_path.strip("/").split("/")
    labels: list[tuple[str, str]] = []
    schema_parts: list[str] = []
    node = schema_root

    for part in parts:
        if not isinstance(node, dict) or "Type" in node:
            # Hit a leaf before consuming all path segments
            return None, None

        if part in node:
            node = node[part]
            schema_parts.append(part)
        else:
            # Look for a single {placeholder} key at this level
            placeholder_keys = [k for k in node if k.startswith("{") and k.endswith("}")]
            if len(placeholder_keys) == 1:
                pk = placeholder_keys[0]
                label_name = pk[1:-1].replace("-", "_")  # strip braces, sanitise
                labels.append((label_name, part))
                node = node[pk]
                schema_parts.append(pk)
            else:
                return None, None

    # Must land on a schema leaf (has a Type key)
    if isinstance(node, dict) and "Type" in node:
        return schema_parts, labels

    return None, None


def leaf(schema_root: dict, schema_parts: list[str]) -> dict:
    """Return the leaf metadata dict for the given schema_parts list."""
    node = schema_root
    for p in schema_parts:
        node = node[p]
    return node


def classify(meta: dict) -> str:
    """Classify a schema leaf as 'drop', 'gauge', or 'info'.

    Rules (in priority order):
      W/O access specifier     -> drop  (write-only RPC triggers)
      Type ByteArray or Array  -> drop  (blobs / arrays)
      Type Float/Integer/Bool  -> gauge
      Type Enum/String/TPT     -> info  (value in label)
    """
    if meta.get("Access Specifier") == "W/O":
        return "drop"
    base_type = meta.get("Type", "").split("(")[0].strip()
    if base_type in _DROP_TYPES:
        return "drop"
    if base_type in _GAUGE_TYPES:
        return "gauge"
    return "info"  # Enum, String, TestPatternType


def all_paths(schema_node: dict, prefix: str = "") -> list[str]:
    """Return all leaf paths in the schema, with {placeholder} segments intact."""
    if not isinstance(schema_node, dict):
        return []
    if "Type" in schema_node:
        return [prefix] if prefix else []
    paths: list[str] = []
    for k, v in schema_node.items():
        child = f"{prefix}/{k}" if prefix else k
        paths.extend(all_paths(v, child))
    return paths
