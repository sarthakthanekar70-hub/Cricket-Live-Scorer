"""
pages/6_Player_Statistics.py
------------------------------
Aggregate career statistics dashboard, built from the `statistics`
table (rebuilt automatically whenever a match is completed). Includes
sortable batting/bowling leaderboards and a per-player detail view.
"""

import streamlit as st
import plotly.express as px

import config
import utils
from app import get_db

utils.apply_theme()
db = get_db()

utils.section_header("Player Statistics Dashboard",
                      "Career batting & bowling statistics across all matches",
                      icon="📊")

all_stats = db.get_all_statistics()

if not all_stats:
    st.info("No statistics available yet. Complete a match to populate this dashboard.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["Batting Leaders", "Bowling Leaders", "Player Profile"])

with tab1:
    bat_rows = [{
        "Player": s["player_name"], "Matches": s["matches"],
        "Runs": s["runs"], "Balls": s["balls_faced"],
        "Avg": round(utils.safe_div(s["runs"], max(s["innings_batted"] - 0, 1)), 2),
        "SR": utils.calc_strike_rate(s["runs"], s["balls_faced"]),
        "4s": s["fours"], "6s": s["sixes"],
        "50s": s["fifties"], "100s": s["hundreds"],
        "HS": s["highest_score"],
    } for s in all_stats]
    bat_rows.sort(key=lambda r: r["Runs"], reverse=True)
    st.dataframe(bat_rows, use_container_width=True, hide_index=True)

    top10 = bat_rows[:10]
    if top10:
        fig = px.bar(top10, x="Player", y="Runs", color="Player",
                     title="Top Run Scorers", template=config.PLOTLY_TEMPLATE)
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    bowl_rows = [{
        "Player": s["player_name"], "Matches": s["matches"],
        "Wickets": s["wickets"], "Runs Conceded": s["runs_conceded"],
        "Overs": utils.balls_to_overs_str(s["balls_bowled"]),
        "Economy": utils.calc_economy(s["runs_conceded"], s["balls_bowled"]),
        "Best": s["best_bowling"] or "-",
    } for s in all_stats]
    bowl_rows.sort(key=lambda r: r["Wickets"], reverse=True)
    st.dataframe(bowl_rows, use_container_width=True, hide_index=True)

    top10_bowl = [r for r in bowl_rows if r["Wickets"] > 0][:10]
    if top10_bowl:
        fig2 = px.bar(top10_bowl, x="Player", y="Wickets", color="Player",
                      title="Top Wicket Takers", template=config.PLOTLY_TEMPLATE)
        st.plotly_chart(fig2, use_container_width=True)

with tab3:
    player_names = {s["player_name"]: s["player_id"] for s in all_stats}
    selected_name = st.selectbox("Select Player", list(player_names.keys()))
    stat = db.get_player_statistics(player_names[selected_name])
    if stat:
        st.markdown(f"### {stat['player_name']}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Matches", stat["matches"])
        c2.metric("Runs", stat["runs"])
        c3.metric("Wickets", stat["wickets"])
        c4.metric("Highest Score", stat["highest_score"])

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Batting Avg", round(utils.safe_div(
            stat["runs"], max(stat["innings_batted"], 1)), 2))
        c6.metric("Strike Rate", utils.calc_strike_rate(stat["runs"], stat["balls_faced"]))
        c7.metric("Economy", utils.calc_economy(stat["runs_conceded"], stat["balls_bowled"]))
        c8.metric("Best Bowling", stat["best_bowling"] or "-")

        st.markdown("---")
        st.caption("🔮 AI Feature Placeholder: Player Performance Prediction")
        import analytics as _a
        st.write(_a.player_performance_prediction_placeholder(stat["player_name"]))
