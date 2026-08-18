"""
pages/2_New_Match.py
---------------------
Collects match metadata (tournament, venue, date, teams, format) and
toss details, creates the match + team records in SQLite, then routes
the user to Playing XI selection.
"""

import datetime
import streamlit as st

import config
import utils
from app import get_db

utils.apply_theme()
db = get_db()

utils.section_header("Create New Match", "Set up match details, teams and toss", icon="🆕")

with st.form("new_match_form", clear_on_submit=False):
    utils.card_start()
    st.markdown("#### Match Details")
    col1, col2 = st.columns(2)
    with col1:
        tournament_name = st.text_input("Tournament Name", placeholder="e.g. Zeal Premier League")
        match_name = st.text_input("Match Name*", placeholder="e.g. Final")
        venue = st.text_input("Venue", placeholder="e.g. Zeal Ground, Pune")
    with col2:
        match_number = st.text_input("Match Number", placeholder="e.g. Match 12")
        match_date = st.date_input("Date", value=datetime.date.today())
        match_type = st.selectbox("Match Type*", list(config.MATCH_TYPES.keys()))

    total_overs = config.MATCH_TYPES.get(match_type)
    if match_type == "Custom":
        total_overs = st.slider("Custom Overs", config.MIN_CUSTOM_OVERS,
                                 config.MAX_CUSTOM_OVERS, 20)
    elif match_type == "Test":
        st.caption("Test matches use unlimited overs per innings (day-based).")
        total_overs = None
    else:
        st.caption(f"{match_type} format uses {total_overs} overs per innings.")
    utils.card_end()

    utils.card_start()
    st.markdown("#### Teams")
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        team_a_name = st.text_input("Team A*", placeholder="e.g. Team Falcons")
    with tcol2:
        team_b_name = st.text_input("Team B*", placeholder="e.g. Team Titans")
    utils.card_end()

    utils.card_start()
    st.markdown("#### Toss")
    tosscol1, tosscol2 = st.columns(2)
    with tosscol1:
        toss_winner_choice = st.radio("Toss Winner", ["Team A", "Team B"], horizontal=True)
    with tosscol2:
        toss_decision = st.radio("Chose to", ["Bat", "Bowl"], horizontal=True)
    utils.card_end()

    submitted = st.form_submit_button("Create Match & Continue to Playing XI",
                                       use_container_width=True, type="primary")

if submitted:
    if not match_name or not team_a_name or not team_b_name:
        st.error("Match Name, Team A, and Team B are required fields.")
    elif team_a_name.strip().lower() == team_b_name.strip().lower():
        st.error("Team A and Team B must be different.")
    else:
        team_a_id = db.get_or_create_team(team_a_name)
        team_b_id = db.get_or_create_team(team_b_name)

        match_id = db.create_match(
            tournament_name=tournament_name, match_name=match_name,
            match_number=match_number, venue=venue,
            match_date=match_date.strftime(config.DATE_FORMAT),
            team_a_id=team_a_id, team_b_id=team_b_id,
            match_type=match_type, total_overs=total_overs,
        )

        toss_winner_team_id = team_a_id if toss_winner_choice == "Team A" else team_b_id
        db.set_toss(match_id, toss_winner_team_id, toss_decision)

        st.session_state[config.SessionKeys.CURRENT_MATCH_ID] = match_id
        st.success(f"Match '{match_name}' created! Toss won by "
                   f"{team_a_name if toss_winner_choice == 'Team A' else team_b_name}, "
                   f"chose to {toss_decision.lower()}.")
        st.switch_page("pages/3_Playing_XI.py")
