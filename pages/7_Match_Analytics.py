"""
pages/7_Match_Analytics.py
----------------------------
Visual analytics for a selected match: worm graph, Manhattan charts,
run rate progression, wickets timeline, boundary timeline, and run
distribution pie chart. Also surfaces the AI-feature placeholders
(final score prediction, win probability, team strength comparison).
"""

import streamlit as st

import config
import utils
import analytics
from app import get_db

utils.apply_theme()
db = get_db()

match_id = (st.session_state.get(config.SessionKeys.SELECTED_MATCH_FOR_VIEW)
            or st.session_state.get(config.SessionKeys.CURRENT_MATCH_ID))

if not match_id:
    st.warning("No match selected. Choose one from Previous Matches or Home.")
    st.stop()

match = db.get_match(match_id)
innings_list = db.get_innings_by_match(match_id)

if not innings_list:
    st.info("No innings data yet for this match.")
    st.stop()

team_names = [db.get_team_name(i["batting_team_id"]) for i in innings_list]

utils.section_header(
    f"Match Analytics - {match['match_name']}",
    "Interactive charts generated from ball-by-ball data",
    icon="📈",
)

# --- Worm & Run Rate (multi-innings comparisons) ---------------------------
if len(innings_list) >= 1:
    st.plotly_chart(analytics.worm_graph(db, innings_list, team_names),
                     use_container_width=True)
if len(innings_list) >= 1:
    st.plotly_chart(analytics.run_rate_graph(db, innings_list, team_names),
                     use_container_width=True)

# --- Per-innings breakdown --------------------------------------------------
innings_choice = st.selectbox(
    "Select Innings for Detailed Breakdown",
    [f"Innings {i['innings_number']} - {db.get_team_name(i['batting_team_id'])}"
     for i in innings_list],
)
selected_innings = innings_list[
    [f"Innings {i['innings_number']} - {db.get_team_name(i['batting_team_id'])}"
     for i in innings_list].index(innings_choice)
]
sel_innings_id = selected_innings["innings_id"]
sel_team_name = db.get_team_name(selected_innings["batting_team_id"])

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(analytics.manhattan_graph(db, sel_innings_id, sel_team_name),
                     use_container_width=True)
with col2:
    st.plotly_chart(analytics.wickets_timeline(db, sel_innings_id),
                     use_container_width=True)

col3, col4 = st.columns(2)
with col3:
    st.plotly_chart(analytics.boundary_timeline(db, sel_innings_id),
                     use_container_width=True)
with col4:
    dist = analytics.run_distribution_breakdown(db, sel_innings_id)
    st.plotly_chart(analytics.run_distribution_pie(dist), use_container_width=True)

st.divider()

# --- AI feature placeholders -------------------------------------------------
utils.section_header("Future AI Features (Design Placeholders)", icon="🤖")
p1, p2 = st.columns(2)
with p1:
    utils.card_start()
    st.markdown("#### 🔮 Predict Final Score")
    balls_bowled = selected_innings["total_balls"] or 0
    overs_bowled = balls_bowled / config.BALLS_PER_OVER
    total_overs = match["total_overs"] or 20
    projected = analytics.predict_final_score_placeholder(
        selected_innings["total_runs"] or 0, overs_bowled, total_overs)
    st.metric("Naive Projection (placeholder)", projected if projected else "-")
    st.caption("This is a simple run-rate extrapolation, not a trained ML model.")
    utils.card_end()
with p2:
    utils.card_start()
    st.markdown("#### ⚖️ Team Strength Comparison")
    comp = analytics.team_strength_comparison_placeholder(
        db.get_team_name(match["team_a_id"]), db.get_team_name(match["team_b_id"]))
    st.write(comp["note"])
    utils.card_end()

st.caption("Additional placeholders: Win Probability (shown on Live Scoring page), "
           "Player Performance Prediction (see Player Statistics), "
           "Man of the Match Prediction, Performance Dashboard.")
