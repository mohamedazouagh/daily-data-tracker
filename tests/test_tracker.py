from datetime import date, timedelta

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



def _day(rain, sun):
    return {"precip_mm": str(rain), "sunshine_h": str(sun)}


def test_rain_sun_correlation_negative():
    rows = [_day(0.0, 10.0), _day(2.0, 6.0), _day(5.0, 1.0), _day(1.0, 8.0)]
    r = report.rain_sun_correlation(rows)
    assert r is not None and r < -0.9


def test_rain_sun_correlation_needs_three_days():
    assert report.rain_sun_correlation([_day(0.0, 10.0), _day(2.0, 6.0)]) is None


def test_rain_sun_correlation_constant_series_is_none():
    rows = [_day(0.0, 10.0), _day(0.0, 6.0), _day(0.0, 1.0)]
    assert report.rain_sun_correlation(rows) is None


def test_rain_sun_correlation_skips_missing_values():
    rows = [_day(0.0, 10.0), {"precip_mm": "", "sunshine_h": "3"}, _day(2.0, 6.0), _day(5.0, 1.0)]
    assert report.rain_sun_correlation(rows) is not None


def test_stats_mentions_correlation():
    rows = [
        {"date": "2026-09-26", "temp_max_c": "20", "temp_min_c": "10", "precip_mm": "0", "sunshine_h": "9"},
        {"date": "2026-09-27", "temp_max_c": "18", "temp_min_c": "9", "precip_mm": "3", "sunshine_h": "2"},
    ]
    assert "Rain vs. sunshine correlation" in report.stats_markdown(rows, [])


def _fx(date, usd, gbp="0.86", chf="0.94", try_="55.0"):
    return {"date": date, "usd": usd, "gbp": gbp, "chf": chf, "try": try_}


def test_fx_pct_changes_between_last_two_days():
    rows = [_fx("2026-09-24", "1.00"), _fx("2026-09-25", "1.10"), _fx("2026-09-28", "1.21")]
    changes = report.fx_pct_changes(rows)
    assert round(changes["usd"], 6) == 10.0
    assert changes["gbp"] == 0.0


def test_fx_pct_changes_needs_two_rows():
    assert report.fx_pct_changes([_fx("2026-09-25", "1.1")]) == {}


def test_fx_pct_changes_skips_missing_values():
    rows = [_fx("2026-09-25", ""), _fx("2026-09-28", "1.1")]
    assert "usd" not in report.fx_pct_changes(rows)


def test_stats_shows_fx_change_line():
    rows = [_fx("2026-09-25", "1.00"), _fx("2026-09-28", "1.02")]
    assert "Change vs. 2026-09-25: USD +2.00%" in report.stats_markdown([], rows)


def test_biggest_fx_move_picks_largest_absolute_change():
    fx = [
        {"date": "2026-09-25", "usd": "1.0", "gbp": "0.8", "chf": "1.0", "try": "50"},
        {"date": "2026-09-28", "usd": "1.01", "gbp": "0.8", "chf": "1.0", "try": "50"},
        {"date": "2026-09-29", "usd": "1.01", "gbp": "0.78", "chf": "1.0", "try": "50"},
    ]
    code, day, pct = report.biggest_fx_move(fx)
    assert (code, day) == ("gbp", "2026-09-29")
    assert round(pct, 2) == -2.5


def test_biggest_fx_move_skips_missing_and_needs_two_rows():
    assert report.biggest_fx_move([]) is None
    assert report.biggest_fx_move([{"date": "2026-09-25", "usd": "1.0"}]) is None
    fx = [
        {"date": "2026-09-25", "usd": "", "gbp": "0", "chf": "1.0", "try": ""},
        {"date": "2026-09-28", "usd": "2.0", "gbp": "0.9", "chf": "1.1", "try": "51"},
    ]
    code, _, pct = report.biggest_fx_move(fx)
    assert code == "chf" and round(pct, 1) == 10.0


def test_stats_markdown_mentions_biggest_move():
    fx = [
        {"date": "2026-09-25", "usd": "1.0", "gbp": "0.8", "chf": "1.0", "try": "50"},
        {"date": "2026-09-28", "usd": "1.02", "gbp": "0.8", "chf": "1.0", "try": "50"},
    ]
    md = report.stats_markdown([], fx)
    assert "Biggest single-day move since tracking started: USD +2.00% on 2026-09-28" in md


def _rain_rows(*pairs):
    return [{"date": d, "precip_mm": p} for d, p in pairs]


def test_longest_dry_streak_picks_longest_run():
    rows = _rain_rows(
        ("2026-09-01", "0.0"), ("2026-09-02", "1.2"),
        ("2026-09-03", "0.0"), ("2026-09-04", "0.0"), ("2026-09-05", "0.0"),
        ("2026-09-06", "0.4"),
    )
    assert report.longest_dry_streak(rows) == (3, "2026-09-03", "2026-09-05")


def test_longest_dry_streak_breaks_on_date_gap_and_missing_value():
    rows = _rain_rows(
        ("2026-09-01", "0.0"), ("2026-09-02", "0.0"),
        ("2026-09-04", "0.0"),  # gap: 09-03 not stored
        ("2026-09-05", ""), ("2026-09-06", "0.0"),
    )
    assert report.longest_dry_streak(rows) == (2, "2026-09-01", "2026-09-02")


def test_longest_dry_streak_none_without_dry_days():
    assert report.longest_dry_streak(_rain_rows(("2026-09-01", "3.0"))) is None
    assert report.longest_dry_streak([]) is None


def _temp_rows(*pairs):
    return [{"date": d, "temp_max_c": t, "precip_mm": "0"} for d, t in pairs]


def test_longest_warm_streak_is_strictly_above_threshold():
    rows = _temp_rows(
        ("2026-09-01", "21.0"), ("2026-09-02", "20.0"),  # exactly 20 breaks it
        ("2026-09-03", "22.5"), ("2026-09-04", "24.1"),
        ("2026-09-05", "19.9"),
    )
    assert report.longest_warm_streak(rows) == (2, "2026-09-03", "2026-09-04")


def test_longest_warm_streak_custom_threshold_and_gaps():
    rows = _temp_rows(("2026-09-01", "16"), ("2026-09-02", "17"), ("2026-09-04", "18"), ("2026-09-05", ""))
    assert report.longest_warm_streak(rows, threshold=15) == (2, "2026-09-01", "2026-09-02")
    assert report.longest_warm_streak(rows) is None


def test_stats_mentions_warm_streak():
    rows = [
        {"date": "2026-09-26", "temp_max_c": "22", "temp_min_c": "10", "precip_mm": "0", "sunshine_h": "9"},
        {"date": "2026-09-27", "temp_max_c": "18", "temp_min_c": "9", "precip_mm": "3", "sunshine_h": "2"},
    ]
    assert "- Longest warm streak (max > 20 °C): **1 day** (2026-09-26)" in report.stats_markdown(rows, [])


def test_rolling_mean_aligns_with_input():
    assert report.rolling_mean([1, 2, 3, 4], window=3) == [None, None, 2, 3]
    assert report.rolling_mean([5.0], window=7) == [None]


def test_rolling_mean_rejects_bad_window():
    import pytest

    with pytest.raises(ValueError):
        report.rolling_mean([1, 2], window=0)


def test_sparkline_draws_overlay_only_with_two_points():
    values = [10.0, 12.0, 14.0, 16.0]
    with_avg = report.sparkline_svg(values, overlay=report.rolling_mean(values, 3))
    assert with_avg.count("<polyline") == 2 and "7-day avg" in with_avg
    too_short = report.sparkline_svg(values, overlay=report.rolling_mean(values, 4))
    assert too_short.count("<polyline") == 1


def test_coldest_night_picks_lowest_min_earliest_on_tie():
    rows = [
        {"date": "2026-09-02", "temp_min_c": "6.5"},
        {"date": "2026-09-01", "temp_min_c": "6.5"},
        {"date": "2026-09-03", "temp_min_c": ""},
        {"date": "2026-09-04", "temp_min_c": "9.0"},
    ]
    assert report.coldest_night(rows) == ("2026-09-01", 6.5)


def test_coldest_night_none_without_values():
    assert report.coldest_night([{"date": "2026-09-01", "temp_min_c": ""}]) is None
    assert report.coldest_night([]) is None


def test_largest_daily_range_skips_incomplete_rows():
    rows = [
        {"date": "2026-09-01", "temp_max_c": "20.0", "temp_min_c": "12.0"},
        {"date": "2026-09-02", "temp_max_c": "25.0", "temp_min_c": ""},
        {"date": "2026-09-03", "temp_max_c": "19.7", "temp_min_c": "7.9"},
        {"date": "2026-09-04", "temp_max_c": "21.8", "temp_min_c": "10.0"},
    ]
    assert report.largest_daily_range(rows) == ("2026-09-03", 11.8)


def test_largest_daily_range_none_without_pairs():
    assert report.largest_daily_range([{"date": "2026-09-01", "temp_max_c": "20", "temp_min_c": ""}]) is None


def test_sunshine_summary_skips_missing_and_breaks_ties_early():
    rows = [
        {"date": "2026-09-03", "sunshine_h": "11.0"},
        {"date": "2026-09-01", "sunshine_h": "11.0"},
        {"date": "2026-09-02", "sunshine_h": ""},
        {"date": "2026-09-04", "sunshine_h": "4.0"},
    ]
    day, best, avg = report.sunshine_summary(rows)
    assert (day, best) == ("2026-09-01", 11.0)
    assert abs(avg - 26.0 / 3) < 1e-9


def test_sunshine_summary_none_without_values():
    assert report.sunshine_summary([{"date": "2026-09-01", "sunshine_h": ""}]) is None
    assert report.sunshine_summary([]) is None


def test_stats_markdown_mentions_sunniest_day():
    rows = [
        {"date": "2026-09-01", "temp_max_c": "20", "temp_min_c": "10", "precip_mm": "0", "sunshine_h": "9.5"},
        {"date": "2026-09-02", "temp_max_c": "21", "temp_min_c": "11", "precip_mm": "1", "sunshine_h": "3.5"},
    ]
    md = report.stats_markdown(rows, [])
    assert "Sunniest day: **9.5 h** on 2026-09-01 · Average sunshine: **6.5 h/day**" in md


def _rain(day: str, mm) -> dict:
    return {"date": day, "precip_mm": "" if mm is None else str(mm)}


def test_wettest_day_picks_most_rain():
    rows = [_rain("2026-09-28", 1.9), _rain("2026-09-30", 4.2), _rain("2026-09-29", 0.1)]
    assert report.wettest_day(rows) == ("2026-09-30", 4.2)


def test_wettest_day_tie_goes_to_earliest_and_skips_missing():
    rows = [_rain("2026-10-02", 3.0), _rain("2026-10-01", 3.0), _rain("2026-10-03", None)]
    assert report.wettest_day(rows) == ("2026-10-01", 3.0)


def test_wettest_day_none_when_all_dry():
    assert report.wettest_day([_rain("2026-10-01", 0.0), _rain("2026-10-02", None)]) is None
    assert report.wettest_day([]) is None


def test_warmest_night_picks_highest_min_earliest_on_tie():
    rows = [
        {"date": "2026-09-03", "temp_min_c": "14.2"},
        {"date": "2026-09-01", "temp_min_c": "14.2"},
        {"date": "2026-09-02", "temp_min_c": ""},
        {"date": "2026-09-04", "temp_min_c": "-1.0"},
    ]
    assert report.warmest_night(rows) == ("2026-09-01", 14.2)


def test_warmest_night_none_without_values():
    assert report.warmest_night([{"date": "2026-09-01", "temp_min_c": ""}]) is None
    assert report.warmest_night([]) is None


def test_stats_markdown_includes_warmest_night():
    rows = [
        {"date": "2026-09-01", "temp_max_c": "20.0", "temp_min_c": "9.0", "precip_mm": "0.0", "sunshine_h": "5.0"},
        {"date": "2026-09-02", "temp_max_c": "22.0", "temp_min_c": "15.5", "precip_mm": "1.0", "sunshine_h": "3.0"},
    ]
    md = report.stats_markdown(rows, [])
    assert "- Warmest night: **15.5 °C** on 2026-09-02" in md


def _rain_days(start: str, amounts: list) -> list[dict]:
    first = date.fromisoformat(start)
    return [_rain((first + timedelta(days=i)).isoformat(), mm) for i, mm in enumerate(amounts)]


def test_rainiest_week_finds_highest_seven_day_total():
    rows = _rain_days("2026-10-01", [0, 1, 0, 0, 5, 0, 0, 2, 0.4])
    # windows: 10-01..07 = 6.0, 10-02..08 = 8.0, 10-03..09 = 7.4
    assert report.rainiest_week(rows) == ("2026-10-02", "2026-10-08", 8.0)


def test_rainiest_week_needs_full_windows_and_takes_earliest_tie():
    assert report.rainiest_week(_rain_days("2026-10-01", [9, 9, 9, 9, 9, 9])) is None
    gap = _rain_days("2026-10-01", [1] * 4) + _rain_days("2026-10-06", [1] * 4)
    assert report.rainiest_week(gap) is None  # 10-05 missing, so no 7-day run
    missing_value = _rain_days("2026-10-01", [1, 1, 1, "", 1, 1, 1])
    assert report.rainiest_week(missing_value) is None
    flat = _rain_days("2026-10-01", [1] * 8)
    assert report.rainiest_week(flat) == ("2026-10-01", "2026-10-07", 7.0)


def test_stats_markdown_includes_rainiest_week():
    rows = [dict(r, temp_max_c=20, temp_min_c=10, sunshine_h=5) for r in _rain_days("2026-10-01", [1] * 7)]
    md = report.stats_markdown(rows, [])
    assert "- Rainiest week: **7.0 mm** (2026-10-01 → 2026-10-07)" in md
    assert "needs 7 consecutive days" in report.stats_markdown(rows[:3], [])
