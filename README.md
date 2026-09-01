# tessera_exporter

A configurable Prometheus exporter for Brompton Tessera LED processors. On large Tessera systems, monitoring performance, health, and configuration can be a challenge, and the built-in alerting is pretty minimal. This exporter scrapes `http://[processor_ip]/api/` and delivers the data to your visualization tool of choice.

I have also included an optional stack for collecting and managing the Tessera syslog output, which can offer some verbose insights to processor and panel health.

Tested against Tessera SX40 processors running firmware **3.5.2**.

---

## Disclosure

Parts of this code have been created or assisted by generative large language models. The structure of this project, as well as all READMEs and docs, have been considered and written by hand.

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

Tessera processors send their operational log over UDP syslog. By default `docker compose up` also brings up `alloy` (receiver + noise filtering), `loki` (log storage, 30d retention), and `grafana` for visualization.

Point your processors’ syslog target at the IP of this server, port `514`.

Severity is normalized into a `level` label (RFC5424's `informational`/`notice`/`warning`/etc. mapped to Grafana's `debug`/`info`/`warn`/`error`/`critical`) so the Logs panel's built-in level coloring works instead of showing everything as `UNK` (unknown).

Retention is 30 days by default, but `debug`/`info`-level lines expire after 24h. See `retention_stream` in `te-syslog-loki/loki-config.yaml` to adjust.

A "Tessera Syslog" dashboard is statically provisioned in Grafana with dropdown filters for serial number, processor name, type, version, and project name. These are the same identity fields `tessera_info` exposes for Prometheus, with an added severity filter derived from the syslog input itself.

**On macOS or Windows**, identity filtering won't work if alloy runs in Docker. This is because Docker Desktop rewrites the source IP of all UDP traffic arriving on a published port, therefore, every log line looks like it came from the same address. Native Linux Docker hosts aren't susceptible to these rewrites.

When running on macOS/Windows, simply run Alloy natively on the host instead. The remaining Loki, Grafana, Prometheus, and tessera-exporter images can remain in Docker.

```bash
# On macOS:
# ~/tessera_exporter/

# Install Alloy with homebrew:
brew install grafana-alloy

# Install the tessera_exporter config (backing up any existing one first)
[ -f /opt/homebrew/etc/grafana-alloy/config.alloy ] && cp /opt/homebrew/etc/grafana-alloy/config.alloy /opt/homebrew/etc/grafana-alloy/config.alloy.old
cp te-syslog-alloy/config-native.alloy /opt/homebrew/etc/grafana-alloy/config.alloy

# To bring up the service
sudo brew services start grafana-alloy

# To bring down the service:
sudo brew services stop grafana-alloy
```

`te-syslog-alloy/config-native.alloy` is the same pipeline as `te-syslog-alloy/config.alloy`, just listening on `:514` directly and pushing to Loki's published port (`127.0.0.1:3101`) instead of compose DNS.

---

## Notes

**IP control must be enabled on each processor.** Go to the Live Control tile in the Tessera UI and enable IP control for the loaded project. If `/probe` returns `tessera_up 0` with `reason="ip_control_disabled"`, this is why.

**Start with scrape_interval at 30s.** Brompton warns that frequent polling may cause "adverse performance" on the Tessera hardware. I have been able to push this much harder, but your mileage may vary.

`/metrics` **may look empty.** Processor data is on `/probe`. `/metrics` is exporter self-instrumentation only. Use `/probe?target=192.0.2.10&debug=1` for a human-readable summary of a single scrape.

The Tessera IP Control API (3.5.2) sadly does not currently expose per-panel telemetry. `devices/items/{serial}` provides only `firmware` and `type`. Panel temperature, voltage, and per-panel error detail are visible in the Tessera UI but are not queryable via IP control.