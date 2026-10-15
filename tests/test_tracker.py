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
