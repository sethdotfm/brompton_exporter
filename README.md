# brompton_exporter

**A Prometheus exporter for Brompton Tessera LED processors.**

Multi-target exporter (blackbox_exporter / snmp_exporter pattern). One running
instance can monitor many processors; targets are passed as a URL parameter at
scrape time.

Tested against Tessera SX40 processors running firmware **3.5.2**.

---

## Quick start

```bash
pip install pyyaml
python tessera_exporter.py --web.listen-address :19800
```

Or with Docker:

```bash
docker compose up
```

Then add your processors to `targets/tessera.yml` and point Prometheus at the
provided `prometheus.yml`.

---

## Prerequisites

### IP control must be enabled on each processor

Go to the **Live Control** tile in the Tessera UI and enable IP control for the
loaded project. A processor can be powered, pingable, and fully functional, yet
refuse the API if this is off.

If /probe returns `tessera_up 0` with `reason="ip_control_disabled"`, this is
why. It is the number one support question.

### Polling rate

Brompton documentation warns that polling large amounts of data multiple times
per second **may cause adverse performance on live video hardware**. The default
`scrape_interval` is 30s. Do not reduce it without testing on your specific
hardware.

---

## Architecture

```
Prometheus → /probe?target=192.0.2.50 → tessera_exporter → GET /api/ → processor
```

- **`/probe?target=<host>[:<port>]`** — scrape one processor; returns metrics
- **`/probe?target=<host>&debug=1`** — human-readable scrape report (not metrics)
- **`/metrics`** — exporter self-instrumentation only (build info, not processor data)
- **`/`** — landing page

If you `curl /metrics` and see nothing useful, that is expected. Processor data
is on `/probe`.

---

## Configuration (`tessera.yml`)

### Collectors

Nine top-level booleans map to the API's subtrees:

| Collector | Default | Contains |
|-----------|---------|---------|
| `system` | on | Temperatures, fans, identity |
| `input` | on | Signal, resolution, refresh rate, proc-amp |
| `output` | on | Brightness, gamma, genlock, shuttersync, failover |
| `override` | on | Blackout, freeze, test pattern |
| `presets` | on | Active preset |
| `project` | on | Project name (goes into `tessera_info`) |
| `processing` | **off** | 3D LUT, curves, colour correct |
| `groups` | **off** | Per-group overrides |
| `devices` | **off** | Per-panel firmware/type (unbounded cardinality) |

Disabling a collector does **not** reduce load on the processor — the full API
response is always fetched. It only reduces what is stored in Prometheus.

To get panel counts without the unbounded per-panel series:

```yaml
collectors:
  devices: false

include:
  - "devices/statistics/*"
```

### Suffix map

Units are not in the Tessera API schema. The `suffix:` map in `tessera.yml`
maps path globs to unit suffixes and scale factors. It is pinned to firmware
3.5.2 — review it after upgrading firmware.

### Gated fields

See [`docs/gated_fields.md`](docs/gated_fields.md) for fields whose values are
semantically meaningless unless a sibling field is in a specific state. The
exporter always exports both; filtering happens in PromQL.

---

## Metrics

All metrics are `gauge` type. Run `scripts/gen_metrics_doc.py` to regenerate
`docs/METRICS.md` from the current schema and config.

### Identity

```
tessera_info{serial="010127", processor_name="Studio A", processor_type="sx40",
             software_version="3.5.2.15", project="ShowConfig"} 1
```

Identity labels (`serial`, `processor_name`, etc.) are on **only** this metric.
Join them at query time:

```promql
tessera_system_temperature_cpu_celsius * on(instance) group_left(serial)
  tessera_info
```

### Uptime

```
tessera_system_uptime_info{value="50d 1215h 71607m 4294997s"} 1
```

Uptime is exported as an info metric only. The raw string from the processor is
preserved. The numeric fields in the uptime string disagree with each other due
to a 32-bit millisecond overflow in firmware 3.5.2 — see *Known firmware bugs*
below.

Reboot detection: use Prometheus's own `up` metric transitioning 0 → 1.

### No-signal sentinels → NaN

When no input signal is present, the firmware returns sentinel values
(`-1` or `0` depending on unit) for `refresh-rate`, `resolution/height`, and
`resolution/width`. These are exported as `NaN` (not as the literal numbers),
so they don't distort aggregations. Use `isnan()` in PromQL to detect
no-signal state:

```promql
tessera_input_ports_sdi_meta_data_resolution_height_hertz == 0 or
isnan(tessera_input_ports_sdi_meta_data_resolution_height)
```

### Panel temperature

**Panel temperature is not available via the Tessera IP Control API (3.5.2).**

`devices/items/{serial}` exposes only `firmware` and `type`. Panel temperature,
per-panel voltage, and per-panel error detail are visible in the Tessera UI but
are not queryable via IP control.

`system/temperature/*` gives processor-internal temperatures only (ambient,
CPU, DSP, GPU, FPGA, PSU, front, rear, six Ethernet PHY sensors).

---

## Not available via the API

- Per-panel temperature, voltage, or error detail
- Per-panel calibration data in numeric form (only a blob via `devices/items`)

These are visible in the Tessera UI but not exposed through IP Control 3.5.2.

---

## Known firmware bugs (3.5.2)

These are documented here and reported upstream. The exporter handles each
correctly without silent workarounds.

1. **`system/uptime` — 32-bit millisecond overflow.** The four fields (days,
   hours, minutes, seconds) are derived from an overflow-prone counter and
   disagree with each other by days on long-running hardware. The seconds
   field freezes. The exporter exports the raw string only and never attempts
   numeric conversion.

2. **`output/dynacal/{panel-type}/{red,green,blue}/mode` returns `"???"`.**
   The documented allowed values are `achievable` and `custom`. Both live
   processors tested return `"???"`. The exporter exports this as-is so the
   misbehaviour is visible in Prometheus.

3. **`override/test-pattern/frame-store/frames/{n}/colour-space` is marked W/O**
   in the API schema but returns a value. The exporter drops it (trusting the
   schema for filtering decisions).

4. **Inconsistent no-signal sentinels.** Two processors on identical firmware
   return different values for `resolution/height` and `resolution/width` when
   no signal is present (`-1` on one unit, `0` on the other). The exporter
   treats both as sentinel values for those specific paths only.

---

## Development

```bash
# Install dev dependencies
pip install pyyaml pytest

# Run tests
pytest tests/ -v

# Validate metric format (requires promtool)
python tessera_exporter.py --web.listen-address :19800 &
curl -s http://localhost:19800/metrics | promtool check metrics

# Generate metrics reference doc
python scripts/gen_metrics_doc.py > docs/METRICS.md
```

---

## License

Apache 2.0
