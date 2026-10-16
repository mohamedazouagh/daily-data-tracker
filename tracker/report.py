"""Build the README stats block and a tiny SVG sparkline from the stored CSVs."""
from __future__ import annotations

from datetime import date, timedelta
from statistics import correlation, mean, stdev


def _floats(rows: list[dict], key: str) -> list[float]:
    return [float(r[key]) for r in rows if r.get(key) not in ("", None)]


def rain_sun_correlation(rows: list[dict]) -> float | None:
    """Pearson r between daily rain and sunshine hours.

    Only days with both values are used. Returns None with fewer than 3 such
    days or when either series is constant (r is undefined then).
    """
    pairs = [
        (float(r["precip_mm"]), float(r["sunshine_h"]))
        for r in rows
        if r.get("precip_mm") not in ("", None) and r.get("sunshine_h") not in ("", None)
    ]
    if len(pairs) < 3:
        return None
    rain, sun = zip(*pairs)
    if len(set(rain)) < 2 or len(set(sun)) < 2:
        return None
    return correlation(rain, sun)


FX_CODES = ("usd", "gbp", "chf", "try")


def fx_pct_changes(fx: list[dict]) -> dict[str, float]:
    """Percent change of each EUR rate between the last two stored business days.

    Currencies missing (or zero) on either day are left out. Returns {} with
    fewer than two rows.
    """
    if len(fx) < 2:
        return {}
    prev, last = fx[-2], fx[-1]
    out = {}
    for code in FX_CODES:
        a, b = prev.get(code), last.get(code)
        if a in ("", None) or b in ("", None) or float(a) == 0:
            continue
        out[code] = (float(b) - float(a)) / float(a) * 100
    return out


def fx_since_start(fx: list[dict]) -> dict[str, tuple[str, float]]:
    """Cumulative % change of each EUR rate from its first to its latest stored value.

    Per currency, the first and last rows with a usable (non-missing,
    non-zero) rate are compared, so a gap at the start of one series does not
    hide the others. Returns {code: (first date used, signed % change)} in
    FX_CODES order; currencies with fewer than two usable values are left out.
    """
    out: dict[str, tuple[str, float]] = {}
    for code in FX_CODES:
        usable = [(r["date"], v) for r in fx if (v := _value(r, code)) not in (None, 0)]
        if len(usable) < 2:
            continue
        (first_day, a), (_, b) = usable[0], usable[-1]
        out[code] = (first_day, (b - a) / a * 100)
    return out


def fx_best_worst_week(
    fx: list[dict], days: int = 5
) -> dict[str, tuple[tuple[str, str, float], tuple[str, str, float]]]:
    """Best and worst ``days``-business-day move of each EUR rate.

    Each stored row is compared with the row ``days`` positions later (stored
    rows are business days, so 5 rows ahead is one trading week). Windows
    with a missing or zero rate at either end are skipped. Returns
    {code: ((first, last, highest %), (first, last, lowest %))} in FX_CODES
    order; the earliest window wins ties and currencies without a full
    window are left out. With only rises (or only falls) both entries can
    have the same sign.
    """
    out = {}
    for code in FX_CODES:
        moves = []
        for start, end in zip(fx, fx[days:]):
            a, b = _value(start, code), _value(end, code)
            if a in (None, 0) or b is None:
                continue
            moves.append((start["date"], end["date"], (b - a) / a * 100))
        if moves:
            best = max(moves, key=lambda m: m[2])
            worst = min(moves, key=lambda m: m[2])
            out[code] = (best, worst)
    return out


def fx_volatility(fx: list[dict]) -> dict[str, tuple[float, int]]:
    """Realised volatility of each EUR rate: sample standard deviation of daily % moves.

    Every pair of consecutive stored rows (business days, so weekend gaps
    count as one move) with usable rates gives one move; pairs with a
    missing or zero rate are skipped. Returns {code: (stdev %, moves used)}
    in FX_CODES order; currencies with fewer than two moves are left out
    because a standard deviation needs at least two values.
    """
    out = {}
    for code in FX_CODES:
        moves = []
        for prev, cur in zip(fx, fx[1:]):
            a, b = _value(prev, code), _value(cur, code)
            if a in (None, 0) or b is None:
                continue
            moves.append((b - a) / a * 100)
        if len(moves) >= 2:
            out[code] = (stdev(moves), len(moves))
    return out


def biggest_fx_move(fx: list[dict]) -> tuple[str, str, float] | None:
    """Largest absolute day-over-day % move across all tracked currencies.

    Compares each stored business day with the one before it and returns
    (currency, date of the move, signed % change). Pairs with a missing or
    zero rate are skipped. Returns None when no pair can be compared.
    """
    best: tuple[str, str, float] | None = None
    for prev, cur in zip(fx, fx[1:]):
        for code in FX_CODES:
            a, b = prev.get(code), cur.get(code)
            if a in ("", None) or b in ("", None) or float(a) == 0:
                continue
            pct = (float(b) - float(a)) / float(a) * 100
            if best is None or abs(pct) > abs(best[2]):
                best = (code, cur["date"], pct)
    return best


def _value(row: dict, key: str) -> float | None:
    v = row.get(key)
    return None if v in ("", None) else float(v)


def _longest_run(rows: list[dict], hit) -> tuple[int, str, str] | None:
    """Longest run of consecutive calendar days where ``hit(row)`` is true.

    Returns (length, first date, last date). Gaps in the stored dates break a
    run. Earliest run wins ties. Returns None when no row matches.
    """
    best: tuple[int, str, str] | None = None
    run_len, run_start, prev_day = 0, "", None
    for r in sorted(rows, key=lambda r: r["date"]):
        day = date.fromisoformat(r["date"])
        ok = hit(r)
        if ok and run_len and prev_day == day - timedelta(days=1):
            run_len += 1
        elif ok:
            run_len, run_start = 1, r["date"]
        else:
            run_len = 0
        if ok and (best is None or run_len > best[0]):
            best = (run_len, run_start, r["date"])
        prev_day = day
    return best


def longest_dry_streak(rows: list[dict]) -> tuple[int, str, str] | None:
    """Longest run of consecutive calendar days with 0 mm of rain.

    Days with missing rain values or gaps in the stored dates break a streak.
    """
    return _longest_run(rows, lambda r: _value(r, "precip_mm") == 0)


WARM_THRESHOLD_C = 20.0


def longest_warm_streak(rows: list[dict], threshold: float = WARM_THRESHOLD_C) -> tuple[int, str, str] | None:
    """Longest run of consecutive days whose max temperature is above ``threshold``.

    Strictly above: a day at exactly the threshold does not count. Missing
    values and date gaps break a streak.
    """

    def warm(r: dict) -> bool:
        t = _value(r, "temp_max_c")
        return t is not None and t > threshold

    return _longest_run(rows, warm)


def coldest_night(rows: list[dict]) -> tuple[str, float] | None:
    """Day with the lowest minimum temperature as (date, temp_min_c).

    Rows without a min temperature are skipped; the earliest date wins ties.
    Returns None when no row has a value.
    """
    best: tuple[str, float] | None = None
    for r in sorted(rows, key=lambda r: r["date"]):
        t = _value(r, "temp_min_c")
        if t is not None and (best is None or t < best[1]):
            best = (r["date"], t)
    return best


def warmest_night(rows: list[dict]) -> tuple[str, float] | None:
    """Day with the highest minimum temperature as (date, temp_min_c).

    Mirror of ``coldest_night``: rows without a min temperature are skipped,
    the earliest date wins ties, and None is returned when no row has a value.
    """
    best: tuple[str, float] | None = None
    for r in sorted(rows, key=lambda r: r["date"]):
        t = _value(r, "temp_min_c")
        if t is not None and (best is None or t > best[1]):
            best = (r["date"], t)
    return best


def first_frost(rows: list[dict]) -> tuple[str, float] | None:
    """Earliest night with a minimum temperature below 0 °C, as (date, temp_min_c).

    Strictly below zero: a night at exactly 0.0 °C is not frost. Rows without
    a min temperature are skipped. Returns None when no frost night is stored.
    """
    for r in sorted(rows, key=lambda r: r["date"]):
        t = _value(r, "temp_min_c")
        if t is not None and t < 0:
            return r["date"], t
    return None


def largest_daily_range(rows: list[dict]) -> tuple[str, float] | None:
    """Day with the biggest gap between max and min temperature, as (date, range °C).

    Rows missing either value are skipped; the earliest date wins ties.
    Returns None when no row has both values.
    """
    best: tuple[str, float] | None = None
    for r in sorted(rows, key=lambda r: r["date"]):
        hi, lo = _value(r, "temp_max_c"), _value(r, "temp_min_c")
        if hi is None or lo is None:
            continue
        span = round(hi - lo, 1)
        if best is None or span > best[1]:
            best = (r["date"], span)
    return best


def sunshine_summary(rows: list[dict]) -> tuple[str, float, float] | None:
    """Sunniest day and the average daily sunshine, as (date, hours, mean hours).

    Rows without a sunshine value are skipped; the earliest date wins ties.
    Returns None when no row has a value.
    """
    best: tuple[str, float] | None = None
    hours: list[float] = []
    for r in sorted(rows, key=lambda r: r["date"]):
        h = _value(r, "sunshine_h")
        if h is None:
            continue
        hours.append(h)
        if best is None or h > best[1]:
            best = (r["date"], h)
    if best is None:
        return None
    return best[0], best[1], mean(hours)


def wettest_day(rows: list[dict]) -> tuple[str, float] | None:
    """Day with the most rain as (date, precip_mm).

    Rows without a rain value are skipped; the earliest date wins ties.
    Returns None when no stored day had any rain (0 mm everywhere is not a
    "wettest day").
    """
    best: tuple[str, float] | None = None
    for r in sorted(rows, key=lambda r: r["date"]):
        mm = _value(r, "precip_mm")
        if mm is not None and mm > 0 and (best is None or mm > best[1]):
            best = (r["date"], mm)
    return best


def wet_day_intensity(rows: list[dict]) -> tuple[float, int] | None:
    """Average rain on wet days only, as (mean mm per wet day, wet days counted).

    A wet day has more than 0 mm; dry days and rows without a rain value are
    ignored, so a long dry spell does not dilute how heavy the rain is when
    it does fall. Returns None until at least one wet day is stored.
    """
    wet = [mm for r in rows if (mm := _value(r, "precip_mm")) is not None and mm > 0]
    if not wet:
        return None
    return mean(wet), len(wet)


def heaviest_rain_share(rows: list[dict]) -> tuple[str, float, float] | None:
    """Share of all stored rain that fell on the single wettest day.

    Returns (date of the wettest day, its mm, % of the total rain). Rows
    without a rain value are skipped; the earliest date wins ties. Returns
    None while no rain has been recorded (a share of 0 mm is undefined).
    """
    wet = wettest_day(rows)
    if wet is None:
        return None
    total = sum(mm for r in rows if (mm := _value(r, "precip_mm")) is not None)
    return wet[0], wet[1], wet[1] / total * 100


def rainiest_week(rows: list[dict], window: int = 7) -> tuple[str, str, float] | None:
    """Highest rain total over ``window`` consecutive calendar days, as (first, last, mm).

    Only windows where every day is stored with a rain value count, so a gap
    or a missing value never makes a short stretch look like a full week.
    The earliest window wins ties. Returns None when no full window exists.
    """
    by_day = {
        date.fromisoformat(r["date"]): mm for r in rows if (mm := _value(r, "precip_mm")) is not None
    }
    best: tuple[str, str, float] | None = None
    for start in sorted(by_day):
        days = [start + timedelta(days=i) for i in range(window)]
        if not all(d in by_day for d in days):
            continue
        total = round(sum(by_day[d] for d in days), 1)
        if best is None or total > best[2]:
            best = (days[0].isoformat(), days[-1].isoformat(), total)
    return best


def week_over_week_max(rows: list[dict]) -> tuple[float, float, float] | None:
    """Average max temperature of the last 7 calendar days vs. the 7 before.

    Windows are anchored on the latest stored date (that day and the six
    before it, then the seven days before those), so gaps do not shift them.
    Returns (this week's mean, previous week's mean, difference), or None when
    either window has no max temperature yet.
    """
    temps = {
        date.fromisoformat(r["date"]): t for r in rows if (t := _value(r, "temp_max_c")) is not None
    }
    if not temps:
        return None
    latest = max(temps)
    this_week = [t for d, t in temps.items() if 0 <= (latest - d).days < 7]
    prev_week = [t for d, t in temps.items() if 7 <= (latest - d).days < 14]
    if not this_week or not prev_week:
        return None
    a, b = mean(this_week), mean(prev_week)
    return a, b, a - b


def calmest_fx_stretch(
    fx: list[dict], code: str = "usd", threshold: float = 0.5
) -> tuple[int, str, str] | None:
    """Longest run of stored business days where ``code`` never moved more than ``threshold`` %.

    A stretch is a sequence of consecutive stored rows in which every
    day-over-day change is at most ``threshold`` percent in absolute value.
    Its length counts the rows (business days) in it, so two rows with a calm
    move between them is a stretch of 2. A missing or zero rate breaks the
    stretch. Returns (days, first date, last date), earliest stretch wins
    ties, or None when no two consecutive rows can be compared calmly.
    """
    best: tuple[int, str, str] | None = None
    run_len, run_start = 0, ""
    for prev, cur in zip(fx, fx[1:]):
        a, b = _value(prev, code), _value(cur, code)
        calm = a not in (None, 0) and b is not None and abs((b - a) / a * 100) <= threshold
        if not calm:
            run_len = 0
            continue
        if run_len == 0:
            run_len, run_start = 2, prev["date"]
        else:
            run_len += 1
        if best is None or run_len > best[0]:
            best = (run_len, run_start, cur["date"])
    return best


def weekend_gap_moves(fx: list[dict], code: str = "usd") -> tuple[float, int, float, int] | None:
    """Average absolute % move of ``code`` across weekend gaps vs. back-to-back business days.

    A pair of consecutive stored rows whose dates are more than one day apart
    (e.g. Friday -> Monday) is a gap move; a pair exactly one day apart is a
    plain daily move. Pairs with a missing or zero rate are skipped. Returns
    (mean gap move %, gap pairs, mean daily move %, daily pairs), or None
    until both kinds have at least one pair.
    """
    gaps: list[float] = []
    daily: list[float] = []
    for prev, cur in zip(fx, fx[1:]):
        a, b = _value(prev, code), _value(cur, code)
        if a in (None, 0) or b is None:
            continue
        move = abs((b - a) / a * 100)
        days = (date.fromisoformat(cur["date"]) - date.fromisoformat(prev["date"])).days
        (gaps if days > 1 else daily).append(move)
    if not gaps or not daily:
        return None
    return mean(gaps), len(gaps), mean(daily), len(daily)


def weekend_gap_all(fx: list[dict]) -> dict[str, tuple[float, int, float, int]]:
    """``weekend_gap_moves`` for every tracked currency, in FX_CODES order.

    Currencies without both a gap pair and a daily pair yet are left out.
    """
    out = {}
    for code in FX_CODES:
        res = weekend_gap_moves(fx, code)
        if res is not None:
            out[code] = res
    return out


def _gap_verdict(gap: float, daily: float) -> str:
    """Short label comparing the mean gap move with the mean daily move."""
    if daily == 0:
        return "weekdays flat" if gap > 0 else "no movement"
    ratio = gap / daily
    if ratio >= 1.2:
        return "gaps larger"
    if ratio <= 1 / 1.2:
        return "gaps smaller"
    return "about the same"


WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def wettest_weekday(rows: list[dict]) -> tuple[str, float, int] | None:
    """Day of the week with the highest average rain, as (weekday, mean mm, days counted).

    Every stored day with a rain value counts towards its weekday's average,
    dry days included. Ties go to the earlier weekday (Monday first). Returns
    None when no day has a rain value or no rain has fallen at all.
    """
    by_weekday: dict[int, list[float]] = {}
    for r in rows:
        mm = _value(r, "precip_mm")
        if mm is not None:
            by_weekday.setdefault(date.fromisoformat(r["date"]).weekday(), []).append(mm)
    if not by_weekday:
        return None
    best_day = max(sorted(by_weekday), key=lambda d: mean(by_weekday[d]))
    avg = mean(by_weekday[best_day])
    if avg == 0:
        return None
    return WEEKDAYS[best_day], avg, len(by_weekday[best_day])


def sunniest_weekday(rows: list[dict]) -> tuple[str, float, int] | None:
    """Day of the week with the most sunshine on average, as (weekday, mean hours, days counted).

    Every stored day with a sunshine value counts towards its weekday's
    average, overcast days (0 h) included. Ties go to the earlier weekday
    (Monday first). Returns None when no day has a sunshine value or no sun
    has been recorded at all.
    """
    by_weekday: dict[int, list[float]] = {}
    for r in rows:
        h = _value(r, "sunshine_h")
        if h is not None:
            by_weekday.setdefault(date.fromisoformat(r["date"]).weekday(), []).append(h)
    if not by_weekday:
        return None
    best_day = max(sorted(by_weekday), key=lambda d: mean(by_weekday[d]))
    avg = mean(by_weekday[best_day])
    if avg == 0:
        return None
    return WEEKDAYS[best_day], avg, len(by_weekday[best_day])


def dry_share_by_weekday(rows: list[dict]) -> dict[str, tuple[int, int]]:
    """How often each day of the week stayed dry, as {weekday: (dry days, days counted)}.

    A day counts when it has a rain value; it is dry at exactly 0 mm. Keys
    follow calendar order (Monday first) and weekdays with no stored rain
    value are left out, so a missing Tuesday never shows up as 0/0.
    """
    counts: dict[int, list[int]] = {}
    for r in rows:
        mm = _value(r, "precip_mm")
        if mm is None:
            continue
        c = counts.setdefault(date.fromisoformat(r["date"]).weekday(), [0, 0])
        c[1] += 1
        if mm == 0:
            c[0] += 1
    return {WEEKDAYS[d]: (counts[d][0], counts[d][1]) for d in sorted(counts)}


def _streak_text(streak: tuple[int, str, str]) -> str:
    n, first, last = streak
    span = first if n == 1 else f"{first} → {last}"
    return f"**{n} day{'s' if n != 1 else ''}** ({span})"


def rolling_mean(values: list[float], window: int = 7) -> list[float | None]:
    """Trailing mean over ``window`` values, aligned with the input.

    The first ``window - 1`` positions have no full window and are None.
    """
    if window < 1:
        raise ValueError("window must be >= 1")
    out: list[float | None] = []
    for i in range(len(values)):
        out.append(mean(values[i - window + 1 : i + 1]) if i >= window - 1 else None)
    return out


def sparkline_svg(
    values: list[float], width: int = 600, height: int = 120, overlay: list[float | None] | None = None
) -> str:
    """SVG line chart of ``values``; ``overlay`` (same length) is drawn dashed on the same scale."""
    if len(values) < 2:
        values = values * 2 if values else [0.0, 0.0]
        overlay = None
    if overlay and len(overlay) != len(values):
        overlay = None
    # Scale over both series: averages can include days cropped from the chart.
    scaled = values + [v for v in (overlay or []) if v is not None]
    lo, hi = min(scaled), max(scaled)
    span = (hi - lo) or 1.0
    step = width / (len(values) - 1)

    def point(i: int, v: float) -> str:
        return f"{i * step:.1f},{height - 10 - (v - lo) / span * (height - 20):.1f}"

    pts = " ".join(point(i, v) for i, v in enumerate(values))
    avg = ""
    if overlay:
        avg_pts = [point(i, v) for i, v in enumerate(overlay) if v is not None]
        if len(avg_pts) >= 2:
            avg = (
                f'<polyline fill="none" stroke="#0969da" stroke-width="2" '
                f'stroke-dasharray="6 4" points="{" ".join(avg_pts)}"/>'
                f'<text x="{width - 6}" y="16" text-anchor="end" font-family="sans-serif" '
                f'font-size="12" fill="#0969da">7-day avg</text>'
            )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
        f'<rect width="100%" height="100%" fill="#ffffff"/>'
        f'<polyline fill="none" stroke="#2da44e" stroke-width="2.5" points="{pts}"/>'
        f"{avg}"
        f'<text x="6" y="16" font-family="sans-serif" font-size="12" fill="#57606a">max {hi:.1f}</text>'
        f'<text x="6" y="{height - 2}" font-family="sans-serif" font-size="12" fill="#57606a">min {lo:.1f}</text>'
        "</svg>\n"
    )


def stats_markdown(weather: list[dict], fx: list[dict]) -> str:
    lines = [f"**Days tracked:** {len(weather)} weather · {len(fx)} FX", ""]
    if weather:
        tmax = _floats(weather, "temp_max_c")
        rain = _floats(weather, "precip_mm")
        lines += [
            f"- Average max temperature: **{mean(tmax):.1f} °C**",
            f"- Warmest day: **{max(tmax):.1f} °C** · Coldest max: **{min(tmax):.1f} °C**",
        ]
        wow = week_over_week_max(weather)
        if wow:
            lines.append(
                f"- Last 7 days vs. the 7 before (avg max): **{wow[0]:.1f} °C** vs. {wow[1]:.1f} °C ({wow[2]:+.1f} °C)"
            )
        lines += [
            f"- Total rain: **{sum(rain):.1f} mm** · Dry days: **{sum(1 for r in rain if r == 0)}**",
        ]
        night = coldest_night(weather)
        if night:
            lines.append(f"- Coldest night: **{night[1]:.1f} °C** on {night[0]}")
        frost = first_frost(weather)
        lines.append(
            f"- First frost: **{frost[1]:.1f} °C** on {frost[0]}" if frost else "- First frost (min below 0 °C): none yet"
        )
        mild = warmest_night(weather)
        if mild:
            lines.append(f"- Warmest night: **{mild[1]:.1f} °C** on {mild[0]}")
        swing = largest_daily_range(weather)
        if swing:
            lines.append(f"- Largest day/night range: **{swing[1]:.1f} °C** on {swing[0]}")
        sun = sunshine_summary(weather)
        if sun:
            lines.append(f"- Sunniest day: **{sun[1]:.1f} h** on {sun[0]} · Average sunshine: **{sun[2]:.1f} h/day**")
        wet = wettest_day(weather)
        lines.append(f"- Wettest day: **{wet[1]:.1f} mm** on {wet[0]}" if wet else "- Wettest day: no rain recorded yet")
        share = heaviest_rain_share(weather)
        if share:
            lines.append(f"- Wettest day's share of all rain: **{share[2]:.0f}%** ({share[1]:.1f} mm on {share[0]})")
        heavy = wet_day_intensity(weather)
        if heavy:
            lines.append(
                f"- Rain intensity (wet days only): **{heavy[0]:.1f} mm/day** over {heavy[1]} wet day{'s' if heavy[1] != 1 else ''}"
            )
        week = rainiest_week(weather)
        lines.append(
            f"- Rainiest week: **{week[2]:.1f} mm** ({week[0]} → {week[1]})"
            if week
            else "- Rainiest week: needs 7 consecutive days"
        )
        streak = longest_dry_streak(weather)
        if streak:
            lines.append(f"- Longest dry streak: {_streak_text(streak)}")
        warm = longest_warm_streak(weather)
        lines.append(
            f"- Longest warm streak (max > {WARM_THRESHOLD_C:.0f} °C): {_streak_text(warm)}"
            if warm
            else f"- Longest warm streak (max > {WARM_THRESHOLD_C:.0f} °C): none yet"
        )
        wd = wettest_weekday(weather)
        if wd:
            lines.append(f"- Wettest weekday so far: **{wd[0]}** ({wd[1]:.1f} mm on average over {wd[2]} day{'s' if wd[2] != 1 else ''})")
        sd = sunniest_weekday(weather)
        if sd:
            lines.append(f"- Sunniest weekday so far: **{sd[0]}** ({sd[1]:.1f} h on average over {sd[2]} day{'s' if sd[2] != 1 else ''})")
        dry = dry_share_by_weekday(weather)
        if dry:
            parts = " · ".join(f"{day[:3]} {d}/{n}" for day, (d, n) in dry.items())
            lines.append(f"- Dry days by weekday: {parts}")
        r = rain_sun_correlation(weather)
        lines.append(
            f"- Rain vs. sunshine correlation: **r = {r:+.2f}**"
            if r is not None
            else "- Rain vs. sunshine correlation: not enough varied days yet"
        )
        lines += [
            "",
            "Last 7 days (Breda):",
            "",
            "| Date | Max °C | Min °C | Rain mm | Sun h |",
            "|---|---|---|---|---|",
        ]
        for r in weather[-7:][::-1]:
            lines.append(
                f"| {r['date']} | {r['temp_max_c']} | {r['temp_min_c']} | {r['precip_mm']} | {r['sunshine_h']} |"
            )
        lines.append("")
    if fx:
        last = fx[-1]
        lines += [
            f"Latest EUR rates ({last['date']}): USD {last['usd']} · GBP {last['gbp']} · CHF {last['chf']} · TRY {last['try']}",
            "",
        ]
        changes = fx_pct_changes(fx)
        if changes:
            parts = " · ".join(f"{code.upper()} {pct:+.2f}%" for code, pct in changes.items())
            lines += [f"Change vs. {fx[-2]['date']}: {parts}", ""]
        since = fx_since_start(fx)
        if since:
            starts = {day for day, _ in since.values()}
            if len(starts) == 1:
                parts = " · ".join(f"{code.upper()} {pct:+.2f}%" for code, (_, pct) in since.items())
                lines += [f"Change since tracking started ({starts.pop()}): {parts}", ""]
            else:
                parts = " · ".join(f"{code.upper()} {pct:+.2f}% (from {day})" for code, (day, pct) in since.items())
                lines += [f"Change since tracking started: {parts}", ""]
        move = biggest_fx_move(fx)
        if move:
            code, day, pct = move
            lines += [f"Biggest single-day move since tracking started: {code.upper()} {pct:+.2f}% on {day}", ""]
        weeks = fx_best_worst_week(fx)
        if weeks:
            lines += ["Best and worst 5-business-day move:", ""]
            for code, ((b1, b2, bp), (w1, w2, wp)) in weeks.items():
                lines.append(f"- {code.upper()}: best **{bp:+.2f}%** ({b1} → {b2}) · worst **{wp:+.2f}%** ({w1} → {w2})")
            lines.append("")
        vol = fx_volatility(fx)
        if vol:
            parts = " · ".join(f"{code.upper()} {sd:.2f}%" for code, (sd, _) in vol.items())
            n_moves = max(n for _, n in vol.values())
            lines += [f"Realised volatility (std. dev. of daily moves, {n_moves} moves): {parts}", ""]
        calm = calmest_fx_stretch(fx)
        if calm:
            n, first, last_day = calm
            lines += [
                f"Longest calm USD stretch (no daily move above 0.5%): **{n} business days** ({first} → {last_day})",
                "",
            ]
        gaps = weekend_gap_all(fx)
        if gaps:
            lines += ["Weekend gaps vs. weekdays (avg absolute move):", ""]
            for code, (g, gn, d, dn) in gaps.items():
                lines.append(
                    f"- {code.upper()}: **{g:.2f}%** over {gn} gap{'s' if gn != 1 else ''}"
                    f" vs. {d:.2f}% over {dn} weekday move{'s' if dn != 1 else ''}"
                    f" ({_gap_verdict(g, d)})"
                )
            lines.append("")
    return "\n".join(lines)


START, END = "<!-- stats:start -->", "<!-- stats:end -->"


def replace_block(readme: str, block: str) -> str:
    head, _, rest = readme.partition(START)
    _, _, tail = rest.partition(END)
    return f"{head}{START}\n{block}\n{END}{tail}"
