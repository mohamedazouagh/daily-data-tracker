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
**Days tracked:** 18 weather · 12 FX

- Average max temperature: **20.0 °C**
- Warmest day: **26.2 °C** · Coldest max: **14.1 °C**
- Last 7 days vs. the 7 before (avg max): **17.3 °C** vs. 21.7 °C (-4.5 °C)
- Total rain: **28.3 mm** · Dry days: **9**
- Coldest night: **4.8 °C** on 2026-10-12
- First frost (min below 0 °C): none yet
- Warmest night: **17.8 °C** on 2026-09-30
- Largest day/night range: **13.4 °C** on 2026-09-25
- Sunniest day: **11.1 h** on 2026-09-25 · Average sunshine: **9.0 h/day**
- Wettest day: **8.1 mm** on 2026-10-07
- Rainiest week: **22.9 mm** (2026-10-05 → 2026-10-11)
- Longest dry streak: **5 days** (2026-10-02 → 2026-10-06)
- Longest warm streak (max > 20 °C): **7 days** (2026-09-25 → 2026-10-01)
- Wettest weekday so far: **Wednesday** (4.6 mm on average over 2 days)
- Sunniest weekday so far: **Sunday** (10.9 h on average over 3 days)
- Rain vs. sunshine correlation: **r = -0.63**

Last 7 days (Breda):

| Date | Max °C | Min °C | Rain mm | Sun h |
|---|---|---|---|---|
| 2026-10-12 | 16.8 | 4.8 | 0.0 | 10.57 |
| 2026-10-11 | 14.2 | 7.9 | 0.9 | 10.79 |
| 2026-10-10 | 14.1 | 9.2 | 4.4 | 9.74 |
| 2026-10-09 | 16.8 | 8.7 | 7.6 | 1.16 |
| 2026-10-08 | 15.1 | 10.8 | 1.9 | 10.96 |
| 2026-10-07 | 22.2 | 11.5 | 8.1 | 7.75 |
| 2026-10-06 | 21.6 | 10.8 | 0.0 | 11.0 |

Latest EUR rates (2026-10-12): USD 1.1181 · GBP 0.84478 · CHF 0.9312 · TRY 55.1635

Change vs. 2026-10-09: USD -0.22% · GBP -0.34% · CHF -0.01% · TRY +0.11%

Biggest single-day move since tracking started: CHF -1.67% on 2026-10-02

Longest calm USD stretch (no daily move above 0.5%): **4 business days** (2026-09-25 → 2026-09-30)

Weekend gaps vs. weekdays (avg absolute move):

- USD: **0.21%** over 3 gaps vs. 0.38% over 8 weekday moves (gaps smaller)
- GBP: **0.34%** over 3 gaps vs. 0.19% over 8 weekday moves (gaps larger)
- CHF: **0.19%** over 3 gaps vs. 0.46% over 8 weekday moves (gaps smaller)
- TRY: **0.13%** over 3 gaps vs. 0.34% over 8 weekday moves (gaps smaller)

<!-- stats:end -->

## Roadmap

- [ ] Monthly summary notebook (pandas)
- [x] Rain vs. sunshine correlation
- [x] Weekday vs. weekend exchange-rate gaps
- [x] Weekend-gap vs. weekday moves for GBP, CHF and TRY too
- [ ] Month-over-month change of each EUR rate once two month-ends are stored
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
- [x] Longest stretch without a USD/EUR move above 0.5%
- [x] Rainiest week (highest 7-day rolling rain total)
- [x] Week-over-week change in average max temperature
- [ ] Monthly averages table (max/min temperature, rain, sunshine) once a full month is stored
- [x] First autumn frost: earliest night with min temperature below 0 °C
- [ ] Count of frost nights per month once winter data comes in
- [x] Average weekday rain: which day of the week is wettest so far
- [x] Sunshine by weekday: which day of the week gets the most sun on average
- [ ] Dry-day share per weekday (how often each day of the week stays at 0 mm)
