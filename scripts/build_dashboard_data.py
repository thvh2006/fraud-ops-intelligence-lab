"""Build the small, browser-ready payload used by the static portfolio dashboard."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def rows(name: str) -> list[dict[str, object]]:
    with (REPORTS / name).open(newline="", encoding="utf-8") as handle:
        records = list(csv.DictReader(handle))
    for record in records:
        for key, value in record.items():
            if value is None:
                continue
            try:
                record[key] = int(value) if value.isdigit() else float(value)
            except ValueError:
                pass
    return records


def main() -> None:
    payload = {
        "profile": json.loads((REPORTS / "data_profile_summary.json").read_text()),
        "partitions": rows("temporal_partitions.csv"),
        "baseline_models": rows("baseline_model_metrics.csv"),
        "challenger_models": rows("challenger_model_metrics.csv"),
        "ablation": rows("feature_family_ablation.csv"),
        "uncertainty": rows("model_comparison_uncertainty.csv"),
        "policy": rows("policy_sensitivity.csv"),
        "actions": rows("policy_action_summary.csv"),
        "monitoring": rows("weekly_monitoring.csv"),
        "delayed_labels": rows("delayed_label_summary.csv"),
    }
    destination = ROOT / "dashboard" / "data.json"
    destination.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {destination} ({destination.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
