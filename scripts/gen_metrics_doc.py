#!/usr/bin/env python3
"""Generate docs/METRICS.md from the schema and tessera.yml config.

Run this after a firmware upgrade to regenerate the metrics reference.
This script is not run in CI — it is a one-shot documentation generator.

Usage:
    python scripts/gen_metrics_doc.py > docs/METRICS.md
"""

from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

# Allow running from repo root or scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
import schema as _schema
from tessera_exporter import make_name, lookup_suffix

REPO = Path(__file__).parent.parent


def main() -> None:
    schema_root = _schema.load()
    with open(REPO / "tessera.yml") as f:
        config = yaml.safe_load(f)

    suffix_config = config.get("suffix") or {}
    sentinel_config = config.get("sentinels") or {}
    collectors = config.get("collectors") or {}

    all_paths = _schema.all_paths(schema_root)

    rows: list[dict] = []
    for schema_path in sorted(all_paths):
        schema_parts = schema_path.split("/")
        meta = _schema.leaf(schema_root, schema_parts)
        kind = _schema.classify(meta)

        if kind == "drop":
            continue

        # Determine collector
        top = schema_parts[0]
        collector_default = collectors.get(top, True)

        # Determine metric name
        value_path = schema_path  # use schema path (with placeholders) for suffix lookup
        suffix, scale = lookup_suffix(schema_path, suffix_config)
        if kind == "info":
            full_suffix = (suffix + "_info") if suffix else "_info"
        else:
            full_suffix = suffix
        metric_name = make_name(schema_parts, full_suffix)

        # Labels from placeholders
        labels = [p[1:-1].replace("-", "_") for p in schema_parts
                  if p.startswith("{") and p.endswith("}")]

        if kind == "info":
            labels.append("value")

        # Sentinel?
        sentinels_note = ""
        for pat, vals in sentinel_config.items():
            if fnmatch.fnmatch(schema_path, pat):
                sentinels_note = f"Sentinel: {vals} → NaN"

        rows.append({
            "name": metric_name,
            "kind": kind,
            "help": meta.get("Summary", ""),
            "access": meta.get("Access Specifier", ""),
            "type_str": meta.get("Type", ""),
            "labels": ", ".join(labels) if labels else "—",
            "scale": f"×{scale}" if scale != 1.0 else "—",
            "collector": top,
            "collector_default": "on" if collector_default else "off",
            "sentinels": sentinels_note,
        })

    # Print markdown table
    print("# Tessera Exporter Metrics Reference")
    print()
    print("Generated from `schema/schema_tessera_3.5.2.json` and `tessera.yml`.")
    print("Re-run `python scripts/gen_metrics_doc.py` after a firmware upgrade.")
    print()
    print("All metrics are `gauge` type. Info metrics have `value` in labels and are always 1.")
    print()

    headers = ["Metric", "Kind", "Labels", "Scale", "Collector (default)", "Notes"]
    col_w = [max(len(h), max((len(r[k]) for r in rows), default=0))
             for h, k in zip(headers, ["name", "kind", "labels", "scale",
                                        "collector_default", "sentinels"])]

    def row_str(cells):
        return "| " + " | ".join(c.ljust(w) for c, w in zip(cells, col_w)) + " |"

    print(row_str(headers))
    print("|" + "|".join("-" * (w + 2) for w in col_w) + "|")

    for r in rows:
        cells = [
            f"`{r['name']}`",
            r["kind"],
            r["labels"],
            r["scale"],
            f"{r['collector']} ({r['collector_default']})",
            r["sentinels"],
        ]
        print(row_str(cells))

    print()
    print(f"Total exported metrics: **{len(rows)}**")


if __name__ == "__main__":
    main()
