"""Daily entry point.

    python -m tracker.run fetch [YYYY-MM-DD]   # store yesterday's data (default)
    python -m tracker.run report               # rebuild README stats + chart
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

from tracker import report, sources, store

ROOT = Path(__file__).resolve().parent.parent
WEATHER = ROOT / "data" / "weather_breda.csv"
FX = ROOT / "data" / "eur_fx.csv"


def fetch(day: str) -> None:
    changed_w = store.upsert_row(WEATHER, sources.fetch_weather(day))
    changed_f = store.upsert_row(FX, sources.fetch_fx(day))
    print(f"{day}: weather {'updated' if changed_w else 'unchanged'}, fx {'updated' if changed_f else 'unchanged'}")


def build_report() -> None:
    weather, fx = store.read_rows(WEATHER), store.read_rows(FX)
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    readme_path.write_text(report.replace_block(readme, report.stats_markdown(weather, fx)), encoding="utf-8")
    temps = [float(r["temp_max_c"]) for r in weather if r["temp_max_c"]]
    (ROOT / "data" / "temp_max.svg").write_text(report.sparkline_svg(temps[-60:]), encoding="utf-8")
    print("report rebuilt")


def main(argv: list[str]) -> None:
    cmd = argv[1] if len(argv) > 1 else "fetch"
    if cmd == "fetch":
        day = argv[2] if len(argv) > 2 else (date.today() - timedelta(days=1)).isoformat()
        fetch(day)
    elif cmd == "report":
        build_report()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
