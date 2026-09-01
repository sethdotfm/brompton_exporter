"""Tests for target parsing, failure modes, and edge cases."""

from __future__ import annotations

import pytest

from tessera_exporter import parse_target


# ── Target parsing ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("target,expected_host,expected_port", [
    ("192.0.2.50", "192.0.2.50", 80),
    ("192.0.2.50:8080", "192.0.2.50", 8080),
    ("http://192.0.2.50", "192.0.2.50", 80),
    ("http://192.0.2.50:9090", "192.0.2.50", 9090),
    ("http://192.0.2.50/", "192.0.2.50", 80),
    ("tessera.local", "tessera.local", 80),
    ("tessera.local:9000", "tessera.local", 9000),
    ("[::1]", "::1", 80),
    ("[::1]:8080", "::1", 8080),
    ("[2001:db8::1]:9090", "2001:db8::1", 9090),
])
def test_parse_target_valid(target, expected_host, expected_port):
    host, port = parse_target(target)
    assert host == expected_host
    assert port == expected_port


@pytest.mark.parametrize("bad_target", [
    "",
    "http://",
    "[::1",       # unclosed bracket
    "host:abc",   # non-integer port
    "host:99999", # out-of-range port
    "host:0",     # out-of-range port
])
def test_parse_target_malformed_raises(bad_target):
    with pytest.raises(ValueError):
        parse_target(bad_target)


# ── IP control disabled detection ────────────────────────────────────────────

def test_ip_control_disabled_detected():
    """A body containing 'response-code' must trigger ip_control_disabled failure."""
    import json
    from unittest.mock import MagicMock, patch
    import io

    error_body = json.dumps({"response-code": 403, "description": "IP Control disabled"})

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = error_body.encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    import schema as _schema
    schema_root = _schema.load()
    config = {"collectors": {}, "suffix": {}, "sentinels": {}}

    with patch("urllib.request.urlopen", return_value=mock_response):
        from tessera_exporter import probe
        text, ctype = probe("192.0.2.50", 80, schema_root, config)

    assert "tessera_up 0" in text
    assert 'reason="ip_control_disabled"' in text


def test_connection_refused_returns_up_0():
    """A connection refused error must return tessera_up 0."""
    import schema as _schema
    from unittest.mock import patch
    import urllib.error

    schema_root = _schema.load()
    config = {"collectors": {}, "suffix": {}, "sentinels": {}}

    with patch("urllib.request.urlopen", side_effect=ConnectionRefusedError()):
        from tessera_exporter import probe
        text, _ = probe("192.0.2.50", 80, schema_root, config)

    assert "tessera_up 0" in text
    assert 'reason="connection_refused"' in text


def test_urlerror_wrapped_failures_classified():
    """urllib wraps socket errors in URLError — reasons must still classify."""
    import socket
    import urllib.error
    from unittest.mock import patch

    import schema as _schema
    from tessera_exporter import probe

    schema_root = _schema.load()
    config = {"collectors": {}, "suffix": {}, "sentinels": {}}

    cases = [
        (socket.gaierror(8, "nodename nor servname provided"), "dns"),
        (ConnectionRefusedError(61, "Connection refused"), "connection_refused"),
        (TimeoutError("timed out"), "timeout"),
        ("something opaque", "connection_error"),
    ]
    for cause, expected in cases:
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError(cause)):
            text, _ = probe("192.0.2.50", 80, schema_root, config)
        assert "tessera_up 0" in text
        assert f'reason="{expected}"' in text, f"cause={cause!r}"


def test_bad_json_returns_up_0():
    """Malformed JSON in the response body must return tessera_up 0."""
    from unittest.mock import MagicMock, patch
    import schema as _schema

    schema_root = _schema.load()
    config = {"collectors": {}, "suffix": {}, "sentinels": {}}

    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b"not json at all {"
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response):
        from tessera_exporter import probe
        text, _ = probe("192.0.2.50", 80, schema_root, config)

    assert "tessera_up 0" in text
    assert 'reason="bad_json"' in text


# ── format_value edge cases ───────────────────────────────────────────────────

def test_format_value_nan():
    from tessera_exporter import format_value
    import math
    assert format_value(float("nan")) == "NaN"


def test_format_value_none():
    from tessera_exporter import format_value
    assert format_value(None) == "NaN"


def test_format_value_true():
    from tessera_exporter import format_value
    assert format_value(True) == "1"


def test_format_value_false():
    from tessera_exporter import format_value
    assert format_value(False) == "0"


def test_format_value_int():
    from tessera_exporter import format_value
    assert format_value(42) == "42"


def test_format_value_float():
    from tessera_exporter import format_value
    assert format_value(1.5) == "1.5"


# ── Label escaping ────────────────────────────────────────────────────────────

def test_label_value_with_quotes_escaped():
    from tessera_exporter import format_labels
    result = format_labels({"v": 'he said "hello"'})
    assert '\\"' in result


def test_label_value_with_backslash_escaped():
    from tessera_exporter import format_labels
    result = format_labels({"v": "path\\to\\file"})
    assert "\\\\" in result


# ── make_name ────────────────────────────────────────────────────────────────

def test_make_name_drops_placeholders():
    from tessera_exporter import make_name
    parts = ["groups", "items", "{number}", "brightness"]
    name = make_name(parts)
    assert "{" not in name
    assert "number" not in name  # placeholder value goes to labels, not name
    assert name == "tessera_groups_items_brightness"


def test_make_name_hyphens_replaced():
    from tessera_exporter import make_name
    parts = ["system", "processor-name"]
    name = make_name(parts)
    assert "-" not in name
    assert name == "tessera_system_processor_name"


def test_make_name_with_suffix():
    from tessera_exporter import make_name
    parts = ["system", "temperature", "cpu"]
    name = make_name(parts, "_celsius")
    assert name == "tessera_system_temperature_cpu_celsius"


# ── Collector filtering ───────────────────────────────────────────────────────

def test_collector_off_drops_paths():
    from tessera_exporter import is_enabled
    config = {"collectors": {"devices": False}, "include": [], "exclude": []}
    assert not is_enabled("devices/items/ABC123/firmware", config)
    assert is_enabled("system/uptime", config)


def test_include_overrides_collector_off():
    from tessera_exporter import is_enabled
    config = {
        "collectors": {"devices": False},
        "include": ["devices/statistics/*"],
        "exclude": [],
    }
    assert is_enabled("devices/statistics/associated-count", config)
    assert not is_enabled("devices/items/ABC123/firmware", config)


def test_exclude_overrides_collector_on():
    from tessera_exporter import is_enabled
    config = {
        "collectors": {"system": True},
        "include": [],
        "exclude": ["system/temperature/*"],
    }
    assert not is_enabled("system/temperature/cpu", config)
    assert is_enabled("system/uptime", config)


# ── Sentinel lookup ───────────────────────────────────────────────────────────

def test_sentinel_matches_glob():
    from tessera_exporter import is_sentinel
    sentinels = {"input/ports/*/meta-data/refresh-rate": [-1]}
    assert is_sentinel("input/ports/sdi/1/meta-data/refresh-rate", -1, sentinels)
    assert not is_sentinel("input/ports/sdi/1/meta-data/refresh-rate", 60.0, sentinels)


def test_sentinel_resolution_height_both_values():
    from tessera_exporter import is_sentinel
    sentinels = {"input/ports/*/meta-data/resolution/height": [-1, 0]}
    assert is_sentinel("input/ports/sdi/1/meta-data/resolution/height", -1, sentinels)
    assert is_sentinel("input/ports/sdi/1/meta-data/resolution/height", 0, sentinels)
    assert not is_sentinel("input/ports/sdi/1/meta-data/resolution/height", 1080, sentinels)
