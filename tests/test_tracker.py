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


def test_longest_wet_streak_picks_longest_run_earliest_on_ties():
    rows = _rain_rows(
        ("2026-09-01", "0.2"), ("2026-09-02", "3.0"),
        ("2026-09-03", "0.0"),
        ("2026-09-04", "1.1"), ("2026-09-05", "0.4"),
        ("2026-09-06", "0.0"),
    )
    assert report.longest_wet_streak(rows) == (2, "2026-09-01", "2026-09-02")


def test_longest_wet_streak_breaks_on_gap_and_missing_value():
    rows = _rain_rows(
        ("2026-09-01", "2.0"), ("2026-09-02", "1.0"), ("2026-09-03", "0.5"),
        ("2026-09-05", "4.0"),  # gap: 09-04 not stored
        ("2026-09-06", ""), ("2026-09-07", "1.0"),
    )
    assert report.longest_wet_streak(rows) == (3, "2026-09-01", "2026-09-03")


def test_longest_wet_streak_none_when_all_dry_or_empty():
    assert report.longest_wet_streak(_rain_rows(("2026-09-01", "0.0"))) is None
    assert report.longest_wet_streak([]) is None


def test_stats_markdown_includes_longest_wet_run():
    rows = [
        {"date": d, "temp_max_c": "15", "temp_min_c": "8", "precip_mm": p, "sunshine_h": "5"}
        for d, p in [("2026-09-01", "1.0"), ("2026-09-02", "2.5"), ("2026-09-03", "0.0")]
    ]
    md = report.stats_markdown(rows, [])
    assert "- Longest wet run: **2 days** (2026-09-01 → 2026-09-02)" in md


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


def _tmax_days(start: str, temps: list) -> list[dict]:
    first = date.fromisoformat(start)
    return [
        {"date": (first + timedelta(days=i)).isoformat(), "temp_max_c": "" if t is None else str(t)}
        for i, t in enumerate(temps)
    ]


def test_week_over_week_max_compares_calendar_windows():
    rows = _tmax_days("2026-09-24", [10] * 7 + [14] * 7)
    assert report.week_over_week_max(rows) == (14, 10, 4)


def test_week_over_week_max_handles_gaps_and_missing_values():
    # latest 2026-10-07; this week 10-01..07, previous week 09-24..30
    rows = _tmax_days("2026-09-29", [12, None]) + _tmax_days("2026-10-05", [20, 22, 24])
    this_week, prev_week, diff = report.week_over_week_max(rows)
    assert (this_week, prev_week) == (22, 12)
    assert diff == 10


def test_week_over_week_max_none_without_previous_week():
    assert report.week_over_week_max(_tmax_days("2026-10-01", [15] * 7)) is None
    assert report.week_over_week_max([]) is None


def test_stats_markdown_includes_week_over_week_line():
    rows = [dict(r, temp_min_c=5, precip_mm=0, sunshine_h=4) for r in _tmax_days("2026-09-24", [18] * 7 + [16.5] * 7)]
    md = report.stats_markdown(rows, [])
    assert "- Last 7 days vs. the 7 before (avg max): **16.5 °C** vs. 18.0 °C (-1.5 °C)" in md


def _usd_days(values):
    days = ["2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06"]
    return [{"date": d, "usd": v} for d, v in zip(days, values)]


def test_calmest_fx_stretch_counts_business_days_between_big_moves():
    # 1.00 -> 1.02 (+2%, breaks), then 1.02 -> 1.021 -> 1.019 -> 1.020 calm, then +1% breaks
    fx = _usd_days([1.00, 1.02, 1.021, 1.019, 1.020, 1.0302, 1.031])
    assert report.calmest_fx_stretch(fx) == (4, "2026-09-29", "2026-10-02")


def test_calmest_fx_stretch_threshold_is_inclusive_and_missing_breaks():
    fx = _usd_days([1.0, 1.005, "", 2.0, 2.001])
    # +0.5% exactly is calm; the missing rate splits the run; earliest wins the tie
    assert report.calmest_fx_stretch(fx) == (2, "2026-09-28", "2026-09-29")


def test_calmest_fx_stretch_none_when_every_move_is_big():
    assert report.calmest_fx_stretch(_usd_days([1.0, 1.1, 1.2])) is None
    assert report.calmest_fx_stretch([]) is None


def test_stats_markdown_includes_calm_usd_line():
    fx = [dict(r, gbp=0.85, chf=0.93, **{"try": 55.0}) for r in _usd_days([1.0, 1.001, 1.002])]
    md = report.stats_markdown([], fx)
    assert "Longest calm USD stretch (no daily move above 0.5%): **3 business days** (2026-09-28 → 2026-09-30)" in md


def _rain_days(start, values):
    first = date.fromisoformat(start)
    return [{"date": (first + timedelta(days=i)).isoformat(), "precip_mm": v} for i, v in enumerate(values)]


def test_wettest_weekday_averages_including_dry_days():
    # 2026-09-28 is a Monday; two weeks of data
    rows = _rain_days("2026-09-28", [4.0, 0, 0, 0, 0, 3.0, 0, 0.0, 0, 0, 0, 0, 3.0, 0])
    # Monday: (4 + 0) / 2 = 2.0; Saturday: (3 + 3) / 2 = 3.0
    assert report.wettest_weekday(rows) == ("Saturday", 3.0, 2)


def test_wettest_weekday_tie_goes_to_earlier_weekday_and_skips_missing():
    rows = _rain_days("2026-09-28", [2.0, 2.0, ""])
    assert report.wettest_weekday(rows) == ("Monday", 2.0, 1)


def test_wettest_weekday_none_without_rain():
    assert report.wettest_weekday([]) is None
    assert report.wettest_weekday(_rain_days("2026-09-28", [0, 0.0, ""])) is None


def test_stats_markdown_includes_wettest_weekday_line():
    rows = [
        dict(r, temp_max_c=15.0, temp_min_c=8.0, sunshine_h=5.0)
        for r in _rain_days("2026-09-28", [1.0, 5.0, 0.0])
    ]
    md = report.stats_markdown(rows, [])
    assert "- Wettest weekday so far: **Tuesday** (5.0 mm on average over 1 day)" in md


def _nights(values):
    first = date.fromisoformat("2026-11-01")
    return [{"date": (first + timedelta(days=i)).isoformat(), "temp_min_c": v} for i, v in enumerate(values)]


def test_first_frost_is_earliest_night_strictly_below_zero():
    rows = _nights([2.0, 0.0, "", -1.5, -3.0])
    assert report.first_frost(rows) == ("2026-11-04", -1.5)


def test_first_frost_ignores_input_order():
    rows = _nights([1.0, -0.5, -2.0])[::-1]
    assert report.first_frost(rows) == ("2026-11-02", -0.5)


def test_first_frost_none_without_frost():
    assert report.first_frost(_nights([0.0, 3.2, ""])) is None
    assert report.first_frost([]) is None


def test_stats_markdown_frost_line():
    base = {"temp_max_c": 8.0, "precip_mm": 0.0, "sunshine_h": 3.0}
    md = report.stats_markdown([dict(r, **base) for r in _nights([1.0, -0.4])], [])
    assert "- First frost: **-0.4 °C** on 2026-11-02" in md
    md = report.stats_markdown([dict(r, **base) for r in _nights([1.0])], [])
    assert "- First frost (min below 0 °C): none yet" in md


def _sun_days(start, values):
    first = date.fromisoformat(start)
    return [{"date": (first + timedelta(days=i)).isoformat(), "sunshine_h": v} for i, v in enumerate(values)]


def test_sunniest_weekday_averages_including_overcast_days():
    # 2026-09-28 is a Monday; Friday gets 10 h and 0 h, Sunday 6 h twice
    rows = _sun_days("2026-09-28", [4.0, 1.0, 1.0, 1.0, 10.0, 2.0, 6.0, 4.0, 1.0, 1.0, 1.0, 0.0, 2.0, 6.0])
    assert report.sunniest_weekday(rows) == ("Sunday", 6.0, 2)


def test_sunniest_weekday_tie_goes_to_earlier_weekday_and_skips_missing():
    rows = _sun_days("2026-09-28", ["", 3.0, 3.0])
    assert report.sunniest_weekday(rows) == ("Tuesday", 3.0, 1)


def test_sunniest_weekday_none_without_sun():
    assert report.sunniest_weekday([]) is None
    assert report.sunniest_weekday(_sun_days("2026-09-28", [0, 0.0, ""])) is None


def test_stats_markdown_includes_sunniest_weekday_line():
    rows = [
        dict(r, temp_max_c=15.0, temp_min_c=8.0, precip_mm=0.0)
        for r in _sun_days("2026-09-28", [2.0, 9.5, 4.0])
    ]
    md = report.stats_markdown(rows, [])
    assert "- Sunniest weekday so far: **Tuesday** (9.5 h on average over 1 day)" in md


def _usd_on(pairs):
    return [{"date": d, "usd": v} for d, v in pairs]


def test_weekend_gap_moves_splits_gaps_from_daily_moves():
    fx = _usd_on([
        ("2026-10-01", 1.00),  # Thu
        ("2026-10-02", 1.01),  # Fri: +1% daily
        ("2026-10-05", 0.99981),  # Mon: -1.01% over the weekend gap
        ("2026-10-06", 0.99981),  # Tue: 0% daily
    ])
    g, gn, d, dn = report.weekend_gap_moves(fx)
    assert (gn, dn) == (1, 2)
    assert round(g, 2) == 1.01
    assert round(d, 2) == 0.50


def test_weekend_gap_moves_skips_missing_and_zero_rates():
    fx = _usd_on([("2026-10-02", 0), ("2026-10-05", 1.0), ("2026-10-06", ""), ("2026-10-07", 1.0)])
    assert report.weekend_gap_moves(fx) is None


def test_weekend_gap_moves_needs_both_kinds():
    assert report.weekend_gap_moves([]) is None
    assert report.weekend_gap_moves(_usd_on([("2026-10-05", 1.0), ("2026-10-06", 1.1)])) is None


def test_stats_markdown_includes_weekend_gap_line():
    fx = [
        dict(r, gbp=0.85, chf=0.93, **{"try": 55.0})
        for r in _usd_on([("2026-10-01", 1.0), ("2026-10-02", 1.01), ("2026-10-05", 0.99981)])
    ]
    md = report.stats_markdown([], fx)
    assert "Weekend gaps vs. weekdays (avg absolute move):" in md
    assert "- USD: **1.01%** over 1 gap vs. 1.00% over 1 weekday move (about the same)" in md
    # Flat GBP/CHF/TRY: both moves are 0 -> still listed, labelled honestly.
    assert "- GBP: **0.00%** over 1 gap vs. 0.00% over 1 weekday move (no movement)" in md


def test_weekend_gap_all_covers_every_currency_with_both_kinds():
    fx = [
        {"date": "2026-10-01", "usd": 1.0, "gbp": 0.80, "chf": 0.90, "try": ""},
        {"date": "2026-10-02", "usd": 1.0, "gbp": 0.808, "chf": 0.90, "try": 50.0},
        {"date": "2026-10-05", "usd": 1.0, "gbp": 0.808, "chf": 0.909, "try": 50.5},
    ]
    res = report.weekend_gap_all(fx)
    # TRY has no weekday pair (first value missing), so it is left out.
    assert list(res) == ["usd", "gbp", "chf"]
    g, gn, d, dn = res["gbp"]
    assert (gn, dn) == (1, 1) and g == 0 and round(d, 2) == 1.00
    g, gn, d, dn = res["chf"]
    assert round(g, 2) == 1.00 and d == 0


def test_gap_verdict_labels():
    assert report._gap_verdict(1.0, 0.5) == "gaps larger"
    assert report._gap_verdict(0.5, 1.0) == "gaps smaller"
    assert report._gap_verdict(1.0, 1.1) == "about the same"
    assert report._gap_verdict(0.3, 0) == "weekdays flat"
    assert report._gap_verdict(0, 0) == "no movement"


def test_dry_share_by_weekday_counts_dry_days_in_calendar_order():
    rows = [
        {"date": "2026-10-07", "precip_mm": "0.0"},  # Wednesday, dry
        {"date": "2026-10-05", "precip_mm": "0.0"},  # Monday, dry
        {"date": "2026-10-12", "precip_mm": "1.2"},  # Monday, wet
        {"date": "2026-10-06", "precip_mm": ""},  # Tuesday, missing -> left out
    ]
    assert report.dry_share_by_weekday(rows) == {"Monday": (1, 2), "Wednesday": (1, 1)}


def test_dry_share_by_weekday_empty():
    assert report.dry_share_by_weekday([]) == {}


def test_stats_markdown_includes_dry_days_by_weekday():
    rows = [
        {"date": "2026-10-05", "temp_max_c": "15", "temp_min_c": "8", "precip_mm": "0.0", "sunshine_h": "4"},
        {"date": "2026-10-06", "temp_max_c": "16", "temp_min_c": "9", "precip_mm": "2.5", "sunshine_h": "1"},
    ]
    md = report.stats_markdown(rows, [])
    assert "- Dry days by weekday: Mon 1/1 · Tue 0/1" in md


def test_fx_since_start_uses_first_and_last_usable_value_per_currency():
    fx = [
        {"date": "2026-10-01", "usd": "1.0", "gbp": "", "chf": "0", "try": "50"},
        {"date": "2026-10-02", "usd": "1.1", "gbp": "0.80", "chf": "0.90", "try": ""},
        {"date": "2026-10-05", "usd": "1.05", "gbp": "0.82", "chf": "", "try": ""},
    ]
    res = report.fx_since_start(fx)
    # CHF has only one usable value (zero is skipped), TRY only one -> left out.
    assert list(res) == ["usd", "gbp"]
    assert res["usd"][0] == "2026-10-01" and round(res["usd"][1], 2) == 5.00
    assert res["gbp"][0] == "2026-10-02" and round(res["gbp"][1], 2) == 2.50


def test_fx_since_start_needs_two_rows():
    assert report.fx_since_start([]) == {}
    assert report.fx_since_start([{"date": "2026-10-01", "usd": "1.0", "gbp": "", "chf": "", "try": ""}]) == {}


def test_stats_markdown_since_start_line_shares_start_date():
    fx = [
        {"date": "2026-10-01", "usd": "1.0", "gbp": "0.80", "chf": "0.90", "try": "50"},
        {"date": "2026-10-02", "usd": "1.02", "gbp": "0.80", "chf": "0.90", "try": "51"},
    ]
    md = report.stats_markdown([], fx)
    assert "Change since tracking started (2026-10-01): USD +2.00% · GBP +0.00% · CHF +0.00% · TRY +2.00%" in md


def test_stats_markdown_since_start_line_lists_differing_start_dates():
    fx = [
        {"date": "2026-10-01", "usd": "1.0", "gbp": "", "chf": "", "try": ""},
        {"date": "2026-10-02", "usd": "1.01", "gbp": "0.80", "chf": "", "try": ""},
        {"date": "2026-10-05", "usd": "1.01", "gbp": "0.84", "chf": "", "try": ""},
    ]
    md = report.stats_markdown([], fx)
    assert "Change since tracking started: USD +1.00% (from 2026-10-01) · GBP +5.00% (from 2026-10-02)" in md


def test_wet_day_intensity_ignores_dry_and_missing_days():
    rows = [
        {"date": "2026-10-01", "precip_mm": "0.0"},
        {"date": "2026-10-02", "precip_mm": "3.0"},
        {"date": "2026-10-03", "precip_mm": ""},
        {"date": "2026-10-04", "precip_mm": "1.0"},
        {"date": "2026-10-05", "precip_mm": "0"},
    ]
    assert report.wet_day_intensity(rows) == (2.0, 2)


def test_wet_day_intensity_none_without_rain():
    assert report.wet_day_intensity([]) is None
    assert report.wet_day_intensity([{"date": "2026-10-01", "precip_mm": "0.0"}]) is None


def test_stats_markdown_rain_intensity_line():
    rows = [
        {"date": "2026-10-05", "temp_max_c": "15", "temp_min_c": "8", "precip_mm": "4.5", "sunshine_h": "2"},
        {"date": "2026-10-06", "temp_max_c": "16", "temp_min_c": "9", "precip_mm": "0.0", "sunshine_h": "8"},
    ]
    md = report.stats_markdown(rows, [])
    assert "- Rain intensity (wet days only): **4.5 mm/day** over 1 wet day" in md


def _fx_rows(usd_values, start=date(2026, 10, 1)):
    return [
        {"date": (start + timedelta(days=i)).isoformat(), "usd": "" if v is None else str(v), "gbp": "", "chf": "", "try": ""}
        for i, v in enumerate(usd_values)
    ]


def test_fx_best_worst_week_compares_rows_five_apart():
    fx = _fx_rows([1.00, 1.00, 1.10, 1.00, 1.00, 1.05, 0.99])
    res = report.fx_best_worst_week(fx)
    assert list(res) == ["usd"]
    (b1, b2, bp), (w1, w2, wp) = res["usd"]
    assert (b1, b2, round(bp, 2)) == ("2026-10-01", "2026-10-06", 5.00)
    assert (w1, w2, round(wp, 2)) == ("2026-10-02", "2026-10-07", -1.00)


def test_fx_best_worst_week_skips_missing_endpoints_and_short_history():
    assert report.fx_best_worst_week(_fx_rows([1.0, 1.0, 1.0, 1.0, 1.0])) == {}
    assert report.fx_best_worst_week(_fx_rows([None, 1.0, 1.0, 1.0, 1.0, 1.2])) == {}


def test_stats_markdown_best_worst_week_lines():
    md = report.stats_markdown([], _fx_rows([1.00, 1.00, 1.10, 1.00, 1.00, 1.05, 0.99]))
    assert "- USD: best **+5.00%** (2026-10-01 → 2026-10-06) · worst **-1.00%** (2026-10-02 → 2026-10-07)" in md


def _daily_rain(values, start=date(2026, 10, 1)):
    return [
        {"date": (start + timedelta(days=i)).isoformat(), "temp_max_c": "15", "temp_min_c": "8",
         "precip_mm": "" if v is None else str(v), "sunshine_h": "5"}
        for i, v in enumerate(values)
    ]


def test_heaviest_rain_share_uses_total_of_all_days():
    day, mm, pct = report.heaviest_rain_share(_daily_rain([0.0, 6.0, 2.0, None, 2.0]))
    assert (day, mm, round(pct, 1)) == ("2026-10-02", 6.0, 60.0)


def test_heaviest_rain_share_none_without_rain_and_earliest_tie():
    assert report.heaviest_rain_share(_daily_rain([0.0, 0.0])) is None
    assert report.heaviest_rain_share([]) is None
    assert report.heaviest_rain_share(_daily_rain([3.0, 3.0]))[0] == "2026-10-01"


def test_stats_markdown_heaviest_rain_share_line():
    md = report.stats_markdown(_daily_rain([1.0, 3.0]), [])
    assert "- Wettest day's share of all rain: **75%** (3.0 mm on 2026-10-02)" in md


def test_fx_volatility_is_sample_stdev_of_daily_moves():
    # moves: +1%, -1%, +1% -> sample stdev = sqrt(4/3) ~ 1.1547
    fx = _fx_rows([100.0, 101.0, 99.99, 100.9899])
    sd, n = report.fx_volatility(fx)["usd"]
    assert n == 3
    assert round(sd, 4) == 1.1547


def test_fx_volatility_skips_gaps_and_needs_two_moves():
    assert report.fx_volatility(_fx_rows([1.0, 1.1])) == {}
    assert report.fx_volatility(_fx_rows([1.0, None, 1.0, 1.0])) == {}
    assert report.fx_volatility(_fx_rows([1.0, 1.0, 1.0]))["usd"] == (0.0, 2)


def test_stats_markdown_volatility_line():
    md = report.stats_markdown([], _fx_rows([100.0, 101.0, 99.99, 100.9899]))
    assert "Realised volatility (std. dev. of daily moves, 3 moves): USD 1.15%" in md


def test_top_rain_days_share_sums_three_wettest():
    top, pct = report.top_rain_days_share(_daily_rain([1.0, 4.0, 0.0, 2.0, None, 3.0]))
    assert top == [("2026-10-02", 4.0), ("2026-10-06", 3.0), ("2026-10-04", 2.0)]
    assert round(pct, 1) == 90.0


def test_top_rain_days_share_edge_cases():
    assert report.top_rain_days_share(_daily_rain([0.0, 0.0])) is None
    top, pct = report.top_rain_days_share(_daily_rain([2.0, 0.0]))
    assert top == [("2026-10-01", 2.0)] and pct == 100.0
    top, _ = report.top_rain_days_share(_daily_rain([1.0, 1.0, 1.0, 1.0]), n=2)
    assert [d for d, _ in top] == ["2026-10-01", "2026-10-02"]


def test_stats_markdown_top3_rain_line_only_with_three_wet_days():
    md = report.stats_markdown(_daily_rain([1.0, 3.0, 0.0, 4.0, 2.0]), [])
    assert "- Share of rain from the 3 wettest days: **90%** (2026-10-04 4.0 mm, 2026-10-02 3.0 mm, 2026-10-05 2.0 mm)" in md
    assert "3 wettest days" not in report.stats_markdown(_daily_rain([1.0, 3.0]), [])


def _fx_from_moves(pcts, start=100.0):
    values = [start]
    for p in pcts:
        values.append(values[-1] * (1 + p / 100))
    return _fx_rows(values)


def test_fx_rolling_volatility_compares_first_and_latest_window():
    # first 3 moves swing +-2%, latest 3 moves swing +-1%
    fx = _fx_from_moves([2, -2, 2, -1, 1, -1])
    first, latest = report.fx_rolling_volatility(fx, window=3)["usd"]
    assert round(first, 4) == round(report.stdev([2, -2, 2]), 4)
    assert round(latest, 4) == round(report.stdev([-1, 1, -1]), 4)


def test_fx_rolling_volatility_needs_more_moves_than_window():
    assert report.fx_rolling_volatility(_fx_from_moves([1, -1, 1]), window=3) == {}
    assert "usd" in report.fx_rolling_volatility(_fx_from_moves([1, -1, 1, 1]), window=3)


def test_vol_trend_labels():
    assert report._vol_trend(1.0, 0.5) == "calmer"
    assert report._vol_trend(1.0, 1.05) == "steady"
    assert report._vol_trend(1.0, 1.5) == "choppier"
    assert report._vol_trend(0.0, 0.0) == "steady"


def test_stats_markdown_rolling_volatility_line():
    md = report.stats_markdown([], _fx_from_moves([2, -2] * 5 + [0.5, -0.5] * 5))
    assert "10-move volatility, first window → latest: USD 2.11% → 0.53% (calmer)" in md


def _fx_multi(series, start=date(2026, 10, 1)):
    """Rows with several currencies; ``series`` maps code -> list of values (same length)."""
    n = len(next(iter(series.values())))
    return [
        {"date": (start + timedelta(days=i)).isoformat(),
         **{c: (str(series[c][i]) if c in series and series[c][i] is not None else "") for c in report.FX_CODES}}
        for i in range(n)
    ]


def _path(pcts, start=100.0):
    values = [start]
    for p in pcts:
        values.append(values[-1] * (1 + p / 100))
    return values


def test_fx_volatility_ranking_orders_calmest_first():
    fx = _fx_multi({"usd": _path([1, -1] * 3), "gbp": _path([0.1, -0.1] * 3), "chf": _path([3, -3] * 3)})
    ranking = report.fx_volatility_ranking(fx, window=4)
    assert [c for c, _ in ranking] == ["gbp", "usd", "chf"]
    assert round(ranking[0][1], 4) == round(report.stdev([0.1, -0.1, 0.1, -0.1]), 4)


def test_fx_volatility_ranking_uses_only_latest_window_and_skips_short_series():
    # usd was wild early but calm lately; try has too few moves to be ranked
    fx = _fx_multi({"usd": _path([5, -5, 0.1, -0.1, 0.1]), "gbp": _path([1, -1, 1, -1, 1]),
                    "try": [None, None, None, 1.0, 1.01, 1.0]})
    ranking = report.fx_volatility_ranking(fx, window=3)
    assert [c for c, _ in ranking] == ["usd", "gbp"]


def test_fx_volatility_ranking_rejects_tiny_window():
    import pytest

    with pytest.raises(ValueError):
        report.fx_volatility_ranking([], window=1)


def test_stats_markdown_volatility_ranking_line_needs_two_currencies():
    fx = _fx_multi({"usd": _path([1, -1] * 5), "gbp": _path([0.5, -0.5] * 5)})
    md = report.stats_markdown([], fx)
    assert "Calmest → choppiest over the latest 10 moves: GBP 0.53% < USD 1.05% (calmest: **GBP**)" in md
    assert "Calmest" not in report.stats_markdown([], _fx_from_moves([1, -1] * 5))


def test_weekend_vs_weekday_rain_splits_saturday_sunday():
    # 2026-10-01 is a Thursday: Thu, Fri, Sat, Sun, Mon
    rows = _daily_rain([1.0, 3.0, 4.0, 0.0, 2.0])
    we, wen, wd, wdn = report.weekend_vs_weekday_rain(rows)
    assert (we, wen, wd, wdn) == (2.0, 2, 2.0, 3)


def test_weekend_vs_weekday_rain_skips_missing_and_needs_both_groups():
    rows = _daily_rain([1.0, None, 5.0, 1.0])  # Thu, Fri (missing), Sat, Sun
    assert report.weekend_vs_weekday_rain(rows) == (3.0, 2, 1.0, 1)
    assert report.weekend_vs_weekday_rain(_daily_rain([1.0, 2.0])) is None  # Thu + Fri only


def test_stats_markdown_weekend_rain_line():
    md = report.stats_markdown(_daily_rain([1.0, 3.0, 4.0, 0.0, 2.0]), [])
    assert "- Weekend vs. weekday rain: **2.0 mm/day** over 2 weekend days vs. 2.0 mm/day over 3 weekdays" in md


def test_weekend_vs_weekday_sunshine_counts_overcast_days():
    # 2026-09-28 is a Monday: Mon..Sun, then Mon
    rows = _sun_days("2026-09-28", [4.0, 2.0, 0.0, 6.0, 3.0, 9.0, 7.0, 0.0])
    we, wen, wd, wdn = report.weekend_vs_weekday_sunshine(rows)
    assert (we, wen, wdn) == (8.0, 2, 6)
    assert round(wd, 4) == round(15.0 / 6, 4)


def test_weekend_vs_weekday_sunshine_skips_missing_and_needs_both_groups():
    rows = _sun_days("2026-10-02", [5.0, "", 3.0])  # Fri, Sat (missing), Sun
    assert report.weekend_vs_weekday_sunshine(rows) == (3.0, 1, 5.0, 1)
    assert report.weekend_vs_weekday_sunshine(_sun_days("2026-09-28", [1.0, 2.0])) is None  # Mon + Tue only


def test_stats_markdown_weekend_sunshine_line():
    md = report.stats_markdown(_daily_rain([1.0, 3.0, 4.0, 0.0, 2.0]), [])
    assert "- Weekend vs. weekday sunshine: **5.0 h/day** over 2 weekend days vs. 5.0 h/day over 3 weekdays" in md


def test_current_rain_run_counts_back_from_latest_day():
    assert report.current_rain_run(_daily_rain([0.0, 0.0, 1.2, 0.4, 3.0])) == ("wet", 3, "2026-10-03")
    assert report.current_rain_run(_daily_rain([2.0, 0.0, 0.0])) == ("dry", 2, "2026-10-02")
    assert report.current_rain_run(_daily_rain([0.0, 0.0, 5.0])) == ("wet", 1, "2026-10-03")


def test_current_rain_run_stops_at_gap_or_missing_value():
    rows = _daily_rain([0.0, 0.0, 0.0, 0.0])
    del rows[1]  # 2026-10-02 missing: run is 10-03 and 10-04 only
    assert report.current_rain_run(rows) == ("dry", 2, "2026-10-03")
    assert report.current_rain_run(_daily_rain([1.0, None, 2.0])) == ("wet", 1, "2026-10-03")
    assert report.current_rain_run(_daily_rain([1.0, None])) is None
    assert report.current_rain_run([]) is None


def test_stats_markdown_current_run_line():
    md = report.stats_markdown(_daily_rain([0.0, 1.0, 2.5]), [])
    assert "- Current run: **2 wet days in a row** since 2026-10-02" in md
    md = report.stats_markdown(_daily_rain([1.0, 0.0]), [])
    assert "- Current run: **1 dry day in a row**\n" in md + "\n"


def _max_days(start: str, temps: list) -> list[dict]:
    d0 = date.fromisoformat(start)
    return [
        {"date": (d0 + timedelta(days=i)).isoformat(), "temp_max_c": "" if v is None else v}
        for i, v in enumerate(temps)
    ]


def test_weekend_vs_weekday_max_temp_splits_and_skips_missing():
    # 2026-09-28 is a Monday: Mon..Fri, Sat, Sun (missing), Mon
    rows = _max_days("2026-09-28", [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, None, 15.0])
    assert report.weekend_vs_weekday_max_temp(rows) == (20.0, 1, 14.166666666666666, 6)


def test_weekend_vs_weekday_max_temp_needs_both_groups():
    assert report.weekend_vs_weekday_max_temp(_max_days("2026-09-28", [10.0, 11.0])) is None
    assert report.weekend_vs_weekday_max_temp([]) is None


def test_stats_markdown_shows_weekend_temperature_line():
    rows = [
        {"date": r["date"], "temp_max_c": r["temp_max_c"], "temp_min_c": 5.0, "precip_mm": 0.0, "sunshine_h": 5.0}
        for r in _max_days("2026-09-28", [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0])
    ]
    md = report.stats_markdown(rows, [])
    assert "- Weekend vs. weekday max temperature: **21.0 °C** over 2 weekend days vs. 14.0 °C over 5 weekdays (+7.0 °C)" in md


def _rain_days(start: str, mms: list) -> list[dict]:
    d0 = date.fromisoformat(start)
    return [
        {"date": (d0 + timedelta(days=i)).isoformat(), "precip_mm": "" if v is None else v}
        for i, v in enumerate(mms)
    ]


def test_wettest_run_prefers_total_over_length():
    # a 3-day drizzle (1.5 mm) loses to a 2-day downpour (12 mm)
    rows = _rain_days("2026-10-01", [0.5, 0.5, 0.5, 0.0, 4.0, 8.0, 0.0])
    assert report.wettest_run(rows) == (12.0, 2, "2026-10-05", "2026-10-06")


def test_wettest_run_breaks_on_missing_values_and_gaps():
    rows = _rain_days("2026-10-01", [3.0, None, 3.0, 3.0])
    assert report.wettest_run(rows) == (6.0, 2, "2026-10-03", "2026-10-04")
    gap = [{"date": "2026-10-01", "precip_mm": 5.0}, {"date": "2026-10-03", "precip_mm": 4.0}]
    assert report.wettest_run(gap) == (5.0, 1, "2026-10-01", "2026-10-01")


def test_wettest_run_earliest_wins_ties_and_none_when_dry():
    rows = _rain_days("2026-10-01", [2.0, 0.0, 2.0])
    assert report.wettest_run(rows) == (2.0, 1, "2026-10-01", "2026-10-01")
    assert report.wettest_run(_rain_days("2026-10-01", [0.0, 0.0])) is None
    assert report.wettest_run([]) is None


def _min_days(start: str, temps: list) -> list[dict]:
    d0 = date.fromisoformat(start)
    return [
        {"date": (d0 + timedelta(days=i)).isoformat(), "temp_min_c": "" if v is None else v}
        for i, v in enumerate(temps)
    ]


def test_weekend_vs_weekday_min_temp_splits_and_skips_missing():
    # 2026-09-28 is a Monday: Mon..Fri, Sat (missing), Sun, Mon
    rows = _min_days("2026-09-28", [4.0, 6.0, 8.0, 10.0, 12.0, None, -1.0, 2.0])
    assert report.weekend_vs_weekday_min_temp(rows) == (-1.0, 1, 7.0, 6)


def test_weekend_vs_weekday_min_temp_needs_both_groups():
    assert report.weekend_vs_weekday_min_temp(_min_days("2026-10-03", [3.0, 4.0])) is None  # Sat + Sun only
    assert report.weekend_vs_weekday_min_temp([]) is None


def test_stats_markdown_shows_weekend_night_temperature_line():
    rows = [
        {"date": r["date"], "temp_max_c": 15.0, "temp_min_c": r["temp_min_c"], "precip_mm": 0.0, "sunshine_h": 5.0}
        for r in _min_days("2026-09-28", [5.0, 6.0, 7.0, 8.0, 9.0, 3.0, 4.0])
    ]
    md = report.stats_markdown(rows, [])
    assert (
        "- Weekend vs. weekday night (min) temperature: **3.5 °C** over 2 weekend days"
        " vs. 7.0 °C over 5 weekdays (-3.5 °C)"
    ) in md


def test_mildest_night_weekday_averages_and_skips_missing():
    # 2026-09-28 is a Monday; two weeks, second Wednesday missing
    temps = [5.0, 6.0, 9.0, 4.0, 3.0, 2.0, 1.0, 7.0, 6.0, None, 4.0, 3.0, 2.0, 1.0]
    # Monday (5 + 7) / 2 = 6.0, Wednesday 9.0 over a single day
    assert report.mildest_night_weekday(_min_days("2026-09-28", temps)) == ("Wednesday", 9.0, 1)


def test_mildest_night_weekday_ties_go_to_monday_and_zero_counts():
    rows = _min_days("2026-09-28", [-2.0, -3.0, -2.0])  # Mon, Tue, Wed
    assert report.mildest_night_weekday(rows) == ("Monday", -2.0, 1)
    assert report.mildest_night_weekday(_min_days("2026-09-28", [0.0])) == ("Monday", 0.0, 1)
    assert report.mildest_night_weekday(_min_days("2026-09-28", [None])) is None
    assert report.mildest_night_weekday([]) is None


def test_stats_markdown_shows_mildest_night_weekday_line():
    rows = [
        {"date": r["date"], "temp_max_c": 15.0, "temp_min_c": r["temp_min_c"], "precip_mm": 0.0, "sunshine_h": 5.0}
        for r in _min_days("2026-09-28", [5.0, 8.5, 7.0])
    ]
    md = report.stats_markdown(rows, [])
    assert "- Mildest nights by weekday: **Tuesday** (8.5 °C average min over 1 day)" in md


def test_longest_wet_run_intensity_uses_longest_run_not_wettest():
    # 3-day drizzle (1.0 + 2.0 + 3.0) beats a 2-day downpour on length
    rows = _rain_days("2026-10-01", [1.0, 2.0, 3.0, 0, 20.0, 10.0])
    total, per_day = report.longest_wet_run_intensity(rows)
    assert round(total, 6) == 6.0
    assert round(per_day, 6) == 2.0


def test_longest_wet_run_intensity_earliest_tie_and_none():
    rows = _rain_days("2026-10-01", [4.0, 0, 9.0])
    assert report.longest_wet_run_intensity(rows) == (4.0, 4.0)
    assert report.longest_wet_run_intensity(_rain_days("2026-10-01", [0, 0, None])) is None
    assert report.longest_wet_run_intensity([]) is None


def test_stats_markdown_shows_wet_run_intensity():
    rows = [
        {"date": r["date"], "temp_max_c": 15.0, "temp_min_c": 8.0, "precip_mm": r["precip_mm"], "sunshine_h": 5.0}
        for r in _rain_days("2026-10-01", [1.5, 2.5, 0.0])
    ]
    md = report.stats_markdown(rows, [])
    assert "- Longest wet run: **2 days** (2026-10-01 → 2026-10-02), 4.0 mm at 2.0 mm/day" in md


def test_coldest_day_weekday_averages_and_skips_missing():
    # 2026-09-28 is a Monday; two weeks, second Thursday missing
    temps = [15.0, 16.0, 14.0, 9.0, 18.0, 17.0, 16.0, 13.0, 16.0, 14.0, None, 18.0, 17.0, 16.0]
    # Monday (15 + 13) / 2 = 14.0, Wednesday 14.0, Thursday 9.0 over a single day
    assert report.coldest_day_weekday(_max_days("2026-09-28", temps)) == ("Thursday", 9.0, 1)


def test_coldest_day_weekday_ties_go_to_monday_and_none_when_empty():
    rows = _max_days("2026-09-28", [-1.0, 3.0, -1.0])  # Mon, Tue, Wed
    assert report.coldest_day_weekday(rows) == ("Monday", -1.0, 1)
    assert report.coldest_day_weekday(_max_days("2026-09-28", [None, None])) is None
    assert report.coldest_day_weekday([]) is None


def test_stats_markdown_shows_coldest_day_weekday():
    rows = [
        {"date": "2026-09-29", "temp_max_c": 12.5, "temp_min_c": 8.0, "precip_mm": 0.0, "sunshine_h": 5.0},
        {"date": "2026-09-30", "temp_max_c": 14.0, "temp_min_c": 7.0, "precip_mm": 0.0, "sunshine_h": 5.0},
    ]
    md = report.stats_markdown(rows, [])
    assert "- Coldest days by weekday: **Tuesday** (12.5 °C average max over 1 day)" in md


def test_wet_runs_keeps_only_long_spells_and_splits_on_gaps():
    rows = _rain_days("2026-10-01", [1.0, 2.0, 3.0, 0, 5.0, 5.0, None, 2.0, 2.0, 2.0, 2.0])
    assert report.wet_runs(rows) == [
        ("2026-10-01", "2026-10-03", 3, 6.0),
        ("2026-10-08", "2026-10-11", 4, 8.0),
    ]
    # a missing calendar day also ends a spell
    gap = [r for r in rows if r["date"] != "2026-10-02"]
    assert report.wet_runs(gap) == [("2026-10-08", "2026-10-11", 4, 8.0)]
    assert report.wet_runs(rows, min_days=2)[1] == ("2026-10-05", "2026-10-06", 2, 10.0)


def test_wet_run_trend_compares_latest_with_previous():
    rows = _rain_days("2026-10-01", [1.0, 2.0, 3.0, 0, 4.0, 4.0, 4.0])
    latest, prev, verdict = report.wet_run_trend(rows)
    assert latest == ("2026-10-05", "2026-10-07", 3, 12.0)
    assert prev == ("2026-10-01", "2026-10-03", 3, 6.0)
    assert verdict == "heavier"
    assert report.wet_run_trend(_rain_days("2026-10-01", [3.0, 3.0, 3.0, 0, 1.0, 1.0, 1.0]))[2] == "lighter"
    assert report.wet_run_trend(_rain_days("2026-10-01", [1.0, 1.0, 1.0, 0, 1.0, 1.0, 1.0]))[2] == "same"
    assert report.wet_run_trend(_rain_days("2026-10-01", [1.0, 1.0, 1.0])) is None


def test_stats_markdown_shows_wet_spell_trend():
    rows = [
        {"date": r["date"], "temp_max_c": 15.0, "temp_min_c": 8.0, "precip_mm": r["precip_mm"], "sunshine_h": 5.0}
        for r in _rain_days("2026-10-01", [1.0, 2.0, 3.0, 0, 4.0, 4.0, 4.0])
    ]
    md = report.stats_markdown(rows, [])
    assert (
        "- Wet spells of 3+ days: 2; latest **4.0 mm/day** over 3 days (2026-10-05 → 2026-10-07)"
        " vs. 2.0 mm/day over 3 days (2026-10-01 → 2026-10-03), heavier"
    ) in md
    one = report.stats_markdown(rows[:3], [])
    assert "- Wet spells of 3+ days: 1 so far, trend needs a second one" in one


def test_dry_runs_keeps_only_long_spells_and_splits_on_gaps_and_missing():
    rows = _rain_days("2026-10-01", [0, 0, 0, 1.0, 0, 0, None, 0, 0, 0, 0, 2.0])
    assert report.dry_runs(rows) == [
        ("2026-10-01", "2026-10-03", 3),
        ("2026-10-08", "2026-10-11", 4),
    ]
    # a missing calendar day also ends a spell
    gap = [r for r in rows if r["date"] != "2026-10-02"]
    assert report.dry_runs(gap) == [("2026-10-08", "2026-10-11", 4)]
    assert report.dry_runs(rows, min_days=2)[1] == ("2026-10-05", "2026-10-06", 2)
    # a spell still running on the newest day is included
    assert report.dry_runs(_rain_days("2026-10-01", [1.0, 0, 0, 0])) == [("2026-10-02", "2026-10-04", 3)]


def test_dry_run_trend_compares_latest_length_with_previous():
    latest, prev, verdict = report.dry_run_trend(_rain_days("2026-10-01", [0, 0, 0, 1.0, 0, 0, 0, 0]))
    assert latest == ("2026-10-05", "2026-10-08", 4)
    assert prev == ("2026-10-01", "2026-10-03", 3)
    assert verdict == "longer"
    assert report.dry_run_trend(_rain_days("2026-10-01", [0, 0, 0, 0, 1.0, 0, 0, 0]))[2] == "shorter"
    assert report.dry_run_trend(_rain_days("2026-10-01", [0, 0, 0, 1.0, 0, 0, 0]))[2] == "same"
    assert report.dry_run_trend(_rain_days("2026-10-01", [0, 0, 0])) is None


def test_stats_markdown_shows_dry_spell_trend():
    rows = [
        {"date": r["date"], "temp_max_c": 15.0, "temp_min_c": 8.0, "precip_mm": r["precip_mm"], "sunshine_h": 5.0}
        for r in _rain_days("2026-10-01", [0, 0, 0, 0, 1.0, 0, 0, 0])
    ]
    md = report.stats_markdown(rows, [])
    assert (
        "- Dry spells of 3+ days: 2 (lengths 4, 3); latest **3 days** (2026-10-06 → 2026-10-08)"
        " vs. 4 days (2026-10-01 → 2026-10-04), shorter"
    ) in md
    one = report.stats_markdown(rows[:4], [])
    assert "- Dry spells of 3+ days: 1 so far, trend needs a second one" in one


def _range_days(start: str, pairs: list) -> list[dict]:
    d0 = date.fromisoformat(start)
    return [
        {"date": (d0 + timedelta(days=i)).isoformat(), "temp_max_c": "" if hi is None else hi, "temp_min_c": "" if lo is None else lo}
        for i, (hi, lo) in enumerate(pairs)
    ]


def test_widest_range_weekday_averages_and_needs_both_values():
    # 2026-09-28 is a Monday; second week's Wednesday has no min, so it is skipped
    pairs = [(15, 10), (14, 9), (20, 8), (12, 10), (16, 6), (15, 10), (15, 10),
             (17, 10), (14, 9), (25, None), (12, 10), (16, 10), (15, 10), (15, 10)]
    # Monday (5 + 7) / 2 = 6.0, Wednesday 12 over one day, Friday (10 + 6) / 2 = 8.0
    assert report.widest_range_weekday(_range_days("2026-09-28", pairs)) == ("Wednesday", 12.0, 1)


def test_widest_range_weekday_ties_go_to_monday_and_none_when_empty():
    assert report.widest_range_weekday(_range_days("2026-09-28", [(10, 5), (9, 4)])) == ("Monday", 5.0, 1)
    assert report.widest_range_weekday(_range_days("2026-09-28", [(10, None), (None, 4)])) is None
    assert report.widest_range_weekday([]) is None


def test_stats_markdown_shows_widest_range_weekday():
    rows = [
        {"date": "2026-09-29", "temp_max_c": 18.0, "temp_min_c": 6.5, "precip_mm": 0.0, "sunshine_h": 5.0},
        {"date": "2026-09-30", "temp_max_c": 14.0, "temp_min_c": 7.0, "precip_mm": 0.0, "sunshine_h": 5.0},
    ]
    md = report.stats_markdown(rows, [])
    assert "- Widest day/night range by weekday: **Tuesday** (11.5 °C average max − min over 1 day)" in md


def test_dry_spell_sunshine_averages_sun_per_spell_and_skips_missing():
    rows = _rain_days("2026-10-01", [0, 0, 0, 1.0, 0, 0, 0, 0])
    sun = [6.0, 8.0, 10.0, 1.0, 4.0, None, 2.0, 3.0]
    for r, h in zip(rows, sun):
        r["sunshine_h"] = h
    assert report.dry_spell_sunshine(rows) == [
        ("2026-10-01", "2026-10-03", 3, 8.0),
        ("2026-10-05", "2026-10-08", 4, 3.0),  # the missing day is left out of the mean
    ]
    for r in rows[:3]:
        r["sunshine_h"] = None
    assert report.dry_spell_sunshine(rows)[0][3] is None
    assert report.dry_spell_sunshine(_rain_days("2026-10-01", [1.0, 0, 0])) == []


def test_stats_markdown_shows_dry_spell_sunshine():
    rows = [
        {"date": r["date"], "temp_max_c": 15.0, "temp_min_c": 8.0, "precip_mm": r["precip_mm"], "sunshine_h": h}
        for r, h in zip(_rain_days("2026-10-01", [0, 0, 0, 1.0, 0, 0, 0]), [6.0, 8.0, 10.0, 1.0, 4.0, 5.0, 6.0])
    ]
    md = report.stats_markdown(rows, [])
    assert "- Sunshine during dry spells (avg h/day): 2026-10-01 → 2026-10-03 8.0 h · 2026-10-05 → 2026-10-07 5.0 h" in md


def _spread_days(start: str, spreads: list) -> list[dict]:
    d0 = date.fromisoformat(start)
    return [
        {"date": (d0 + timedelta(days=i)).isoformat(), "temp_max_c": "" if s is None else 10.0 + s,
         "temp_min_c": 10.0, "precip_mm": 0.0, "sunshine_h": 5.0}
        for i, s in enumerate(spreads)
    ]


def test_weekly_range_trend_blocks_back_from_latest_day():
    # 17 days: 3 leftover days (dropped, under min_days), then two full weeks
    rows = _spread_days("2026-10-01", [9.0, 9.0, 9.0] + [8.0] * 7 + [4.0, 6.0, None, 5.0, 5.0, 5.0, 5.0])
    weeks = report.weekly_range_trend(rows)
    assert [(w[0], w[1]) for w in weeks] == [("2026-10-04", "2026-10-10"), ("2026-10-11", "2026-10-17")]
    assert weeks[0][2] == 8.0
    assert weeks[1][2] == 5.0  # the day without a max is skipped
    assert report.range_trend_verdict(weeks) == "narrowing"
    assert report.weekly_range_trend(rows, min_days=3)[0] == ("2026-09-27", "2026-10-03", 9.0)
    assert report.range_trend_verdict(report.weekly_range_trend(_spread_days("2026-10-01", [4.0] * 7 + [6.0] * 7))) == "widening"
    assert report.range_trend_verdict(report.weekly_range_trend(_spread_days("2026-10-01", [4.0] * 14))) == "flat"
    assert report.range_trend_verdict(report.weekly_range_trend(_spread_days("2026-10-01", [4.0] * 7))) is None
    assert report.weekly_range_trend([]) == []


def test_stats_markdown_shows_weekly_range_trend():
    md = report.stats_markdown(_spread_days("2026-10-01", [8.0] * 7 + [5.0] * 7), [])
    assert (
        "- Day/night range by week: 8.0 → 5.0 °C; latest week (2026-10-08 → 2026-10-14) **5.0 °C** vs. 8.0 °C in the first, narrowing"
        in md
    )
