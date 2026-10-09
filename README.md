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
**Days tracked:** 14 weather · 10 FX

- Average max temperature: **21.2 °C**
- Warmest day: **26.2 °C** · Coldest max: **15.1 °C**
- Last 7 days vs. the 7 before (avg max): **19.9 °C** vs. 22.6 °C (-2.7 °C)
- Total rain: **15.4 mm** · Dry days: **8**
- Coldest night: **7.6 °C** on 2026-10-05
- Warmest night: **17.8 °C** on 2026-09-30
- Largest day/night range: **13.4 °C** on 2026-09-25
- Sunniest day: **11.1 h** on 2026-09-25 · Average sunshine: **9.3 h/day**
- Wettest day: **8.1 mm** on 2026-10-07
- Rainiest week: **10.3 mm** (2026-10-01 → 2026-10-07)
- Longest dry streak: **5 days** (2026-10-02 → 2026-10-06)
- Longest warm streak (max > 20 °C): **7 days** (2026-09-25 → 2026-10-01)
- Rain vs. sunshine correlation: **r = -0.40**

Last 7 days (Breda):

| Date | Max °C | Min °C | Rain mm | Sun h |
|---|---|---|---|---|
| 2026-10-08 | 15.1 | 10.8 | 1.9 | 10.96 |
| 2026-10-07 | 22.2 | 11.5 | 8.1 | 7.75 |
| 2026-10-06 | 21.6 | 10.8 | 0.0 | 11.0 |
| 2026-10-05 | 20.8 | 7.6 | 0.0 | 9.83 |
| 2026-10-04 | 20.2 | 9.0 | 0.0 | 11.0 |
| 2026-10-03 | 19.7 | 7.9 | 0.0 | 9.49 |
| 2026-10-02 | 19.5 | 10.8 | 0.0 | 9.65 |

Latest EUR rates (2026-10-08): USD 1.1186 · GBP 0.84698 · CHF 0.9326 · TRY 55.0523

Change vs. 2026-10-07: USD +0.08% · GBP +0.06% · CHF +0.18% · TRY +0.13%

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
- [x] Rainiest week (highest 7-day rolling rain total)
- [x] Week-over-week change in average max temperature
- [ ] Monthly averages table (max/min temperature, rain, sunshine) once a full month is stored
- [ ] First autumn frost: earliest night with min temperature below 0 °C
