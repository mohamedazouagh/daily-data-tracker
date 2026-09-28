"""Append-only CSV storage keyed by date (re-running a day never duplicates it)."""
from __future__ import annotations

import csv
from pathlib import Path


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def upsert_row(path: Path, row: dict) -> bool:
    """Insert or replace the row for row['date']. Returns True if the file changed."""
    rows = read_rows(path)
    new = {k: "" if v is None else str(v) for k, v in row.items()}
    for i, existing in enumerate(rows):
        if existing["date"] == new["date"]:
            if existing == new:
                return False
            rows[i] = new
            break
    else:
        rows.append(new)
    rows.sort(key=lambda r: r["date"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(new.keys()))
        writer.writeheader()
        writer.writerows(rows)
    return True
