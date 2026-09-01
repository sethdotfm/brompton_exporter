"""Tests for tessera_exporter.build_metrics — metric output correctness."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
import yaml

import schema as _schema
from tessera_exporter import build_metrics, flatten_json

FIXTURES = Path(__file__).parent / "fixtures"
CONFIG_FILE = Path(__file__).parent.parent / "tessera.yml"


@pytest.fixture(scope="module")
def schema_root():
    return _schema.load()


@pytest.fixture(scope="module")
def config():
    with open(CONFIG_FILE) as f:
        cfg = yaml.safe_load(f)
    # Enable all collectors so tests see every metric
    for key in cfg.get("collectors", {}):
        cfg["collectors"][key] = True
    return cfg


def _load_fixture(name: str) -> dict:
    with open(FIXTURES / name) as f:
        return json.load(f)


def _metrics(fixture_name: str, schema_root, config) -> tuple[str, dict, list]:
    data = _load_fixture(fixture_name)
    return build_metrics(data, schema_root, config)


# ── uptime ────────────────────────────────────────────────────────────────────

def test_uptime_is_info_not_gauge(schema_root, config):
    text, _, _ = _metrics("values-022582.json", schema_root, config)
    # Must not appear as a seconds gauge
    assert "tessera_system_uptime_seconds" not in text
    assert "uptime_info" in text
    assert "50d 1215h 71607m 4294997s" in text


def test_uptime_value_preserved(schema_root, config):
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    assert "12d 293h 17608m 1058014s" in text


# ── null values ───────────────────────────────────────────────────────────────

def test_null_does_not_raise(schema_root, config):
    """shuttersync/angle-settings/custom-frame-rate is null in fixture 022582."""
    data = _load_fixture("values-022582.json")
    # Must not raise
    text, stats, _ = build_metrics(data, schema_root, config)
    assert stats["dropped_null"] > 0


# ── array dropped ─────────────────────────────────────────────────────────────

def test_array_dropped(schema_root, config):
    """processing/curves/*/points is Array type — must not appear in output."""
    text, stats, _ = _metrics("values-010127.json", schema_root, config)
    assert "curves_points" not in text
    assert stats["dropped_wo_type"] > 0


# ── enum outside allowed values ───────────────────────────────────────────────

def test_enum_outside_allowed_values_does_not_crash(schema_root, config):
    """output/dynacal/{panel-type}/red/mode returns '???' — must be exported."""
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    assert '???' in text or "value=" in text  # exported as info label value


def test_enum_outside_allowed_values_visible(schema_root, config):
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    # '???' should appear as a label value
    assert 'value="???"' in text


# ── string preservation ───────────────────────────────────────────────────────

def test_leading_zero_serial_preserved(schema_root, config):
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    assert 'serial="010127"' in text


def test_preset_name_string_preserved(schema_root, config):
    """Preset name '80' must stay as string '80', not be coerced to integer."""
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    # The preset name "80" should appear as a string label value
    assert 'value="80"' in text


# ── panel type with dot in name ───────────────────────────────────────────────

def test_panel_type_dot_in_label_not_name(schema_root, config):
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    lines = text.splitlines()
    metric_lines = [l for l in lines if l.startswith("tessera_") and "cld27rs1.5_v2" in l]
    assert metric_lines, "Panel-type label should appear in output"
    for line in metric_lines:
        name = line.split("{")[0]
        assert "." not in name, f"Dot found in metric name: {name}"
        assert "cld27rs1.5_v2" in line  # should be in label value


# ── series collision ──────────────────────────────────────────────────────────

def test_no_series_collision(schema_root, config):
    """No two API paths should produce the same (metric_name, labels) pair."""
    for fname in ("values-010127.json", "values-022582.json"):
        _, stats, _ = _metrics(fname, schema_root, config)
        assert stats["collisions"] == 0, (
            f"{fname}: {stats['collisions']} series collision(s) detected"
        )


# ── percentage / ratio conversion ────────────────────────────────────────────

def test_percentage_field_converted_to_ratio(schema_root, config):
    """proc-amp contrast=150 → 1.5 ratio (150 * 0.01)."""
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    # contrast is 150 in the fixture → should become 1.5 after *0.01
    assert "_ratio" in text
    # The proc-amp contrast value 150 * 0.01 = 1.5
    assert "1.5" in text


# ── sentinel values → NaN ────────────────────────────────────────────────────

def test_sentinel_produces_nan_010127(schema_root, config):
    """resolution height/width = 0 in 010127 → NaN (not 0)."""
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    # Filter to data lines only (exclude # HELP / # TYPE lines)
    lines = [l for l in text.splitlines()
             if ("resolution_height" in l or "resolution_width" in l) and not l.startswith("#")]
    assert lines, "resolution data lines should be present"
    for line in lines:
        assert "NaN" in line, f"Expected NaN for sentinel 0, got: {line}"


def test_sentinel_produces_nan_022582(schema_root, config):
    """resolution height/width = -1 in 022582 → NaN."""
    text, _, _ = _metrics("values-022582.json", schema_root, config)
    lines = [l for l in text.splitlines()
             if ("resolution_height" in l or "resolution_width" in l) and not l.startswith("#")]
    assert lines, "resolution data lines should be present"
    for line in lines:
        assert "NaN" in line, f"Expected NaN for sentinel -1, got: {line}"


def test_refresh_rate_sentinel_nan(schema_root, config):
    """refresh-rate = -1 → NaN."""
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    lines = [l for l in text.splitlines() if "refresh_rate" in l and not l.startswith("#")]
    assert any("NaN" in l for l in lines), "refresh-rate -1 should produce NaN"


# ── tessera_info identity metric ─────────────────────────────────────────────

def test_tessera_info_present(schema_root, config):
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    assert "tessera_info" in text


def test_tessera_info_has_all_labels(schema_root, config):
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    info_line = next(
        l for l in text.splitlines() if l.startswith("tessera_info{")
    )
    assert "serial=" in info_line
    assert "processor_name=" in info_line
    assert "processor_type=" in info_line
    assert "software_version=" in info_line
    assert "project=" in info_line


# ── unmatched paths exported ──────────────────────────────────────────────────

def test_unmatched_path_exported(schema_root, config):
    """A path absent from the schema must appear in output, not be silently dropped."""
    data = {
        "api": {
            "system": {
                "serial-number": "999999",
                "future-firmware-field": "some-value",
            }
        }
    }
    text, stats, unmatched = build_metrics(data, schema_root, config)
    assert stats["unmatched"] > 0
    assert "tessera_unknown_path_info" in text
    assert "future-firmware-field" in text


# ── W/O fields dropped ───────────────────────────────────────────────────────

def test_wo_fields_dropped(schema_root, config):
    """system/actions/reboot is W/O — must not appear in output."""
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    assert "system_actions_reboot" not in text


# ── ByteArray dropped ─────────────────────────────────────────────────────────

def test_bytearray_dropped(schema_root, config):
    """processing/3d-lut/data is ByteArray — must not appear in output."""
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    assert "3d_lut_data" not in text


# ── boolean as gauge ─────────────────────────────────────────────────────────

def test_boolean_emitted_as_0_or_1(schema_root, config):
    text, _, _ = _metrics("values-010127.json", schema_root, config)
    # override/blackout/enabled is false → should be 0
    lines = [l for l in text.splitlines() if "blackout_enabled" in l and not l.startswith("#")]
    assert lines
    for line in lines:
        assert line.endswith(" 0") or line.endswith(" 1"), f"Bad boolean: {line}"
