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
**Days tracked:** 30 weather · 21 FX

- Average max temperature: **18.0 °C**
- Warmest day: **26.2 °C** · Coldest max: **11.6 °C**
- Last 7 days vs. the 7 before (avg max): **13.0 °C** vs. 17.3 °C (-4.3 °C)
- Total rain: **98.5 mm** · Dry days: **11**
- Coldest night: **4.8 °C** on 2026-10-12
- First frost (min below 0 °C): none yet
- Warmest night: **17.8 °C** on 2026-09-30
- Largest day/night range: **13.4 °C** on 2026-09-25
- Sunniest day: **11.1 h** on 2026-09-25 · Average sunshine: **8.1 h/day**
- Wettest day: **28.7 mm** on 2026-10-23
- Wettest day's share of all rain: **29%** (28.7 mm on 2026-10-23)
- Share of rain from the 3 wettest days: **58%** (2026-10-23 28.7 mm, 2026-10-24 20.4 mm, 2026-10-07 8.1 mm)
- Rain intensity (wet days only): **5.2 mm/day** over 19 wet days
- Rainiest week: **63.0 mm** (2026-10-18 → 2026-10-24)
- Longest dry streak: **5 days** (2026-10-02 → 2026-10-06)
- Longest wet run: **9 days** (2026-10-16 → 2026-10-24)
- Wettest run by total rain: **69.4 mm** over 9 days (2026-10-16 → 2026-10-24)
- Current run: **9 wet days in a row** since 2026-10-16
- Longest warm streak (max > 20 °C): **7 days** (2026-09-25 → 2026-10-01)
- Wettest weekday so far: **Friday** (8.1 mm on average over 5 days)
- Sunniest weekday so far: **Sunday** (10.1 h on average over 4 days)
- Mildest nights by weekday: **Wednesday** (11.9 °C average min over 4 days)
- Dry days by weekday: Mon 2/4 · Tue 1/4 · Wed 1/4 · Thu 1/4 · Fri 2/5 · Sat 2/5 · Sun 2/4
- Weekend vs. weekday rain: **3.7 mm/day** over 9 weekend days vs. 3.1 mm/day over 21 weekdays
- Weekend vs. weekday sunshine: **9.3 h/day** over 9 weekend days vs. 7.5 h/day over 21 weekdays
- Weekend vs. weekday max temperature: **16.5 °C** over 9 weekend days vs. 18.6 °C over 21 weekdays (-2.1 °C)
- Weekend vs. weekday night (min) temperature: **9.0 °C** over 9 weekend days vs. 10.6 °C over 21 weekdays (-1.6 °C)
- Rain vs. sunshine correlation: **r = -0.37**

Last 7 days (Breda):

| Date | Max °C | Min °C | Rain mm | Sun h |
|---|---|---|---|---|
| 2026-10-24 | 12.2 | 8.9 | 20.4 | 6.48 |
| 2026-10-23 | 13.8 | 9.6 | 28.7 | 5.0 |
| 2026-10-22 | 13.6 | 7.8 | 4.2 | 8.1 |
| 2026-10-21 | 12.6 | 8.8 | 0.9 | 2.59 |
| 2026-10-20 | 12.3 | 6.0 | 2.4 | 6.64 |
| 2026-10-19 | 14.8 | 8.2 | 0.6 | 3.44 |
| 2026-10-18 | 11.6 | 6.5 | 5.8 | 7.48 |

Latest EUR rates (2026-10-23): USD 1.1193 · GBP 0.83728 · CHF 0.9227 · TRY 55.6715

Change vs. 2026-10-22: USD -0.11% · GBP -0.05% · CHF +0.17% · TRY +0.11%

Change since tracking started (2026-09-25): USD -1.84% · GBP -2.69% · CHF -2.31% · TRY -0.23%

Biggest single-day move since tracking started: CHF -1.67% on 2026-10-02

Best and worst 5-business-day move:

- USD: best **+0.42%** (2026-10-09 → 2026-10-16) · worst **-1.57%** (2026-09-30 → 2026-10-07)
- GBP: best **-0.10%** (2026-10-08 → 2026-10-15) · worst **-1.24%** (2026-09-28 → 2026-10-05)
- CHF: best **+0.37%** (2026-10-02 → 2026-10-09) · worst **-1.78%** (2026-09-30 → 2026-10-07)
- TRY: best **+1.14%** (2026-10-09 → 2026-10-16) · worst **-1.22%** (2026-09-30 → 2026-10-07)

Realised volatility (std. dev. of daily moves, 20 moves): USD 0.33% · GBP 0.19% · CHF 0.47% · TRY 0.33%

10-move volatility, first window → latest: USD 0.41% → 0.21% (calmer) · GBP 0.21% → 0.17% (calmer) · CHF 0.63% → 0.24% (calmer) · TRY 0.39% → 0.24% (calmer)

Calmest → choppiest over the latest 10 moves: GBP 0.17% < USD 0.21% < TRY 0.24% < CHF 0.24% (calmest: **GBP**)

Longest calm USD stretch (no daily move above 0.5%): **13 business days** (2026-10-07 → 2026-10-23)

Weekend gaps vs. weekdays (avg absolute move):

- USD: **0.22%** over 4 gaps vs. 0.27% over 16 weekday moves (gaps smaller)
- GBP: **0.30%** over 4 gaps vs. 0.17% over 16 weekday moves (gaps larger)
- CHF: **0.17%** over 4 gaps vs. 0.35% over 16 weekday moves (gaps smaller)
- TRY: **0.15%** over 4 gaps vs. 0.27% over 16 weekday moves (gaps smaller)

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
- [x] Weekend vs. weekday temperature: are Saturdays/Sundays warmer than Monday–Friday
- [x] Longest wet run (consecutive days with rain) next to the longest dry streak
- [x] Weekend vs. weekday night (min) temperature
- [x] Wettest run by total rain: the consecutive wet days that together brought the most mm
- [ ] Average rain per day within wet runs (how intense the longest spells are)
- [x] Warmest weekday for nights: which day of the week has the mildest average min temperature
- [ ] Coldest weekday for days: which day of the week has the lowest average max temperature
