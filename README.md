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

Solid green: daily max · dashed blue: trailing 7-day average (appears once 7 days are stored).

![Max temperature trend](data/temp_max.svg)

## Stats

<!-- stats:start -->
**Days tracked:** 12 weather · 8 FX

- Average max temperature: **21.7 °C**
- Warmest day: **26.2 °C** · Coldest max: **19.5 °C**
- Total rain: **5.4 mm** · Dry days: **8**
- Coldest night: **7.6 °C** on 2026-10-05
- Warmest night: **17.8 °C** on 2026-09-30
- Largest day/night range: **13.4 °C** on 2026-09-25
- Sunniest day: **11.1 h** on 2026-09-25 · Average sunshine: **9.2 h/day**
- Wettest day: **2.2 mm** on 2026-10-01
- Longest dry streak: **5 days** (2026-10-02 → 2026-10-06)
- Longest warm streak (max > 20 °C): **7 days** (2026-09-25 → 2026-10-01)
- Rain vs. sunshine correlation: **r = -0.73**

Last 7 days (Breda):

| Date | Max °C | Min °C | Rain mm | Sun h |
|---|---|---|---|---|
| 2026-10-06 | 21.6 | 10.8 | 0.0 | 11.0 |
| 2026-10-05 | 20.8 | 7.6 | 0.0 | 9.83 |
| 2026-10-04 | 20.2 | 9.0 | 0.0 | 11.0 |
| 2026-10-03 | 19.7 | 7.9 | 0.0 | 9.49 |
| 2026-10-02 | 19.5 | 10.8 | 0.0 | 9.65 |
| 2026-10-01 | 21.0 | 14.4 | 2.2 | 8.27 |
| 2026-09-30 | 24.8 | 17.8 | 1.2 | 5.74 |

Latest EUR rates (2026-10-06): USD 1.1269 · GBP 0.8488 · CHF 0.9359 · TRY 55.4196

Change vs. 2026-10-05: USD +0.58% · GBP +0.19% · CHF +0.52% · TRY +0.62%

Biggest single-day move since tracking started: CHF -1.67% on 2026-10-02

<!-- stats:end -->

## Roadmap

- [ ] Monthly summary notebook (pandas)
- [x] Rain vs. sunshine correlation
- [ ] Weekday vs. weekend exchange-rate gaps
- [x] Day-over-day % change for each EUR rate
- [x] Rolling 7-day average temperature in the chart
- [x] Biggest single-day FX move since tracking started
- [x] Longest dry-day streak in Breda
- [x] Longest warm streak (max temperature above 20 °C)
- [x] Coldest night (lowest min temperature) and its date
- [x] Largest day/night temperature range (max − min) and its date
- [x] Sunniest day and average daily sunshine hours
- [x] Wettest day (most rain) and its date
- [x] Warmest night (highest min temperature) and its date
- [ ] Longest stretch without a USD/EUR move above 0.5%
- [ ] Rainiest week (highest 7-day rolling rain total)
- [ ] Week-over-week change in average max temperature
