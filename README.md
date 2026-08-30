# brompton_exporter
__A configurable Prometheus exporter for Brompton Tessera LED processors.__ <br> On large Tessera systems, monitoring performance, health, and configuration can be a challenge, and the built in alerting systems are pretty minimal. You can use this exporter to scrape the data from the http://[processor_ip]/api/ URL and deliver it to your favorite visualization tool.

## Not available via the API
The Tessera IP Control API (3.5.2) sadly does not currently expose per-panel telemetry.
`devices/items/{serial}` provides only `firmware` and `type`. Panel
temperature, voltage, and per-panel error detail are visible in the
Tessera UI but are not queryable via IP control.