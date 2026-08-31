"""Tests for schema.py — loading, matching, classification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import schema as _schema

FIXTURES = Path(__file__).parent / "fixtures"
FIXTURE_FILES = [
    FIXTURES / "values-010127.json",
    FIXTURES / "values-022582.json",
]


@pytest.fixture(scope="module")
def schema_root():
    return _schema.load()


# ── load / all_paths ──────────────────────────────────────────────────────────

def test_load_strips_api_key(schema_root):
    assert "api" not in schema_root
    assert "system" in schema_root


def test_load_count(schema_root):
    paths = _schema.all_paths(schema_root)
    assert len(paths) == 372, f"Expected 372 schema leaves, got {len(paths)}"


# ── classify ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("type_str,expected", [
    ("Float (range: 0 - 10)", "gauge"),
    ("Integer (range: 0 - 100)", "gauge"),
    ("Boolean", "gauge"),
    ("Enum (allowed values: a,b,c)", "info"),
    ("String", "info"),
    ("TestPatternType (allowed values: a) (range: 1 - 50)", "info"),
    ("ByteArray", "drop"),
    ("Array", "drop"),
])
def test_classify_types(type_str, expected):
    meta = {"Type": type_str, "Access Specifier": "R/W", "Summary": "", "Name": "", "Details": ""}
    assert _schema.classify(meta) == expected


def test_classify_wo_drops_regardless_of_type():
    meta = {"Type": "String", "Access Specifier": "W/O", "Summary": "", "Name": "", "Details": ""}
    assert _schema.classify(meta) == "drop"


# ── match — happy paths ───────────────────────────────────────────────────────

def test_match_literal_path(schema_root):
    parts, labels = _schema.match("system/uptime", schema_root)
    assert parts == ["system", "uptime"]
    assert labels == []


def test_match_placeholder_resolution(schema_root):
    parts, labels = _schema.match(
        "override/test-pattern/frame-store/frames/7/name",
        schema_root,
    )
    assert "{frame-user-number}" in parts
    assert ("frame_user_number", "7") in labels


def test_match_label_name_sanitised(schema_root):
    parts, labels = _schema.match(
        "output/dynacal/cld27rs1.5_v2/red/mode",
        schema_root,
    )
    label_names = [n for n, _ in labels]
    assert "panel_type" in label_names
    assert "panel-type" not in label_names


def test_match_panel_type_dot_in_label_value(schema_root):
    parts, labels = _schema.match(
        "output/dynacal/cld27rs1.5_v2/red/mode",
        schema_root,
    )
    label_values = {n: v for n, v in labels}
    assert label_values["panel_type"] == "cld27rs1.5_v2"
    # The dot appears in the label value, never in the metric name
    name = "tessera_" + "_".join(
        p.replace("-", "_") for p in parts if not (p.startswith("{") and p.endswith("}"))
    )
    assert "." not in name


def test_match_sdi_port_placeholder(schema_root):
    parts, labels = _schema.match(
        "input/ports/sdi/1/meta-data/refresh-rate",
        schema_root,
    )
    assert parts is not None
    assert ("sdi_port_number", "1") in labels


def test_match_nested_placeholders(schema_root):
    parts, labels = _schema.match(
        "groups/items/3/gains/red",
        schema_root,
    )
    assert parts is not None
    assert ("number", "3") in labels


# ── match — miss cases ────────────────────────────────────────────────────────

def test_match_nonexistent_path(schema_root):
    parts, labels = _schema.match("system/does-not-exist", schema_root)
    assert parts is None
    assert labels is None


def test_match_intermediate_node_not_a_leaf(schema_root):
    # system/temperature is an intermediate node, not a leaf
    parts, labels = _schema.match("system/temperature", schema_root)
    assert parts is None


def test_match_empty_path(schema_root):
    parts, labels = _schema.match("", schema_root)
    assert parts is None


# ── schema hit rate against fixtures ─────────────────────────────────────────

@pytest.mark.parametrize("fixture_file", FIXTURE_FILES, ids=lambda p: p.stem)
def test_schema_hit_rate(fixture_file, schema_root):
    """Every flattened path in the fixture must match the schema.

    W/O fields that the firmware erroneously returns are a known exception:
    they match the schema (as W/O) and are correctly classified as 'drop'.
    Unknown paths would indicate schema drift.
    """
    from tessera_exporter import flatten_json

    with open(fixture_file) as f:
        data = json.load(f)

    flat = flatten_json(data.get("api", data))
    misses = []

    for path in flat:
        # Skip identity fields (they're handled separately)
        parts, _ = _schema.match(path, schema_root)
        if parts is None:
            misses.append(path)

    assert misses == [], (
        f"Paths in {fixture_file.name} not found in schema — "
        f"update fixtures or allowlist:\n" + "\n".join(f"  {p}" for p in misses)
    )
