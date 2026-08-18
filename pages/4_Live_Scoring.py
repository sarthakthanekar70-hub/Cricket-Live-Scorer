"""
pages/4_Live_Scoring.py
-------------------------
The heart of the application. Renders the live scoreboard, ball-input
button panel, batting/bowling scorecards, partnership, and over
summary for the innings currently in progress. All scoring events are
delegated to scorer.Scorer so this file stays purely presentational.
"""

import streamlit as st

import config
import utils
import analytics
from app import get_db
from scorer import Scorer

utils.apply_theme()
db = get_db()

match_id = st.session_state.get(config.SessionKeys.CURRENT_MATCH_ID)
if not match_id:
    st.warning("No match selected. Go to Home and create or resume a match.")
    st.stop()

match = db.get_match(match_id)
if match["status"] == "Setup":
    st.warning("Playing XI has not been set for this match yet.")
    if st.button("Go to Playing XI"):
        st.switch_page("pages/3_Playing_XI.py")
    st.stop()

innings_list = db.get_innings_by_match(match_id)
current_innings_number = match["current_innings"]
innings = next((i for i in innings_list if i["innings_number"] == current_innings_number), None)

if innings is None:
    st.error("Could not locate the current innings record.")
    st.stop()

innings_id = innings["innings_id"]
batting_team_id = innings["batting_team_id"]
bowling_team_id = innings["bowling_team_id"]
batting_team_name = db.get_team_name(batting_team_id)
bowling_team_name = db.get_team_name(bowling_team_id)

scorer = Scorer(db, innings_id)

# --------------------------------------------------------------------------
# HEADER
# --------------------------------------------------------------------------
utils.section_header(
    f"{match['match_name']} - Live Scoring",
    f"{db.get_team_name(match['team_a_id'])} vs {db.get_team_name(match['team_b_id'])} | "
    f"{match.get('venue') or ''} | Innings {current_innings_number}",
    icon="🏏",
)

# ==========================================================================
# STAGE 0: SELECT OPENERS & BOWLER (only when innings has not started yet)
# ==========================================================================
if not innings["current_striker_id"]:
    st.markdown("#### Select Openers & Opening Bowler")
    batting_squad = db.get_squad(match_id, batting_team_id)
    bowling_squad = db.get_squad(match_id, bowling_team_id)

    if not batting_squad or not bowling_squad:
        st.error("Playing XI missing for one of the teams.")
        st.stop()

    bat_names = {p["player_name"]: p["player_id"] for p in batting_squad}
    bowl_names = {p["player_name"]: p["player_id"] for p in bowling_squad}

    with st.form("openers_form"):
        c1, c2, c3 = st.columns(3)
        striker_name = c1.selectbox("On Strike (Batter 1)", list(bat_names.keys()))
        non_striker_name = c2.selectbox("Non-Striker (Batter 2)",
                                         [n for n in bat_names if n != striker_name])
        bowler_name = c3.selectbox("Opening Bowler", list(bowl_names.keys()))
        start_submit = st.form_submit_button("Start Innings", type="primary",
                                              use_container_width=True)
    if start_submit:
        scorer.set_openers(bat_names[striker_name], bat_names[non_striker_name],
                            bowl_names[bowler_name])
        st.rerun()
    st.stop()

# ==========================================================================
# REFRESH LIVE STATE
# ==========================================================================
innings = db.get_innings(innings_id)
striker_id = innings["current_striker_id"]
non_striker_id = innings["current_non_striker_id"]
bowler_id = innings["current_bowler_id"]
last_bowler_id = innings["last_bowler_id"]
balls_this_over = innings["balls_this_over"] or 0

batting_squad = db.get_squad(match_id, batting_team_id)
bowling_squad = db.get_squad(match_id, bowling_team_id)
bat_names_map = {p["player_id"]: p["player_name"] for p in batting_squad}
bowl_names_map = {p["player_id"]: p["player_name"] for p in bowling_squad}

# ==========================================================================
# STAGE: NEED NEW BOWLER (an over just completed)
# ==========================================================================
over_just_completed = (balls_this_over == 0 and (innings["total_balls"] or 0) > 0
                        and bowler_id == last_bowler_id)

if over_just_completed:
    st.markdown("#### 🔄 Select Bowler for the New Over")
    options = {p["player_name"]: p["player_id"] for p in bowling_squad
               if p["player_id"] != last_bowler_id}
    with st.form("new_bowler_form"):
        new_bowler_name = st.selectbox("Next Bowler", list(options.keys()))
        confirm_bowler = st.form_submit_button("Confirm Bowler", type="primary",
                                                use_container_width=True)
    if confirm_bowler:
        scorer.change_bowler(options[new_bowler_name])
        st.rerun()
    st.stop()

# ==========================================================================
# SCOREBOARD
# ==========================================================================
target = innings["target"]
total_balls = innings["total_balls"] or 0
total_overs_limit = match["total_overs"]
max_balls = utils.max_balls_for_match(total_overs_limit)

crr = utils.calc_run_rate(innings["total_runs"] or 0, total_balls)

utils.card_start()
sb1, sb2, sb3 = st.columns([2, 2, 2])
with sb1:
    st.markdown(f"### {batting_team_name}")
    st.markdown(f"<div class='cls-score-big'>{innings['total_runs']}/"
                f"{innings['total_wickets']}</div>", unsafe_allow_html=True)
    overs_display = utils.balls_to_overs_str(total_balls)
    overs_limit_display = total_overs_limit if total_overs_limit else "∞"
    st.markdown(f"Overs: **{overs_display} / {overs_limit_display}**")
with sb2:
    st.metric("Current Run Rate", crr)
    if target:
        runs_needed = max(target - (innings["total_runs"] or 0), 0)
        balls_remaining = max((max_balls or 0) - total_balls, 0)
        rrr = utils.calc_required_run_rate(runs_needed, balls_remaining)
        st.metric("Required Run Rate", rrr)
with sb3:
    if target:
        st.metric("Target", target)
        st.metric("Runs Needed", runs_needed)
        st.metric("Balls Remaining", balls_remaining)
        win_prob = utils.calc_win_probability(
            innings["total_runs"] or 0, target,
            overs_left=(balls_remaining / config.BALLS_PER_OVER),
            wickets_left=10 - (innings["total_wickets"] or 0),
        )
        st.metric("Win Probability (placeholder)", f"{win_prob}%")
    else:
        st.caption("First innings in progress - target will appear once set.")
utils.card_end()

# Striker / non-striker / bowler quick view
qc1, qc2, qc3 = st.columns(3)
striker_bat = next((b for b in db.get_batting_card(innings_id) if b["player_id"] == striker_id), None)
nonstriker_bat = next((b for b in db.get_batting_card(innings_id) if b["player_id"] == non_striker_id), None)
bowler_bowl = next((b for b in db.get_bowling_card(innings_id) if b["player_id"] == bowler_id), None)

with qc1:
    if striker_bat:
        st.info(f"🏏 **{bat_names_map.get(striker_id,'?')}\\*** — "
                f"{striker_bat['runs']} ({striker_bat['balls']})")
with qc2:
    if nonstriker_bat:
        st.info(f"🏏 {bat_names_map.get(non_striker_id,'?')} — "
                f"{nonstriker_bat['runs']} ({nonstriker_bat['balls']})")
with qc3:
    if bowler_bowl:
        st.warning(f"🎯 {bowl_names_map.get(bowler_id,'?')} — "
                   f"{bowler_bowl['wickets']}/{bowler_bowl['runs_conceded']} "
                   f"({utils.balls_to_overs_str(bowler_bowl['balls'])})")

st.write("")

# ==========================================================================
# WICKET DETAIL FLOW
# ==========================================================================
if st.session_state.get("awaiting_wicket_details"):
    st.markdown("#### 🎯 Wicket Details")
    with st.form("wicket_form"):
        dismissal_type = st.selectbox("Dismissal Type", config.DISMISSAL_TYPES)
        who_out_name = st.selectbox(
            "Who got out",
            [bat_names_map.get(striker_id, "Striker"), bat_names_map.get(non_striker_id, "Non-Striker")],
        )
        runs_before_dismissal = st.number_input("Runs completed before dismissal",
                                                 min_value=0, max_value=3, value=0)
        fielder_name = st.selectbox("Fielder (optional)",
                                     ["None"] + list(bowl_names_map.values()))

        remaining_batters = [
            p for p in batting_squad
            if p["player_id"] not in (striker_id, non_striker_id)
            and not any(b["player_id"] == p["player_id"] and b["is_out"]
                        for b in db.get_batting_card(innings_id))
        ]
        next_batter_name = None
        wickets_after = (innings["total_wickets"] or 0) + 1
        if wickets_after < 10 and remaining_batters:
            next_batter_name = st.selectbox(
                "Next Batter", [p["player_name"] for p in remaining_batters]
            )
        confirm_wicket = st.form_submit_button("Confirm Wicket", type="primary",
                                                use_container_width=True)

    if confirm_wicket:
        who_out_id = striker_id if who_out_name == bat_names_map.get(striker_id) else non_striker_id
        fielder_id = None
        if fielder_name != "None":
            fielder_id = {v: k for k, v in bowl_names_map.items()}.get(fielder_name)
        next_batter_id = None
        if next_batter_name:
            next_batter_id = next(p["player_id"] for p in remaining_batters
                                   if p["player_name"] == next_batter_name)

        scorer.process_ball(
            runs=runs_before_dismissal, is_wicket=True,
            dismissal_type=dismissal_type, dismissed_player_id=who_out_id,
            fielder_id=fielder_id, next_batter_id=next_batter_id,
        )
        st.session_state["awaiting_wicket_details"] = False
        st.rerun()

    if st.button("Cancel"):
        st.session_state["awaiting_wicket_details"] = False
        st.rerun()
    st.stop()

# ==========================================================================
# BALL INPUT PANEL
# ==========================================================================
utils.section_header("Ball Input", icon="🎮")

run_cols = st.columns(7)
run_labels = [0, 1, 2, 3, 4, 5, 6]
for col, r in zip(run_cols, run_labels):
    if col.button(str(r), key=f"run_{r}", use_container_width=True):
        scorer.process_ball(runs=r)
        st.rerun()

extra_cols = st.columns(5)
extra_defs = [("Wide", "Wide"), ("No Ball", "No Ball"), ("Bye", "Bye"),
              ("Leg Bye", "Leg Bye"), ("Dot Ball", None)]
for col, (label, extra_type) in zip(extra_cols, extra_defs):
    if col.button(label, key=f"extra_{label}", use_container_width=True):
        scorer.process_ball(runs=0, extra_type=extra_type)
        st.rerun()

action_cols = st.columns(4)
if action_cols[0].button("🔴 Wicket", key="wicket_btn", use_container_width=True):
    st.session_state["awaiting_wicket_details"] = True
    st.rerun()
if action_cols[1].button("↩️ Undo", key="undo_btn", use_container_width=True):
    if scorer.undo_last_ball():
        st.success("Last ball undone.")
    else:
        st.info("Nothing to undo.")
    st.rerun()
if action_cols[2].button("⏭️ End Over", key="end_over_btn", use_container_width=True,
                          help="Overs complete automatically after 6 legal balls."):
    st.info("Overs complete automatically once 6 legal balls are bowled.")
if action_cols[3].button("🏁 Finish Match", key="finish_match_btn",
                          use_container_width=True):
    st.session_state["confirm_finish_match"] = True
    st.rerun()

st.write("")

# Next Innings / Finish Match logic ----------------------------------------
innings = db.get_innings(innings_id)
if scorer.is_innings_over() and current_innings_number == 1:
    st.success("First innings complete!")
    if st.button("➡️ Start Next Innings", type="primary", use_container_width=True):
        scorer.finish_innings()
        target = (innings["total_runs"] or 0) + 1
        new_innings_id = db.create_innings(match_id, 2, bowling_team_id,
                                            batting_team_id, target=target)
        db.update_match_status(match_id, "Live", current_innings=2)
        st.rerun()

if scorer.is_innings_over() and current_innings_number == 2:
    st.success("Second innings complete! You can finish the match to view the result.")

if st.session_state.get("confirm_finish_match"):
    st.warning("Are you sure you want to finish this match? This will lock in the result.")
    fc1, fc2 = st.columns(2)
    if fc1.button("Yes, Finish Match", type="primary", use_container_width=True):
        scorer.finish_innings()
        db.update_match_status(match_id, "Completed")
        result = analytics.determine_result(db, match_id)
        if result:
            db.save_result(match_id, result["winner_team_id"], result["result_type"],
                            result["margin"], result["player_of_match_id"], result["summary"])
            for pid in {b["player_id"] for inn in db.get_innings_by_match(match_id)
                        for b in db.get_batting_card(inn["innings_id"])} | \
                       {b["player_id"] for inn in db.get_innings_by_match(match_id)
                        for b in db.get_bowling_card(inn["innings_id"])}:
                db.rebuild_player_statistics(pid)
        st.session_state["confirm_finish_match"] = False
        st.session_state[config.SessionKeys.SELECTED_MATCH_FOR_VIEW] = match_id
        st.switch_page("pages/5_Scorecard.py")
    if fc2.button("Cancel", use_container_width=True):
        st.session_state["confirm_finish_match"] = False
        st.rerun()

st.divider()

# ==========================================================================
# LIVE SCORECARDS
# ==========================================================================
tab1, tab2, tab3, tab4 = st.tabs(["Batting", "Bowling", "Partnership", "Over Summary"])

with tab1:
    batting_card = db.get_batting_card(innings_id)
    rows = []
    for b in batting_card:
        rows.append({
            "Batter": b["player_name"],
            "Status": b["dismissal_type"] if b["is_out"] else b["status"],
            "Runs": b["runs"], "Balls": b["balls"],
            "4s": b["fours"], "6s": b["sixes"],
            "SR": utils.calc_strike_rate(b["runs"], b["balls"]),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

with tab2:
    bowling_card = db.get_bowling_card(innings_id)
    rows = []
    for b in bowling_card:
        rows.append({
            "Bowler": b["player_name"], "Overs": utils.balls_to_overs_str(b["balls"]),
            "Maidens": b["maidens"], "Runs": b["runs_conceded"], "Wickets": b["wickets"],
            "Economy": utils.calc_economy(b["runs_conceded"], b["balls"]),
            "Wide": b["wides"], "No Ball": b["no_balls"],
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

with tab3:
    partnership = db.get_active_partnership(innings_id)
    if partnership:
        b1_name = bat_names_map.get(partnership["batter1_id"], "?")
        b2_name = bat_names_map.get(partnership["batter2_id"], "?")
        st.markdown(f"**Current Partnership ({utils.ordinal(partnership['wicket_number'])} wkt): "
                    f"{partnership['runs']} runs off {partnership['balls']} balls**")
        pc1, pc2 = st.columns(2)
        pc1.metric(b1_name, partnership["batter1_runs"])
        pc2.metric(b2_name, partnership["batter2_runs"])
    all_partnerships = db.get_partnerships(innings_id)
    st.markdown("##### All Partnerships")
    st.dataframe([{
        "Wicket": p["wicket_number"],
        "Batters": f"{bat_names_map.get(p['batter1_id'],'?')} & {bat_names_map.get(p['batter2_id'],'?')}",
        "Runs": p["runs"], "Balls": p["balls"],
    } for p in all_partnerships], use_container_width=True, hide_index=True)

with tab4:
    overs_data = db.get_overs(innings_id)
    for o in overs_data[-5:][::-1]:
        st.markdown(f"**Over {o['over_number'] + 1}** ({bowl_names_map.get(o['bowler_id'], '?')}) "
                    f"— Runs: {o['runs_in_over']} | Wickets: {o['wickets_in_over']}"
                    f"{' | Maiden' if o['is_maiden'] else ''}")
    fow = db.get_fall_of_wickets(innings_id)
    if fow:
        st.markdown("##### Fall of Wickets")
        st.write(" | ".join(f"{f['team_score']}/{f['wicket_number']} ({f['over_ball']})" for f in fow))
