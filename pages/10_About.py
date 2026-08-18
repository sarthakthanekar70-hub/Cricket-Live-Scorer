"""
pages/10_About.py
--------------------
Static informational page describing the project, tech stack, and
roadmap of future AI-powered features.
"""

import streamlit as st

import config
import utils

utils.apply_theme()

utils.section_header(config.APP_NAME, f"Version {config.APP_VERSION}", icon="ℹ️")

utils.card_start()
st.markdown("""
#### About
The **Cricket Live Scoring & Analytics System** is a full-featured, Cricbuzz/ESPN
Cricinfo-style scoring application built entirely with Streamlit and SQLite.
It supports end-to-end match management: creating matches, setting Playing XIs,
ball-by-ball live scoring, automatic scorecards, rich analytics, and multi-format
exports (PDF, Excel, CSV).

#### Tech Stack
- **Frontend:** Streamlit
- **Backend:** Python (OOP business logic in `scorer.py`, `analytics.py`)
- **Database:** SQLite (13 relational tables)
- **Libraries:** pandas, NumPy, Plotly, openpyxl, ReportLab, Pillow

#### Supported Match Formats
T10, T20, ODI, Test, and Custom Overs (1-100).

#### Roadmap - Future AI Features (placeholders in this build)
- Predict Final Score
- Win Probability Model
- Player Performance Prediction
- Man of the Match Prediction
- Team Strength Comparison
- Advanced Performance Dashboard
""")
utils.card_end()

utils.card_start()
st.markdown("#### Credits")
st.write("Designed and engineered as a modular, production-quality reference "
         "implementation for a cricket scoring platform.")
utils.card_end()
