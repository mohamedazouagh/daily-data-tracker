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
**Days tracked:** 50 weather · 36 FX

- Average max temperature: **15.1 °C**
- Warmest day: **26.2 °C** · Coldest max: **6.0 °C**
- Last 7 days vs. the 7 before (avg max): **8.4 °C** vs. 10.0 °C (-1.6 °C)
- Total rain: **130.6 mm** · Dry days: **18**
- Coldest night: **-1.2 °C** on 2026-11-10
- First frost: **-1.2 °C** on 2026-11-10
- First frost-risk night (min below 3 °C): **1.6 °C** on 2026-11-06 (week 45), 5 such nights so far
- Warmest night: **17.8 °C** on 2026-09-30
- Largest day/night range: **13.4 °C** on 2026-09-25
- Sunniest day: **11.1 h** on 2026-09-25 · Average sunshine: **7.3 h/day**
- Wettest day: **28.7 mm** on 2026-10-23
- Wettest day's share of all rain: **22%** (28.7 mm on 2026-10-23)
- Share of rain from the 3 wettest days: **46%** (2026-10-23 28.7 mm, 2026-10-24 20.4 mm, 2026-10-25 11.0 mm)
- Rain intensity (wet days only): **4.1 mm/day** over 32 wet days
- Rainiest week: **68.3 mm** (2026-10-20 → 2026-10-26)
- Longest dry streak: **5 days** (2026-10-02 → 2026-10-06)
- Longest wet run: **12 days** (2026-10-16 → 2026-10-27), 82.9 mm at 6.9 mm/day
- Wettest run by total rain: **82.9 mm** over 12 days (2026-10-16 → 2026-10-27)
- Wet spells of 3+ days: 5; latest **2.4 mm/day** over 4 days (2026-11-10 → 2026-11-13) vs. 0.7 mm/day over 3 days (2026-11-01 → 2026-11-03), heavier
- Dry spells of 3+ days: 3 (lengths 3, 5, 3); latest **3 days** (2026-11-04 → 2026-11-06) vs. 5 days (2026-10-02 → 2026-10-06), shorter
- Sunshine during dry spells (avg h/day): 2026-09-25 → 2026-09-27 9.9 h · 2026-10-02 → 2026-10-06 10.2 h · 2026-11-04 → 2026-11-06 8.6 h
- Sunshine during wet spells (avg h/day): 2026-09-28 → 2026-10-01 7.5 h · 2026-10-07 → 2026-10-11 8.1 h · 2026-10-16 → 2026-10-27 5.9 h · 2026-11-01 → 2026-11-03 2.3 h · 2026-11-10 → 2026-11-13 5.8 h
- Dry vs. wet spell sunshine: **+3.6 h/day** (9.7 h over 11 dry-spell days vs. 6.1 h over 28 wet-spell days)
- Dry vs. wet spell temperature: days **+3.4 °C** (17.8 vs. 14.4 °C max), nights **-0.6 °C** (8.0 vs. 8.6 °C min) over 11 dry-spell and 28 wet-spell days
- Current run: **4 wet days in a row** since 2026-11-10
- Longest warm streak (max > 20 °C): **7 days** (2026-09-25 → 2026-10-01)
- Wettest weekday so far: **Friday** (5.1 mm on average over 8 days)
- Sunniest weekday so far: **Thursday** (8.8 h on average over 7 days)
- Cloudiest weekday by sunshine share: **Monday** (59% of possible sun on average over 7 days)
- Mildest nights by weekday: **Wednesday** (9.2 °C average min over 7 days)
- Coldest days by weekday: **Saturday** (14.0 °C average max over 7 days)
- Widest day/night range by weekday: **Tuesday** (8.1 °C average max − min over 7 days)
- Day/night range by week: 8.4 → 10.0 → 7.7 → 5.4 → 5.5 → 5.2 → 6.1 °C; latest week (2026-11-07 → 2026-11-13) **6.1 °C** vs. 8.4 °C in the first, narrowing
- Sunshine by week: 8.3 → 8.7 → 8.8 → 6.2 → 7.0 → 5.4 → 5.9 h/day; latest week (2026-11-07 → 2026-11-13) **5.9 h/day** vs. 8.3 h in the first, darker
- Sunshine as share of daylight by week: 72% → 78% → 82% → 60% → 71% → 58% → 65%; latest week (2026-11-07 → 2026-11-13) **65%** of possible sun vs. 72% in the first, cloudier
- Nights by week (avg min): 13.8 → 9.5 → 9.6 → 7.8 → 8.3 → 4.8 → 2.3 °C; latest week (2026-11-07 → 2026-11-13) **2.3 °C** vs. 13.8 °C in the first, colder
- Frost-risk nights by week (min below 3 °C): 0 → 0 → 0 → 0 → 0 → 1 → 4; latest week (2026-11-07 → 2026-11-13) **4 of 7 nights**
- Frost nights by week (min below 0 °C): 0 → 0 → 0 → 0 → 0 → 0 → 1; latest week (2026-11-07 → 2026-11-13) **1 of 7 nights** vs. 4 frost-risk
- Dry days by weekday: Mon 3/7 · Tue 1/7 · Wed 3/7 · Thu 2/7 · Fri 4/8 · Sat 3/7 · Sun 2/7
- Weekend vs. weekday rain: **3.7 mm/day** over 14 weekend days vs. 2.2 mm/day over 36 weekdays
- Weekend vs. weekday sunshine: **7.8 h/day** over 14 weekend days vs. 7.1 h/day over 36 weekdays
- Weekend vs. weekday max temperature: **14.2 °C** over 14 weekend days vs. 15.4 °C over 36 weekdays (-1.2 °C)
- Weekend vs. weekday night (min) temperature: **7.7 °C** over 14 weekend days vs. 8.1 °C over 36 weekdays (-0.4 °C)
- Rain vs. sunshine correlation: **r = -0.25**

Last 7 days (Breda):

| Date | Max °C | Min °C | Rain mm | Sun h |
|---|---|---|---|---|
| 2026-11-13 | 8.9 | 3.3 | 0.3 | 8.3 |
| 2026-11-12 | 8.2 | 1.6 | 0.5 | 6.55 |
| 2026-11-11 | 6.0 | 4.2 | 8.4 | 0.0 |
| 2026-11-10 | 8.1 | -1.2 | 0.3 | 8.23 |
| 2026-11-09 | 10.0 | 1.5 | 0.0 | 8.91 |
| 2026-11-08 | 9.0 | 6.0 | 6.0 | 4.37 |
| 2026-11-07 | 8.6 | 0.6 | 0.9 | 4.74 |

Latest EUR rates (2026-11-13): USD 1.1052 · GBP 0.83559 · CHF 0.9266 · TRY 55.6667

Change vs. 2026-11-12: USD -0.26% · GBP -0.04% · CHF +0.37% · TRY -0.04%

Change since tracking started (2026-09-25): USD -3.08% · GBP -2.89% · CHF -1.90% · TRY -0.23%

Biggest single-day move since tracking started: CHF -1.67% on 2026-10-02

Best and worst 5-business-day move:

- USD: best **+1.20%** (2026-10-28 → 2026-11-04) · worst **-1.57%** (2026-09-30 → 2026-10-07)
- GBP: best **+0.24%** (2026-11-05 → 2026-11-12) · worst **-1.24%** (2026-09-28 → 2026-10-05)
- CHF: best **+1.35%** (2026-11-06 → 2026-11-13) · worst **-1.78%** (2026-09-30 → 2026-10-07)
- TRY: best **+1.58%** (2026-10-28 → 2026-11-04) · worst **-1.22%** (2026-09-30 → 2026-10-07)

Realised volatility (std. dev. of daily moves, 35 moves): USD 0.36% · GBP 0.18% · CHF 0.40% · TRY 0.37%

10-move volatility, first window → latest: USD 0.41% → 0.49% (choppier) · GBP 0.21% → 0.14% (calmer) · CHF 0.63% → 0.29% (calmer) · TRY 0.39% → 0.48% (choppier)

Calmest → choppiest over the latest 10 moves: GBP 0.14% < CHF 0.29% < TRY 0.48% < USD 0.49% (calmest: **GBP**)

Longest calm USD stretch (no daily move above 0.5%): **20 business days** (2026-10-07 → 2026-11-03)

Weekend gaps vs. weekdays (avg absolute move):

- USD: **0.22%** over 7 gaps vs. 0.32% over 28 weekday moves (gaps smaller)
- GBP: **0.23%** over 7 gaps vs. 0.15% over 28 weekday moves (gaps larger)
- CHF: **0.16%** over 7 gaps vs. 0.30% over 28 weekday moves (gaps smaller)
- TRY: **0.18%** over 7 gaps vs. 0.31% over 28 weekday moves (gaps smaller)

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
- [x] Average rain per day within wet runs (how intense the longest spells are)
- [x] Warmest weekday for nights: which day of the week has the mildest average min temperature
- [x] Wet-run intensity history: is each new long spell heavier or lighter than the last
- [x] Dry-spell history: how long each dry spell of 3+ days lasted and whether they are getting shorter
- [x] Dry-spell sunshine: average sun hours during each dry spell of 3+ days
- [x] Wet-spell sunshine: average sun hours during each wet spell of 3+ days, next to the dry ones
- [x] Dry vs. wet spell sunshine gap: how many more sun hours a day the dry spells get on average
- [x] Dry vs. wet spell temperature: are dry spells warmer by day and colder at night than wet ones
- [ ] Dry vs. wet spell temperature history: does the night-time gap grow as autumn nights get longer
- [x] Coldest weekday for days: which day of the week has the lowest average max temperature
- [x] Day/night range by weekday: which day of the week has the widest average max − min spread
- [x] Day/night range trend: is the weekly average max − min spread shrinking as autumn goes on
- [x] Sunshine by week: weekly average sun hours to see how fast the days are getting darker
- [x] Sunshine by week vs. day length: share of the astronomically possible sun hours each week
- [x] Cloudiest weekday by sunshine share (removes the day-length effect from the weekday sun ranking)
- [ ] Cloudiest weekday history: does the same weekday stay cloudiest as more weeks come in
- [x] Nights by week: weekly average min temperature to see how fast the nights are cooling
- [x] Week of the first frost-risk night (min below 3 °C) once nights keep dropping
- [x] Frost-risk nights per week (min below 3 °C) to see how fast they become common
- [x] Frost nights per week (min below 0 °C) next to the frost-risk count once frosts start
- [ ] Frost share of frost-risk nights: how often a night below 3 °C actually drops below 0 °C, per week
