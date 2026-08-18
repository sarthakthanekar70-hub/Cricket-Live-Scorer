"""
pages/5_Scorecard.py
----------------------
Displays the complete scorecard (both innings: batting, bowling,
fall of wickets, match summary and result) for whichever match is
stored in session_state under SELECTED_MATCH_FOR_VIEW (or the current
live match as a fallback).
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
if not match:
    st.error("Match not found.")
    st.stop()

team_a_name = db.get_team_name(match["team_a_id"])
team_b_name = db.get_team_name(match["team_b_id"])

utils.section_header(
    match["match_name"] or "Match Scorecard",
    f"{team_a_name} vs {team_b_name} | {match.get('venue') or ''} | {match.get('match_date') or ''}",
    icon="📋",
)

result = db.get_result(match_id)
if result:
    utils.card_start()
    st.markdown(f"### 🏆 {result['summary']}")
    if result["player_of_match_id"]:
        st.markdown(f"**Player of the Match:** {db.get_player_name(result['player_of_match_id'])}")
    utils.card_end()
elif match["status"] == "Live":
    st.info("This match is currently live. Visit Live Scoring to continue.")

innings_list = db.get_innings_by_match(match_id)

for idx, inn in enumerate(innings_list, start=1):
    team_name = db.get_team_name(inn["batting_team_id"])
    st.markdown(f"## Innings {idx}: {team_name}")
    st.markdown(f"**{inn['total_runs']}/{inn['total_wickets']}** "
                f"({utils.balls_to_overs_str(inn['total_balls'])} overs)")

    tab_bat, tab_bowl, tab_extra = st.tabs(["Batting", "Bowling", "Extras & FoW"])

    with tab_bat:
        batting_card = db.get_batting_card(inn["innings_id"])
        rows = []
        for b in batting_card:
            status = b["dismissal_type"] if b["is_out"] else b["status"]
            rows.append({
                "Batter": b["player_name"], "Status": status,
                "Runs": b["runs"], "Balls": b["balls"],
                "4s": b["fours"], "6s": b["sixes"],
                "SR": utils.calc_strike_rate(b["runs"], b["balls"]),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    with tab_bowl:
        bowling_card = db.get_bowling_card(inn["innings_id"])
        rows = []
        for b in bowling_card:
            rows.append({
                "Bowler": b["player_name"], "Overs": utils.balls_to_overs_str(b["balls"]),
                "Maidens": b["maidens"], "Runs": b["runs_conceded"],
                "Wickets": b["wickets"],
                "Economy": utils.calc_economy(b["runs_conceded"], b["balls"]),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    with tab_extra:
        st.markdown(
            f"Wide: **{inn['extras_wide']}** | No Ball: **{inn['extras_noball']}** | "
            f"Bye: **{inn['extras_bye']}** | Leg Bye: **{inn['extras_legbye']}** | "
            f"Penalty: **{inn['extras_penalty']}**"
        )
        fow = db.get_fall_of_wickets(inn["innings_id"])
        if fow:
            st.markdown("##### Fall of Wickets")
            st.write(" | ".join(
                f"{f['team_score']}/{f['wicket_number']} ({f['over_ball']} ov)" for f in fow
            ))

    # Innings summary metrics
    summary = analytics.build_match_summary(db, inn["innings_id"])
    st.markdown("##### Innings Summary")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Highest Scorer", f"{summary['highest_scorer']} ({summary['highest_scorer_runs']})")
    s2.metric("Best Bowler", f"{summary['best_bowler']} ({summary['best_bowler_figures']})")
    s3.metric("Boundaries", summary["boundary_count"])
    s4.metric("Run Rate", summary["run_rate"])
    st.divider()

st.markdown("Want deeper visuals? Head to **Match Analytics** for worm graphs, "
            "Manhattan charts, and more.")
if st.button("📊 View Match Analytics"):
    st.session_state[config.SessionKeys.SELECTED_MATCH_FOR_VIEW] = match_id
    st.switch_page("pages/7_Match_Analytics.py")
