import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_payload_covers_every_policy_control_combination() -> None:
    payload = json.loads((ROOT / "dashboard" / "data.json").read_text())
    oot = [row for row in payload["policy"] if row["partition"] == "oot"]
    combinations = {(row["scenario"], row["review_capacity"]) for row in oot}

    assert combinations == {
        (scenario, capacity)
        for scenario in ("customer_first", "balanced_reference", "loss_first")
        for capacity in (50, 100, 250, 500)
    }


def test_dashboard_has_no_placeholder_copy_and_loads_local_assets() -> None:
    html = (ROOT / "dashboard" / "index.html").read_text()

    assert "TODO" not in html
    assert 'href="styles.css"' in html
    assert 'src="app.js"' in html
    assert (ROOT / "dashboard" / "styles.css").is_file()
    assert (ROOT / "dashboard" / "app.js").is_file()
