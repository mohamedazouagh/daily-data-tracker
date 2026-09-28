from tracker import report, sources, store

WEATHER_PAYLOAD = {
    "daily": {
        "time": ["2026-09-27"],
        "temperature_2m_max": [17.4],
        "temperature_2m_min": [9.1],
        "precipitation_sum": [2.3],
        "sunshine_duration": [18000.0],
    }
}
FX_PAYLOAD = {"date": "2026-09-25", "rates": {"USD": 1.17, "GBP": 0.87, "CHF": 0.93, "TRY": 48.9}}


def test_parse_weather():
    row = sources.parse_weather(WEATHER_PAYLOAD)
    assert row == {"date": "2026-09-27", "temp_max_c": 17.4, "temp_min_c": 9.1, "precip_mm": 2.3, "sunshine_h": 5.0}


def test_parse_fx_keeps_business_date():
    assert sources.parse_fx(FX_PAYLOAD)["date"] == "2026-09-25"


def test_upsert_is_idempotent(tmp_path):
    path = tmp_path / "w.csv"
    row = sources.parse_weather(WEATHER_PAYLOAD)
    assert store.upsert_row(path, row) is True
    assert store.upsert_row(path, row) is False
    assert len(store.read_rows(path)) == 1


def test_upsert_sorts_by_date(tmp_path):
    path = tmp_path / "w.csv"
    store.upsert_row(path, {"date": "2026-09-27", "v": 1})
    store.upsert_row(path, {"date": "2026-09-26", "v": 2})
    assert [r["date"] for r in store.read_rows(path)] == ["2026-09-26", "2026-09-27"]


def test_replace_block_keeps_surroundings():
    readme = f"top\n{report.START}\nold\n{report.END}\nbottom"
    out = report.replace_block(readme, "new")
    assert out.startswith("top\n") and out.endswith("\nbottom") and "new" in out and "old" not in out


def test_sparkline_handles_single_value():
    assert report.sparkline_svg([5.0]).startswith("<svg")
