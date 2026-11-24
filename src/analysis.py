"""Regenerate the database, processed tables, charts, and printed figures."""

from __future__ import annotations

import os
from pathlib import Path

from src.charts import render_all
from src.metrics import ROOT, build_report
from src.report import key_figures, print_report

IMAGE_DIR = ROOT / "images"
README_PATH = ROOT / "README.md"


def check_readme(report: dict) -> None:
    text = README_PATH.read_text()
    missing = [figure for figure in key_figures(report) if figure not in text]
    if not missing:
        print("\nREADME contains the key figures.")
        return
    print("\nREADME is missing these figures:")
    for figure in missing:
        print(f"  {figure}")
    raise SystemExit(1)


def main() -> None:
    report = build_report()
    paths = render_all(report, IMAGE_DIR)
    print_report(report)
    print(f"\nWrote {len(paths)} charts to {IMAGE_DIR.relative_to(ROOT)}")
    if os.environ.get("CHECK_README") == "1":
        check_readme(report)


if __name__ == "__main__":
    main()
