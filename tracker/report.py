"""Build the README stats block and a tiny SVG sparkline from the stored CSVs."""
from __future__ import annotations

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


def sparkline_svg(values: list[float], width: int = 600, height: int = 120) -> str:
    if len(values) < 2:
        values = values * 2 if values else [0.0, 0.0]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    step = width / (len(values) - 1)
    pts = " ".join(
        f"{i * step:.1f},{height - 10 - (v - lo) / span * (height - 20):.1f}"
        for i, v in enumerate(values)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
        f'<rect width="100%" height="100%" fill="#ffffff"/>'
        f'<polyline fill="none" stroke="#2da44e" stroke-width="2.5" points="{pts}"/>'
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
    return "\n".join(lines)


START, END = "<!-- stats:start -->", "<!-- stats:end -->"


def replace_block(readme: str, block: str) -> str:
    head, _, rest = readme.partition(START)
    _, _, tail = rest.partition(END)
    return f"{head}{START}\n{block}\n{END}{tail}"
