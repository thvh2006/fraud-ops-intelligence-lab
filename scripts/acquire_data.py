"""Download IEEE-CIS files through the official Kaggle CLI."""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
COMPETITION = "ieee-fraud-detection"


def main() -> int:
    kaggle = shutil.which("kaggle")
    if kaggle is None:
        print(
            "Kaggle CLI is not available. Install/configure the official Kaggle client, "
            "accept the competition rules, then rerun this script.",
            file=sys.stderr,
        )
        return 2

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [kaggle, "competitions", "download", "-c", COMPETITION, "-p", str(RAW_DIR)],
        check=False,
    )
    if result.returncode != 0:
        print(
            "Download failed. Verify Kaggle authentication and competition-rule acceptance.",
            file=sys.stderr,
        )
        return result.returncode

    archive = RAW_DIR / f"{COMPETITION}.zip"
    if not archive.exists():
        print(f"Expected archive was not created: {archive}", file=sys.stderr)
        return 3
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(RAW_DIR)
    archive.unlink()
    print(f"Data extracted to {RAW_DIR}. Raw files remain git-ignored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

