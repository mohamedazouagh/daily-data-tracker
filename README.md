# daily-data-tracker

A small data pipeline that runs every day and builds its own dataset over time:

- **Weather in Breda** (max/min temperature, rain, sunshine) from [Open-Meteo](https://open-meteo.com/) (CC BY 4.0)
- **EUR exchange rates** (USD, GBP, CHF, TRY) from the ECB via [Frankfurter](https://www.frankfurter.app/)

Pure Python standard library for the pipeline; `pytest` for tests.

```bash
python -m tracker.run fetch            # store yesterday's data (safe to re-run)
python -m tracker.run fetch 2026-09-01 # backfill a specific day
python -m tracker.run report           # rebuild the stats below + chart
python -m pytest
```

## Max temperature, last 60 days

![Max temperature trend](data/temp_max.svg)

## Stats

<!-- stats:start -->
**Days tracked:** 4 weather · 3 FX

- Average max temperature: **22.6 °C**
- Warmest day: **26.2 °C** · Coldest max: **20.6 °C**
- Total rain: **2.0 mm** · Dry days: **2**
- Rain vs. sunshine correlation: **r = -0.82**

Last 7 days (Breda):

| Date | Max °C | Min °C | Rain mm | Sun h |
|---|---|---|---|---|
| 2026-09-29 | 26.2 | 15.5 | 0.1 | 10.65 |
| 2026-09-28 | 21.4 | 15.1 | 1.9 | 5.42 |
| 2026-09-27 | 22.1 | 10.6 | 0.0 | 11.0 |
| 2026-09-26 | 20.6 | 12.7 | 0.0 | 7.72 |

Latest EUR rates (2026-09-29): USD 1.1355 · GBP 0.85718 · CHF 0.9461 · TRY 55.6398

Change vs. 2026-09-28: USD -0.20% · GBP -0.08% · CHF -0.03% · TRY -0.17%

<!-- stats:end -->

## Roadmap

- [ ] Monthly summary notebook (pandas)
- [x] Rain vs. sunshine correlation
- [ ] Weekday vs. weekend exchange-rate gaps
- [x] Day-over-day % change for each EUR rate
- [ ] Rolling 7-day average temperature in the chart
- [ ] Biggest single-day FX move since tracking started
