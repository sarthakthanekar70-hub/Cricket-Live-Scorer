"""
utils.py
--------
Small, reusable, stateless helper functions shared across pages:
number formatting, overs<->balls conversion, rate calculations, and the
dark-theme CSS injector. Keeping these here avoids duplicating logic
inside every Streamlit page.
"""

import streamlit as st
import config


# --------------------------------------------------------------------------
# OVERS / BALLS CONVERSION
# --------------------------------------------------------------------------
def balls_to_overs_str(total_balls):
    """Convert a raw ball count into cricket over notation, e.g. 17.4"""
    if total_balls is None:
        total_balls = 0
    overs = total_balls // config.BALLS_PER_OVER
    balls = total_balls % config.BALLS_PER_OVER
    return f"{overs}.{balls}"


def overs_str_to_balls(overs_str):
    """Convert '17.4' style overs notation back into total ball count."""
    try:
        if "." in str(overs_str):
            whole, part = str(overs_str).split(".")
        else:
            whole, part = str(overs_str), "0"
        return int(whole) * config.BALLS_PER_OVER + int(part)
    except (ValueError, TypeError):
        return 0


def max_balls_for_match(total_overs):
    """Total legal balls available in an innings for a given over limit."""
    if total_overs is None:
        return None
    return int(total_overs) * config.BALLS_PER_OVER


# --------------------------------------------------------------------------
# RATE CALCULATIONS
# --------------------------------------------------------------------------
def calc_run_rate(runs, balls):
    if not balls:
        return 0.0
    return round((runs / balls) * config.BALLS_PER_OVER, 2)


def calc_strike_rate(runs, balls):
    if not balls:
        return 0.0
    return round((runs / balls) * 100, 2)


def calc_economy(runs, balls):
    if not balls:
        return 0.0
    return round((runs / balls) * config.BALLS_PER_OVER, 2)


def calc_required_run_rate(runs_needed, balls_remaining):
    if not balls_remaining or balls_remaining <= 0:
        return 0.0
    return round((runs_needed / balls_remaining) * config.BALLS_PER_OVER, 2)


def calc_win_probability(current_score, target, overs_left, wickets_left,
                          total_wickets=10):
    """A lightweight heuristic placeholder for win probability -
    NOT a real predictive model. Blends required-rate pressure with
    wickets in hand so the UI has a believable number to display.
    Marked clearly as a placeholder for a future ML model."""
    if target is None or target <= 0:
        return 50.0
    runs_needed = max(target - current_score, 0)
    balls_left = max(overs_left * config.BALLS_PER_OVER, 1)
    required_rate = calc_required_run_rate(runs_needed, balls_left)

    if runs_needed <= 0:
        return 100.0
    if balls_left <= 0:
        return 0.0

    wicket_factor = wickets_left / max(total_wickets, 1)
    # Higher required rate relative to ~9 rpo baseline lowers win chance
    rate_pressure = max(0.0, 1 - (required_rate / 15.0))
    probability = (0.55 * rate_pressure + 0.45 * wicket_factor) * 100
    return round(min(max(probability, 1.0), 99.0), 1)


# --------------------------------------------------------------------------
# FORMATTING HELPERS
# --------------------------------------------------------------------------
def format_score(runs, wickets):
    return f"{runs}/{wickets}"


def ordinal(n):
    """1 -> 1st, 2 -> 2nd, 3 -> 3rd, 4 -> 4th ..."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def safe_div(a, b, default=0.0):
    return a / b if b else default


# --------------------------------------------------------------------------
# THEME / CSS
# --------------------------------------------------------------------------
def apply_theme():
    """Injects global CSS once per session so every page shares the same
    dark, rounded-card, professional look and feel."""
    t = config.THEME
    st.markdown(f"""
    <style>
        .stApp {{
            background-color: {t['background']};
            color: {t['text']};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {t['secondary_background']};
            border-right: 1px solid {t['border']};
        }}
        div[data-testid="stMetric"] {{
            background-color: {t['card_background']};
            border: 1px solid {t['border']};
            border-radius: 14px;
            padding: 14px 18px;
            transition: transform 0.15s ease-in-out;
        }}
        div[data-testid="stMetric"]:hover {{
            transform: translateY(-2px);
            border-color: {t['primary']};
        }}
        .cls-card {{
            background-color: {t['card_background']};
            border: 1px solid {t['border']};
            border-radius: 16px;
            padding: 20px 22px;
            margin-bottom: 16px;
        }}
        .cls-card h3, .cls-card h4 {{
            margin-top: 0;
        }}
        .cls-pill {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
            background-color: rgba(0,194,168,0.15);
            color: {t['primary']};
            border: 1px solid {t['primary']};
        }}
        .cls-pill-danger {{
            background-color: rgba(255,75,92,0.15);
            color: {t['danger']};
            border: 1px solid {t['danger']};
        }}
        .cls-pill-warning {{
            background-color: rgba(255,183,3,0.15);
            color: {t['secondary']};
            border: 1px solid {t['secondary']};
        }}
        .cls-score-big {{
            font-size: 2.6rem;
            font-weight: 800;
            color: {t['text']};
        }}
        .cls-subtle {{
            color: {t['muted_text']};
            font-size: 0.9rem;
        }}
        .stButton>button {{
            border-radius: 10px;
            border: 1px solid {t['border']};
            font-weight: 600;
        }}
        .stButton>button:hover {{
            border-color: {t['primary']};
            color: {t['primary']};
        }}
        h1, h2, h3 {{
            font-weight: 800;
        }}
        hr {{
            border-color: {t['border']};
        }}
    </style>
    """, unsafe_allow_html=True)


def section_header(title, subtitle=None, icon=""):
    st.markdown(f"### {icon} {title}")
    if subtitle:
        st.markdown(f"<div class='cls-subtle'>{subtitle}</div>", unsafe_allow_html=True)
    st.write("")


def card_start():
    st.markdown("<div class='cls-card'>", unsafe_allow_html=True)


def card_end():
    st.markdown("</div>", unsafe_allow_html=True)


def pill(text, kind="primary"):
    cls = "cls-pill"
    if kind == "danger":
        cls += " cls-pill-danger"
    elif kind == "warning":
        cls += " cls-pill-warning"
    return f"<span class='{cls}'>{text}</span>"
