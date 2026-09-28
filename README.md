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
**Days tracked:** 2 weather · 1 FX

- Average max temperature: **21.4 °C**
- Warmest day: **22.1 °C** · Coldest max: **20.6 °C**
- Total rain: **0.0 mm** · Dry days: **2**

Last 7 days (Breda):

| Date | Max °C | Min °C | Rain mm | Sun h |
|---|---|---|---|---|
| 2026-09-27 | 22.1 | 10.6 | 0.0 | 11.0 |
| 2026-09-26 | 20.6 | 12.7 | 0.0 | 7.72 |

Latest EUR rates (2026-09-25): USD 1.1403 · GBP 0.86045 · CHF 0.9445 · TRY 55.7975

<!-- stats:end -->

## Roadmap

- [ ] Monthly summary notebook (pandas)
- [ ] Rain vs. sunshine correlation
- [ ] Weekday vs. weekend exchange-rate gaps
