# tessera_exporter

A configurable Prometheus exporter for Brompton Tessera LED processors. On large Tessera systems, monitoring performance, health, and configuration can be a challenge, and the built-in alerting is pretty minimal. This exporter scrapes `http://[processor_ip]/api/` and delivers the data to your visualization tool of choice.

Tested against Tessera SX40 processors running firmware **3.5.2**.

---

## Disclosure

Parts of this code have been created or assisted by generative large language models. The structure of this project, as well as all READMEs and docs, have been written entirely by hand.

---

## Quick start

Edit `targets/tessera.yml` with your processor IPs and run:

```bash
docker compose up
```

Or pull the image directly:

```bash
docker pull ghcr.io/sethdotfm/tessera_exporter:latest
```

---

## Adding to an existing Prometheus installation

Add your processors to `targets/tessera.yml`. Prometheus picks up changes to this file automatically with no reload needed.

```yaml
- targets: ["192.2.0.50"]
  labels:
    site: "STUDIO-1"
    location: "MAIN"
```

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: tessera
    scrape_interval: 30s
    metrics_path: /probe
    file_sd_configs:
      - files: [/etc/prometheus/tessera_targets/*.yml]
        refresh_interval: 30s
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
        regex: "([^:]+)(:\\d+)?"
        replacement: "$1"
      - target_label: __address__
        replacement: "tessera-exporter:19800"
  - job_name: tessera_exporter
    static_configs:
      - targets: ["tessera-exporter:19800"]
```

Mount the targets directory into your Prometheus container:

```yaml
volumes:
  - ./targets:/etc/prometheus/tessera_targets:ro
```

---

## Syslog (optional)

Tessera processors can send their operational log over UDP syslog. `docker compose up` also brings up `alloy` (receiver + noise filtering), `loki` (log storage, 30d retention), and `grafana` (view it in Explore) to catch it.

Point your processor's syslog target at `<this_host>:514`. To silence routine/noisy messages before they're stored, add a `stage.drop` block in `alloy/config.alloy`.

Severity is normalized into a `level` label (RFC5424's `informational`/`notice`/`warning`/etc. mapped to Grafana's `debug`/`info`/`warn`/`error`/`critical`) so the Logs panel's built-in level coloring works instead of showing everything as `UNK`.

**Retention:** 30 days by default, but `debug`/`info`-level lines (the vast majority of volume) expire after 24h — see `retention_stream` in `loki/loki-config.yaml` if you want a different split. Loki has no built-in hard byte-size cap ("keep at most 1GB"); if that's a hard requirement, enforce it with a filesystem quota on the `loki-data` volume rather than Loki config — 24h of debug logs from a handful of processors measured well under 1GB in testing here, but that's not a guarantee.

A "Tessera Syslog" dashboard is provisioned in Grafana with dropdown filters for serial/processor name/type/version/project (the same identity fields `tessera_info` already exposes for Prometheus) plus severity, all narrowing down to a specific unit's syslog. Leaving a filter at "All" matches everything for that field.

**On macOS or Windows**, that identity filtering won't work if `alloy` runs in Docker: Docker Desktop rewrites the source IP of UDP traffic arriving on a published port ([known, years-open Docker issue](https://github.com/moby/libnetwork/issues/1994) — confirmed here even with Docker Desktop's host-networking beta setting enabled), so every log line looks like it came from the same address. Windows/WSL2 with mirrored networking mode may not have this problem, but that's unverified — test before relying on it. Native Linux Docker hosts aren't affected at all.

If you need the filters to work on macOS/Windows, run Alloy natively on the host instead — Loki/Grafana/Prometheus/tessera-exporter stay in Docker as-is:

```bash
brew install grafana-alloy   # or the Windows/native build from grafana.com
cp alloy/config-native.alloy /opt/homebrew/etc/grafana-alloy/config.alloy
# don't start the alloy service from docker-compose — just this one, as a
# launchd service so it survives crashes and reboots (KeepAlive: true):
sudo brew services start grafana-alloy
```

Logs land at `/opt/homebrew/var/log/grafana-alloy.log`. `sudo brew services stop grafana-alloy` to stop it, or `sudo brew services list` to check status. (A plain foreground `alloy run ...` in a `tmux`/`screen` session also works if you don't want it installed as a persistent service, but it won't auto-restart if Alloy crashes or the Mac reboots — `brew services` does.)

`alloy/config-native.alloy` is the same pipeline as `alloy/config.alloy`, just listening on `:514` directly and pushing to Loki's published port (`127.0.0.1:3100`) instead of compose DNS.

---

## Notes

**IP control must be enabled on each processor.** Go to the Live Control tile in the Tessera UI and enable IP control for the loaded project. If `/probe` returns `tessera_up 0` with `reason="ip_control_disabled"`, this is why.

**Start with scrape_interval at 30s.** Brompton warns that frequent polling may cause "adverse performance" on the Tessera hardware. I have been able to push this much harder, but your milage may vary.

**`/metrics` may look empty.** Processor data is on `/probe`. `/metrics` is exporter self-instrumentation only. Use `/probe?target=192.0.2.10&debug=1` for a human-readable summary of a single scrape.

---

## Not currently available via the API

The Tessera IP Control API (3.5.2) sadly does not currently expose per-panel telemetry. `devices/items/{serial}` provides only `firmware` and `type`. Panel temperature, voltage, and per-panel error detail are visible in the Tessera UI but are not queryable via IP control.

