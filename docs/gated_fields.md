# Gated Fields

Some Tessera fields are always exported but semantically meaningless unless a
sibling "gate" field has the right value. Querying the gated field directly
without checking the gate produces misleading metrics.

The exporter always exports **both** the gate and the gated field. Filtering
must happen in PromQL at query time.

---

## Why export both?

If the exporter suppressed gated fields, operators would lose observability
of the firmware state. Consider: a gated field returning an unexpected value
when it should be inactive reveals a firmware bug. Suppressing it hides that.

---

## 1. Dynacal white colour temperature

| Role | Path |
|------|------|
| Gate | `*/dynacal/white/gamut` |
| Gated | `*/dynacal/white/colour-temperature` |

When `gamut` is set to a standard colour space (e.g., `d65`, `rec-709`), the
`colour-temperature` field is a leftover value that doesn't affect output.
Only when `gamut` is `colour-temperature` does the numeric field control
anything.

**Example observed on hardware:**
```
white.gamut = "d65"
white.colour-temperature = 5600   ← inactive; output is D65 (6500K)
```

**PromQL:**
```promql
tessera_input_ports_sdi_dynacal_white_colour_temperature
  and on(instance, sdi_port_number)
  (tessera_input_ports_sdi_dynacal_white_gamut_info{value="colour-temperature"} == 1)
```

---

## 2. ShutterSync dark time

| Role | Path |
|------|------|
| Gate | `output/network/shuttersync/dark-time-mode` |
| Gated (ms) | `output/network/shuttersync/dark-time` |
| Gated (%) | `output/network/shuttersync/dark-time-percentage` |

When `dark-time-mode` is `"time"`, use `dark-time` (milliseconds).
When `dark-time-mode` is `"percentage"`, use `dark-time-percentage`.

**PromQL for time-based dark time:**
```promql
tessera_output_network_shuttersync_dark_time_milliseconds
  and on(instance)
  (tessera_output_network_shuttersync_dark_time_mode_info{value="time"} == 1)
```

---

## 3. ShutterSync mode — speed-settings vs angle-settings

| Role | Path |
|------|------|
| Gate | `output/network/shuttersync/mode` |
| Gated | `output/network/shuttersync/speed-settings/*` |
| Gated | `output/network/shuttersync/angle-settings/*` |

`mode` values: `disabled`, `shutter-speed`, `shutter-angle`.

- `speed-settings/*` is active only when `mode == "shutter-speed"`
- `angle-settings/*` is active only when `mode == "shutter-angle"`

**PromQL:**
```promql
tessera_output_network_shuttersync_angle_settings_shutter_angle_degrees
  and on(instance)
  (tessera_output_network_shuttersync_mode_info{value="shutter-angle"} == 1)
```

---

## 4. Output brightness limit

| Role | Path |
|------|------|
| Gate | `output/global-colour/brightness-limit/enabled` |
| Gated | `output/global-colour/brightness-limit/value` |

`value` is only active when `enabled == true`.

**PromQL:**
```promql
tessera_output_global_colour_brightness_limit_value
  and on(instance)
  (tessera_output_global_colour_brightness_limit_enabled == 1)
```

---

## 5. Custom frame rate for angle-based ShutterSync

| Role | Path |
|------|------|
| Gate | `output/network/shuttersync/angle-settings/use-custom-frame-rate` |
| Gated | `output/network/shuttersync/angle-settings/custom-frame-rate` |

`custom-frame-rate` is active only when `use-custom-frame-rate == true`.

Note: `custom-frame-rate` can be `null` when disabled (observed in firmware 3.5.2);
the exporter drops null values and they will not appear in Prometheus.

---

## 6. Dynacal per-channel mode

| Role | Path |
|------|------|
| Gate | `output/dynacal/{panel-type}/mode` |
| Gated | `output/dynacal/{panel-type}/{red,green,blue}/mode` |

Per-channel `mode` is meaningful only when the panel-level `mode == "custom"`.

**Known firmware bug (3.5.2):** Both processors tested return `"???"` for
per-channel mode regardless of the panel-level setting. This is outside the
documented allowed values (`achievable`, `custom`). The exporter exports the
value as-is so this misbehaviour is visible in Prometheus.

**PromQL:**
```promql
tessera_output_dynacal_red_mode_info
  and on(instance, panel_type)
  (tessera_output_dynacal_mode_info{value="custom"} == 1)
```

---

## Known firmware bugs affecting gated fields

See the README for the full vendor bug list. Relevant to gated fields:

1. `output/dynacal/{panel-type}/{r,g,b}/mode` returns `"???"` (not in allowed values)
2. `override/test-pattern/frame-store/frames/{n}/colour-space` is marked W/O
   in the schema but returns a value — the exporter drops it correctly per schema
