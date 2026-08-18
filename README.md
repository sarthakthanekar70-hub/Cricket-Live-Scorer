# 🏏 Cricket Live Scoring & Analytics System

A production-quality, Cricbuzz/ESPN Cricinfo-style **live cricket scoring and
analytics platform**, built entirely with **Streamlit** and **SQLite**.

---

## ✨ Features

- **Match Setup** - tournament, venue, date, teams, format (T10 / T20 / ODI / Test
  / Custom 1-100 overs), toss winner & decision.
- **Playing XI** - 11 players per team with jersey number, captain, wicketkeeper,
  and batting order.
- **Live Scoring** - one-tap ball input (0-6, Wide, No Ball, Bye, Leg Bye, Dot
  Ball, Wicket, Undo, End Over, Next Innings, Finish Match) with automatic
  updates to totals, batter/bowler figures, partnerships, extras, and overs.
- **Wicket Workflow** - dismissal type, fielder, bowler, and next-batter capture.
- **Scorecards** - full batting & bowling cards, fall of wickets, partnerships,
  and over-by-over summaries.
- **Match Analytics** - Worm graph, Manhattan chart, run-rate progression,
  wickets timeline, boundary timeline, and run-distribution pie chart (Plotly).
- **Player Statistics Dashboard** - career batting/bowling leaderboards and
  per-player profiles, rebuilt automatically after every completed match.
- **Previous Matches** - search, filter (team / tournament / status), open,
  delete, and export.
- **Exports** - PDF (ReportLab), Excel (openpyxl), and CSV scorecards.
- **Dark Professional UI** - rounded cards, colored scorecards, sidebar
  navigation, responsive layout.
- **Future AI Feature placeholders** - final score prediction, win probability,
  player performance prediction, Man of the Match prediction, team strength
  comparison (clearly marked as design placeholders, not real ML models).

---

## 📁 Project Structure

```
CricketLiveScorer/
├── app.py                  # Entry point, page config, theme, Home renderer
├── config.py                # Constants, theme colors, paths, formats
├── database.py               # SQLite schema + Database access layer
├── scorer.py                 # Live-scoring business logic engine
├── analytics.py               # Summary stats & Plotly chart builders
├── export.py                  # PDF / Excel / CSV export functions
├── utils.py                    # Shared helpers (overs/rates/CSS theme)
├── requirements.txt
├── README.md
├── database/cricket.db          # SQLite database (auto-created)
├── assets/                       # logo, background, icons
├── exports/{pdf,excel,csv}/        # generated exports are also saved here
├── charts/                          # reserved for cached chart images
├── pages/
│   ├── 1_Home.py
│   ├── 2_New_Match.py
│   ├── 3_Playing_XI.py
│   ├── 4_Live_Scoring.py
│   ├── 5_Scorecard.py
│   ├── 6_Player_Statistics.py
│   ├── 7_Match_Analytics.py
│   ├── 8_Previous_Matches.py
│   ├── 9_Settings.py
│   └── 10_About.py
└── models/                          # reserved for future ML model artifacts
```

---

## 🗄️ Database Schema (13 tables)

`teams`, `players`, `matches`, `match_squads`, `innings`, `batting`, `bowling`,
`ball_by_ball`, `overs`, `partnerships`, `fall_of_wickets`, `statistics`, `result`.

`ball_by_ball` is the single source of truth - every other aggregate (batting,
bowling, overs, totals) can be rebuilt from it, which is exactly what happens
when you hit **Undo**.

---

## 🚀 Getting Started

```bash
cd CricketLiveScorer
pip install -r requirements.txt
streamlit run app.py
```

The SQLite database and folder structure are created automatically on first run.

---

## 🧭 How To Use

1. **Home** → click **Create Match**.
2. Fill in match details, teams, and toss → **Create Match & Continue to Playing XI**.
3. Enter all 11 players (name, jersey, captain, keeper, batting order) for both
   teams → **Save Playing XI & Continue**.
4. Choose openers and the opening bowler → **Start Innings**.
5. Score ball-by-ball using the input panel. Wickets open a details form;
   completed overs prompt you to pick the next bowler.
6. When the innings ends, click **Start Next Innings** (target is set
   automatically), repeat scoring, then **Finish Match** to lock in the result.
7. View the full **Scorecard**, explore **Match Analytics**, or head to
   **Previous Matches** to search, export, or delete historical matches.

---

## 🛠️ Tech Stack

| Layer      | Technology                          |
|------------|--------------------------------------|
| Frontend   | Streamlit                            |
| Backend    | Python (OOP: `Scorer`, `Database`)     |
| Database   | SQLite                                |
| Data/Charts| pandas, NumPy, Plotly                  |
| Exports    | openpyxl (Excel), ReportLab (PDF), CSV |
| Media      | Pillow                                  |

---

## 📌 Notes on Design Decisions

- **Undo** works by deleting the last `ball_by_ball` row and rebuilding all
  derived batting/bowling/over aggregates from what remains - simpler and far
  less bug-prone than reversing each incremental update by hand.
- **Win Probability**, **Predict Final Score**, and other "AI" numbers shown
  in the UI are explicitly labelled **placeholders** - lightweight heuristics,
  not trained models - matching the "Future AI Features (design placeholders
  only)" requirement.
- Batting order in Playing XI is captured via a numeric "Bat Order" field per
  player (sorted on save) as a Streamlit-native stand-in for drag-and-drop,
  since native multi-item drag-and-drop reordering isn't part of core Streamlit.

---

## 📄 License

Provided as an educational / portfolio reference implementation.
