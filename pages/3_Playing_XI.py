"""
pages/3_Playing_XI.py
-----------------------
Collects the Playing XI for both teams (name, jersey number, captain,
wicket-keeper) and lets the user set batting order via a numeric
"batting order" field per player (a lightweight, Streamlit-native
stand-in for full drag-and-drop reordering). On submit, persists the
squads and creates the first innings based on the toss decision.
"""

import streamlit as st

import config
import utils
from app import get_db

utils.apply_theme()
db = get_db()

match_id = st.session_state.get(config.SessionKeys.CURRENT_MATCH_ID)
if not match_id:
    st.warning("No match selected. Please create a new match first.")
    st.stop()

match = db.get_match(match_id)
team_a_name = db.get_team_name(match["team_a_id"])
team_b_name = db.get_team_name(match["team_b_id"])

utils.section_header(
    "Playing XI",
    f"{team_a_name} vs {team_b_name} - enter 11 players for each team",
    icon="🧢",
)

# Skip if squads already exist (resuming this page after a rerun/back nav)
existing_squad_a = db.get_squad(match_id, match["team_a_id"])
existing_squad_b = db.get_squad(match_id, match["team_b_id"])
if existing_squad_a and existing_squad_b:
    st.info("Playing XI already saved for this match.")
    if st.button("➡️ Proceed to Live Scoring", type="primary"):
        st.switch_page("pages/4_Live_Scoring.py")
    st.stop()


def squad_input_block(team_label, team_name):
    st.markdown(f"#### {team_label}: {team_name}")
    players = []
    for i in range(11):
        with st.expander(f"Player {i + 1}", expanded=(i < 2)):
            c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
            name = c1.text_input("Name", key=f"{team_label}_name_{i}",
                                  placeholder=f"Player {i + 1} name")
            jersey = c2.text_input("Jersey #", key=f"{team_label}_jersey_{i}")
            order = c3.number_input("Bat Order", min_value=1, max_value=11,
                                     value=i + 1, key=f"{team_label}_order_{i}")
            captain = c4.checkbox("Captain", key=f"{team_label}_cap_{i}")
            keeper = c5.checkbox("Keeper", key=f"{team_label}_wk_{i}")
            players.append({
                "name": name, "jersey": jersey, "order": order,
                "captain": captain, "keeper": keeper,
            })
    return players


col_a, col_b = st.columns(2)
with col_a:
    utils.card_start()
    squad_a = squad_input_block("TeamA", team_a_name)
    utils.card_end()
with col_b:
    utils.card_start()
    squad_b = squad_input_block("TeamB", team_b_name)
    utils.card_end()

st.write("")
if st.button("✅ Save Playing XI & Continue", type="primary", use_container_width=True):
    errors = []
    for label, squad in (("Team A", squad_a), ("Team B", squad_b)):
        names = [p["name"].strip() for p in squad if p["name"].strip()]
        if len(names) < 11:
            errors.append(f"{label} needs all 11 player names filled in "
                           f"(only {len(names)} entered).")
        captains = sum(1 for p in squad if p["captain"])
        if captains != 1:
            errors.append(f"{label} must have exactly one Captain selected.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        for team_id, squad in ((match["team_a_id"], squad_a), (match["team_b_id"], squad_b)):
            sorted_squad = sorted(squad, key=lambda p: p["order"])
            for p in sorted_squad:
                player_id = db.get_or_create_player(p["name"], team_id)
                db.add_squad_player(
                    match_id=match_id, team_id=team_id, player_id=player_id,
                    jersey_number=p["jersey"], is_captain=p["captain"],
                    is_keeper=p["keeper"], batting_order=p["order"],
                )

        # Determine batting order from toss decision
        toss_winner = match["toss_winner_team_id"]
        toss_decision = match["toss_decision"]
        other_team = (match["team_b_id"] if toss_winner == match["team_a_id"]
                      else match["team_a_id"])
        if toss_decision == "Bat":
            batting_first, bowling_first = toss_winner, other_team
        else:
            batting_first, bowling_first = other_team, toss_winner

        innings_id = db.create_innings(match_id, 1, batting_first, bowling_first)
        db.update_match_status(match_id, "Live", current_innings=1)

        st.success("Playing XI saved! Match is now Live.")
        st.switch_page("pages/4_Live_Scoring.py")
