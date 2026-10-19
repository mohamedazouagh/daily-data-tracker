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
**Days tracked:** 24 weather · 16 FX

- Average max temperature: **19.2 °C**
- Warmest day: **26.2 °C** · Coldest max: **11.6 °C**
- Last 7 days vs. the 7 before (avg max): **16.9 °C** vs. 17.8 °C (-0.9 °C)
- Total rain: **41.3 mm** · Dry days: **11**
- Coldest night: **4.8 °C** on 2026-10-12
- First frost (min below 0 °C): none yet
- Warmest night: **17.8 °C** on 2026-09-30
- Largest day/night range: **13.4 °C** on 2026-09-25
- Sunniest day: **11.1 h** on 2026-09-25 · Average sunshine: **8.8 h/day**
- Wettest day: **8.1 mm** on 2026-10-07
- Wettest day's share of all rain: **20%** (8.1 mm on 2026-10-07)
- Share of rain from the 3 wettest days: **52%** (2026-10-07 8.1 mm, 2026-10-09 7.6 mm, 2026-10-18 5.8 mm)
- Rain intensity (wet days only): **3.2 mm/day** over 13 wet days
- Rainiest week: **23.7 mm** (2026-10-07 → 2026-10-13)
- Longest dry streak: **5 days** (2026-10-02 → 2026-10-06)
- Current run: **3 wet days in a row** since 2026-10-16
- Longest warm streak (max > 20 °C): **7 days** (2026-09-25 → 2026-10-01)
- Wettest weekday so far: **Wednesday** (3.1 mm on average over 3 days)
- Sunniest weekday so far: **Sunday** (10.1 h on average over 4 days)
- Dry days by weekday: Mon 2/3 · Tue 1/3 · Wed 1/3 · Thu 1/3 · Fri 2/4 · Sat 2/4 · Sun 2/4
- Weekend vs. weekday rain: **1.7 mm/day** over 8 weekend days vs. 1.8 mm/day over 16 weekdays
- Weekend vs. weekday sunshine: **9.7 h/day** over 8 weekend days vs. 8.3 h/day over 16 weekdays
- Rain vs. sunshine correlation: **r = -0.60**

Last 7 days (Breda):

| Date | Max °C | Min °C | Rain mm | Sun h |
|---|---|---|---|---|
| 2026-10-18 | 11.6 | 6.5 | 5.8 | 7.48 |
| 2026-10-17 | 14.0 | 8.0 | 2.1 | 10.1 |
| 2026-10-16 | 17.8 | 11.9 | 4.3 | 5.12 |
| 2026-10-15 | 19.9 | 10.3 | 0.0 | 9.84 |
| 2026-10-14 | 17.3 | 9.5 | 0.0 | 10.6 |
| 2026-10-13 | 20.8 | 13.5 | 0.8 | 5.14 |
| 2026-10-12 | 16.8 | 4.8 | 0.0 | 10.57 |

Latest EUR rates (2026-10-16): USD 1.1253 · GBP 0.84385 · CHF 0.9272 · TRY 55.7328

Change vs. 2026-10-15: USD +0.40% · GBP -0.27% · CHF -0.35% · TRY +0.62%

Change since tracking started (2026-09-25): USD -1.32% · GBP -1.93% · CHF -1.83% · TRY -0.12%

Biggest single-day move since tracking started: CHF -1.67% on 2026-10-02

Best and worst 5-business-day move:

- USD: best **+0.42%** (2026-10-09 → 2026-10-16) · worst **-1.57%** (2026-09-30 → 2026-10-07)
- GBP: best **-0.10%** (2026-10-08 → 2026-10-15) · worst **-1.24%** (2026-09-28 → 2026-10-05)
- CHF: best **+0.37%** (2026-10-02 → 2026-10-09) · worst **-1.78%** (2026-09-30 → 2026-10-07)
- TRY: best **+1.14%** (2026-10-09 → 2026-10-16) · worst **-1.22%** (2026-09-30 → 2026-10-07)

Realised volatility (std. dev. of daily moves, 15 moves): USD 0.37% · GBP 0.21% · CHF 0.52% · TRY 0.37%

10-move volatility, first window → latest: USD 0.41% → 0.38% (steady) · GBP 0.21% → 0.23% (steady) · CHF 0.63% → 0.33% (calmer) · TRY 0.39% → 0.40% (steady)

Calmest → choppiest over the latest 10 moves: GBP 0.23% < CHF 0.33% < USD 0.38% < TRY 0.40% (calmest: **GBP**)

Longest calm USD stretch (no daily move above 0.5%): **8 business days** (2026-10-07 → 2026-10-16)

Weekend gaps vs. weekdays (avg absolute move):

- USD: **0.21%** over 3 gaps vs. 0.30% over 12 weekday moves (gaps smaller)
- GBP: **0.34%** over 3 gaps vs. 0.18% over 12 weekday moves (gaps larger)
- CHF: **0.19%** over 3 gaps vs. 0.38% over 12 weekday moves (gaps smaller)
- TRY: **0.13%** over 3 gaps vs. 0.31% over 12 weekday moves (gaps smaller)

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
- [x] Dry-day share per weekday (how often each day of the week stays at 0 mm)
- [x] Cumulative change of each EUR rate since the first stored day
- [x] Best and worst week for each EUR rate (largest 5-business-day move)
- [x] Realised volatility per EUR rate (standard deviation of daily % moves)
- [x] Rolling 10-day volatility per EUR rate to see whether markets are calming down
- [x] Volatility ranking: which currency has been the calmest over the latest 10 moves
- [ ] Volatility ranking history: how often each currency has been the calmest at month-end
- [x] Average rain on wet days only (rain intensity, ignoring dry days)
- [x] Heaviest-rain share: what fraction of all rain fell on the single wettest day
- [x] Share of rain from the 3 wettest days (how concentrated rainfall is overall)
- [x] Weekend vs. weekday rain: average mm on Saturdays/Sundays against Monday–Friday
- [x] Weekend vs. weekday sunshine: do Saturdays/Sundays get more sun than Monday–Friday
- [x] Current dry or wet run: how many days in a row the latest weather has lasted
- [ ] Weekend vs. weekday temperature: are Saturdays/Sundays warmer than Monday–Friday
- [ ] Longest wet run (consecutive days with rain) next to the longest dry streak
