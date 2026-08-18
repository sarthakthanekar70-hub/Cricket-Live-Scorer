"""
config.py
----------
Central configuration file for the Cricket Live Scoring & Analytics System.
Holds constants, theme colors, paths, and match-format definitions so that
every other module can import a single source of truth instead of
hard-coding values throughout the codebase.
"""

import os

# --------------------------------------------------------------------------
# BASE PATHS
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "cricket.db")

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
BACKGROUND_PATH = os.path.join(ASSETS_DIR, "background.png")

EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
EXPORT_PDF_DIR = os.path.join(EXPORTS_DIR, "pdf")
EXPORT_EXCEL_DIR = os.path.join(EXPORTS_DIR, "excel")
EXPORT_CSV_DIR = os.path.join(EXPORTS_DIR, "csv")

CHARTS_DIR = os.path.join(BASE_DIR, "charts")

# Ensure critical directories exist at import time (safe / idempotent)
for _d in (DATABASE_DIR, ASSETS_DIR, ICONS_DIR, EXPORT_PDF_DIR,
           EXPORT_EXCEL_DIR, EXPORT_CSV_DIR, CHARTS_DIR):
    os.makedirs(_d, exist_ok=True)

# --------------------------------------------------------------------------
# APP METADATA
# --------------------------------------------------------------------------
APP_NAME = "Cricket Live Scoring & Analytics System"
APP_SHORT_NAME = "CricketLiveScorer"
APP_ICON = "🏏"
APP_VERSION = "1.0.0"

# --------------------------------------------------------------------------
# MATCH FORMATS
# --------------------------------------------------------------------------
MATCH_TYPES = {
    "T10": 10,
    "T20": 20,
    "ODI": 50,
    "Test": 90,          # per-innings over cap not strictly enforced for Test
    "Custom": None,       # user selects overs (1-100)
}

MAX_CUSTOM_OVERS = 100
MIN_CUSTOM_OVERS = 1

BALLS_PER_OVER = 6

DISMISSAL_TYPES = [
    "Bowled", "Caught", "LBW", "Run Out",
    "Stumped", "Hit Wicket", "Retired Hurt", "Obstructing the Field"
]

EXTRA_TYPES = ["Wide", "No Ball", "Bye", "Leg Bye", "Penalty"]

# Overs considered part of Powerplay / Middle / Death phases (used for
# analytics splits). These scale automatically for shorter formats.
POWERPLAY_OVERS_FRACTION = 0.3   # first 30% of innings overs
DEATH_OVERS_FRACTION = 0.2       # last 20% of innings overs

# --------------------------------------------------------------------------
# THEME / UI COLORS (Dark Professional Theme)
# --------------------------------------------------------------------------
THEME = {
    "background": "#0E1117",
    "secondary_background": "#161A23",
    "card_background": "#1B2030",
    "primary": "#00C2A8",       # teal accent
    "secondary": "#FFB703",     # amber accent
    "danger": "#FF4B5C",
    "success": "#3DDC84",
    "text": "#E8EAF0",
    "muted_text": "#8A90A2",
    "border": "#2A2F3E",
    "team_a": "#00C2A8",
    "team_b": "#FFB703",
}

PLOTLY_TEMPLATE = "plotly_dark"

# --------------------------------------------------------------------------
# MISC
# --------------------------------------------------------------------------
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Session-state keys used across pages (centralised to avoid typos)
class SessionKeys:
    CURRENT_MATCH_ID = "current_match_id"
    CURRENT_INNINGS = "current_innings_number"
    SELECTED_MATCH_FOR_VIEW = "selected_match_for_view"
    LAST_ACTION_SNAPSHOT = "last_action_snapshot"
    THEME_APPLIED = "theme_applied"
