"""Build the README stats block and a tiny SVG sparkline from the stored CSVs."""
from __future__ import annotations

from datetime import date, timedelta
from statistics import correlation, mean


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
            f"- Total rain: **{sum(rain):.1f} mm** · Dry days: **{sum(1 for r in rain if r == 0)}**",
        ]
        streak = longest_dry_streak(weather)
        if streak:
            lines.append(f"- Longest dry streak: {_streak_text(streak)}")
        warm = longest_warm_streak(weather)
        lines.append(
            f"- Longest warm streak (max > {WARM_THRESHOLD_C:.0f} °C): {_streak_text(warm)}"
            if warm
            else f"- Longest warm streak (max > {WARM_THRESHOLD_C:.0f} °C): none yet"
        )
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
        move = biggest_fx_move(fx)
        if move:
            code, day, pct = move
            lines += [f"Biggest single-day move since tracking started: {code.upper()} {pct:+.2f}% on {day}", ""]
    return "\n".join(lines)


START, END = "<!-- stats:start -->", "<!-- stats:end -->"


def replace_block(readme: str, block: str) -> str:
    head, _, rest = readme.partition(START)
    _, _, tail = rest.partition(END)
    return f"{head}{START}\n{block}\n{END}{tail}"
