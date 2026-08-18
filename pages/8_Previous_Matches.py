"""
pages/8_Previous_Matches.py
------------------------------
Lists every match stored in SQLite with search/filter controls, and
lets the user open a scorecard, jump into analytics, export to
PDF/Excel/CSV, or delete a match record entirely.
"""

import streamlit as st

import config
import utils
import export as export_mod
from app import get_db

utils.apply_theme()
db = get_db()

utils.section_header("Previous Matches", "Browse, search, filter and export match history",
                      icon="📚")

all_matches = db.get_all_matches()
if not all_matches:
    st.info("No matches recorded yet.")
    st.stop()

teams = sorted({m["team_a_name"] for m in all_matches} | {m["team_b_name"] for m in all_matches})
tournaments = sorted({m["tournament_name"] for m in all_matches if m["tournament_name"]})

f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
search_term = f1.text_input("🔎 Search by match name")
team_filter = f2.selectbox("Filter by Team", ["All"] + teams)
tournament_filter = f3.selectbox("Filter by Tournament", ["All"] + tournaments)
status_filter = f4.selectbox("Status", ["All", "Live", "Completed", "Setup"])

filtered = all_matches
if search_term:
    filtered = [m for m in filtered if search_term.lower() in (m["match_name"] or "").lower()]
if team_filter != "All":
    filtered = [m for m in filtered if team_filter in (m["team_a_name"], m["team_b_name"])]
if tournament_filter != "All":
    filtered = [m for m in filtered if m["tournament_name"] == tournament_filter]
if status_filter != "All":
    filtered = [m for m in filtered if m["status"] == status_filter]

st.caption(f"Showing {len(filtered)} of {len(all_matches)} matches")

for m in filtered:
    utils.card_start()
    c1, c2, c3 = st.columns([3, 2, 3])
    with c1:
        status_kind = {"Live": "danger", "Completed": "primary", "Setup": "warning"}.get(m["status"], "primary")
        st.markdown(f"**{m['match_name']}** {utils.pill(m['status'], status_kind)}",
                    unsafe_allow_html=True)
        st.caption(f"{m['team_a_name']} vs {m['team_b_name']}")
    with c2:
        st.caption(f"🏟️ {m.get('venue') or '-'}")
        st.caption(f"📅 {m.get('match_date') or '-'} | {m['match_type']}")
    with c3:
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("View", key=f"view_{m['match_id']}"):
            st.session_state[config.SessionKeys.SELECTED_MATCH_FOR_VIEW] = m["match_id"]
            st.switch_page("pages/5_Scorecard.py")
        if m["status"] == "Live":
            if b2.button("Resume", key=f"resume_{m['match_id']}"):
                st.session_state[config.SessionKeys.CURRENT_MATCH_ID] = m["match_id"]
                st.switch_page("pages/4_Live_Scoring.py")
        else:
            if b2.button("Analytics", key=f"analytics_{m['match_id']}"):
                st.session_state[config.SessionKeys.SELECTED_MATCH_FOR_VIEW] = m["match_id"]
                st.switch_page("pages/7_Match_Analytics.py")
        with b3.popover("Export"):
            fmt = st.radio("Format", ["PDF", "Excel", "CSV"], key=f"fmt_{m['match_id']}",
                           horizontal=True)
            if st.button("Download", key=f"dl_{m['match_id']}"):
                if fmt == "PDF":
                    data, filename = export_mod.export_pdf(db, m["match_id"])
                    mime = "application/pdf"
                elif fmt == "Excel":
                    data, filename = export_mod.export_excel(db, m["match_id"])
                    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                else:
                    data, filename = export_mod.export_csv(db, m["match_id"])
                    mime = "text/csv"
                st.download_button("Save File", data=data, file_name=filename,
                                    mime=mime, key=f"savefile_{m['match_id']}_{fmt}")
        if b4.button("🗑️ Delete", key=f"delete_{m['match_id']}"):
            st.session_state[f"confirm_delete_{m['match_id']}"] = True

    if st.session_state.get(f"confirm_delete_{m['match_id']}"):
        st.warning(f"Delete '{m['match_name']}' permanently? This cannot be undone.")
        dc1, dc2 = st.columns(2)
        if dc1.button("Yes, Delete", key=f"confirmyes_{m['match_id']}", type="primary"):
            db.delete_match(m["match_id"])
            st.session_state[f"confirm_delete_{m['match_id']}"] = False
            st.rerun()
        if dc2.button("Cancel", key=f"confirmno_{m['match_id']}"):
            st.session_state[f"confirm_delete_{m['match_id']}"] = False
            st.rerun()

    utils.card_end()
