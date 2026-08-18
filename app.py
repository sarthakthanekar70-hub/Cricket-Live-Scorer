"""
app.py
------
Main entry point for the Cricket Live Scoring & Analytics System.
Sets global Streamlit page config, applies the dark theme, initializes
the SQLite database/schema, and renders the Home dashboard. Every page
inside pages/ imports `get_db()` from here so the whole app shares one
Database instance per session.
"""

import os
import streamlit as st

import config
import utils
from database import Database


# --------------------------------------------------------------------------
# PAGE CONFIG (must be the first Streamlit call)
# --------------------------------------------------------------------------
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon=config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

utils.apply_theme()


# --------------------------------------------------------------------------
# SHARED DATABASE ACCESSOR
# --------------------------------------------------------------------------
@st.cache_resource
def get_db():
    """Single cached Database instance shared by every page in the app."""
    return Database()


# --------------------------------------------------------------------------
# HOME PAGE RENDERER (imported by pages/1_Home.py as well)
# --------------------------------------------------------------------------
def render_home():
    db = get_db()

    col_logo, col_title = st.columns([1, 6])
    with col_logo:
        if os.path.exists(config.LOGO_PATH):
            st.image(config.LOGO_PATH, width=90)
        else:
            st.markdown(f"<div style='font-size:64px'>{config.APP_ICON}</div>",
                        unsafe_allow_html=True)
    with col_title:
        st.markdown(f"# {config.APP_NAME}")
        st.markdown(
            "<div class='cls-subtle'>Professional live scoring, analytics and "
            "match management - built with Streamlit &amp; SQLite.</div>",
            unsafe_allow_html=True,
        )

    st.write("")
    st.divider()

    all_matches = db.get_all_matches()
    live_matches = [m for m in all_matches if m["status"] == "Live"]
    completed_matches = [m for m in all_matches if m["status"] == "Completed"]

    # ---- Top level quick metrics -----------------------------------------
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Matches", len(all_matches))
    m2.metric("Live Matches", len(live_matches))
    m3.metric("Completed Matches", len(completed_matches))
    m4.metric("Players Tracked", len(db.get_all_players()))

    st.write("")

    # ---- Quick action cards ------------------------------------------------
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        utils.card_start()
        st.markdown("#### 🆕 Create New Match")
        st.write("Set up teams, toss, and match format to start scoring.")
        if st.button("Create Match", use_container_width=True, key="home_new_match"):
            st.switch_page("pages/2_New_Match.py")
        utils.card_end()

    with c2:
        utils.card_start()
        st.markdown("#### ▶️ Resume Match")
        st.write("Continue scoring a match that is already in progress.")
        if st.button("Resume Match", use_container_width=True, key="home_resume"):
            if live_matches:
                st.session_state[config.SessionKeys.CURRENT_MATCH_ID] = live_matches[0]["match_id"]
                st.switch_page("pages/4_Live_Scoring.py")
            else:
                st.warning("No live matches to resume right now.")
        utils.card_end()

    with c3:
        utils.card_start()
        st.markdown("#### 📚 Previous Matches")
        st.write("Browse, search, and export completed match scorecards.")
        if st.button("View Matches", use_container_width=True, key="home_prev"):
            st.switch_page("pages/8_Previous_Matches.py")
        utils.card_end()

    with c4:
        utils.card_start()
        st.markdown("#### 📊 Statistics Dashboard")
        st.write("Career batting and bowling statistics across all matches.")
        if st.button("Open Dashboard", use_container_width=True, key="home_stats"):
            st.switch_page("pages/6_Player_Statistics.py")
        utils.card_end()

    st.write("")

    # ---- Live matches strip --------------------------------------------------
    if live_matches:
        utils.section_header("Live Matches", icon="🔴")
        for m in live_matches:
            utils.card_start()
            lc1, lc2, lc3 = st.columns([3, 2, 1])
            with lc1:
                st.markdown(f"**{m['match_name']}** &nbsp; "
                            f"{utils.pill('LIVE', 'danger')}", unsafe_allow_html=True)
                st.caption(f"{m['team_a_name']} vs {m['team_b_name']} | {m['venue'] or 'TBD'}")
            with lc2:
                st.caption(f"Format: {m['match_type']} | {m.get('tournament_name') or ''}")
            with lc3:
                if st.button("Open", key=f"open_live_{m['match_id']}"):
                    st.session_state[config.SessionKeys.CURRENT_MATCH_ID] = m["match_id"]
                    st.switch_page("pages/4_Live_Scoring.py")
            utils.card_end()

    # ---- Recent completed matches --------------------------------------------
    if completed_matches:
        utils.section_header("Recent Completed Matches", icon="🏁")
        for m in completed_matches[:5]:
            result = db.get_result(m["match_id"])
            utils.card_start()
            rc1, rc2 = st.columns([4, 1])
            with rc1:
                st.markdown(f"**{m['match_name']}** - {m['team_a_name']} vs {m['team_b_name']}")
                st.caption(result["summary"] if result else "Result pending")
            with rc2:
                if st.button("Scorecard", key=f"open_completed_{m['match_id']}"):
                    st.session_state[config.SessionKeys.SELECTED_MATCH_FOR_VIEW] = m["match_id"]
                    st.switch_page("pages/5_Scorecard.py")
            utils.card_end()

    if not all_matches:
        st.info("No matches yet. Click **Create Match** above to get started!")


# --------------------------------------------------------------------------
# SIDEBAR (shown on every page automatically via Streamlit's page nav,
# this adds extra context above the automatic page links)
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"## {config.APP_ICON} {config.APP_SHORT_NAME}")
    st.caption(f"v{config.APP_VERSION}")
    st.divider()


if __name__ == "__main__":
    render_home()
