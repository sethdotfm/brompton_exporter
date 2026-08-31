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

A "Tessera Syslog" dashboard is provisioned in Grafana with dropdown filters for serial/processor name/type/version/project — the same identity fields `tessera_info` already exposes for Prometheus — that narrow the log view down to a specific unit's syslog.

**On macOS or Windows**, that identity filtering won't work if `alloy` runs in Docker: Docker Desktop rewrites the source IP of UDP traffic arriving on a published port (confirmed even with its host-networking beta setting enabled), so every log line looks like it came from the same address. If you need the filters to work, run Alloy natively on the host instead — Loki/Grafana/Prometheus/tessera-exporter stay in Docker as-is:

```bash
brew install grafana-alloy   # or the Windows/native build from grafana.com
# don't start the alloy service from docker-compose — just this one:
sudo alloy run --storage.path=/opt/homebrew/var/lib/grafana-alloy/data alloy/config-native.alloy
```

`alloy/config-native.alloy` is the same pipeline as `alloy/config.alloy`, just listening on `:514` directly and pushing to Loki's published port (`127.0.0.1:3100`) instead of compose DNS.

---

## Notes

**IP control must be enabled on each processor.** Go to the Live Control tile in the Tessera UI and enable IP control for the loaded project. If `/probe` returns `tessera_up 0` with `reason="ip_control_disabled"`, this is why.

**Start with scrape_interval at 30s.** Brompton warns that frequent polling may cause "adverse performance" on the Tessera hardware. I have been able to push this much harder, but your milage may vary.

**`/metrics` may look empty.** Processor data is on `/probe`. `/metrics` is exporter self-instrumentation only. Use `/probe?target=192.0.2.10&debug=1` for a human-readable summary of a single scrape.

---

## Not currently available via the API

The Tessera IP Control API (3.5.2) sadly does not currently expose per-panel telemetry. `devices/items/{serial}` provides only `firmware` and `type`. Panel temperature, voltage, and per-panel error detail are visible in the Tessera UI but are not queryable via IP control.

