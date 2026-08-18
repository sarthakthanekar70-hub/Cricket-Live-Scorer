"""
pages/9_Settings.py
---------------------
Lightweight settings page: theme info, database maintenance actions,
and app metadata. Kept intentionally simple since this is a local
single-user scoring tool rather than a multi-tenant SaaS product.
"""

import os
import streamlit as st

import config
import utils
from app import get_db

utils.apply_theme()
db = get_db()

utils.section_header("Settings", "App preferences and database maintenance", icon="⚙️")

utils.card_start()
st.markdown("#### Appearance")
st.write("This app ships with a single professionally designed dark theme "
         "for consistency across all pages.")
st.color_picker("Primary Accent Color", config.THEME["primary"], disabled=True)
utils.card_end()

utils.card_start()
st.markdown("#### Database")
st.write(f"Database file location: `{config.DATABASE_PATH}`")
if os.path.exists(config.DATABASE_PATH):
    size_kb = os.path.getsize(config.DATABASE_PATH) / 1024
    st.write(f"Current size: **{size_kb:.1f} KB**")

all_matches = db.get_all_matches()
st.write(f"Total matches stored: **{len(all_matches)}**")

st.markdown("##### ⚠️ Danger Zone")
if st.button("Delete ALL match data", type="secondary"):
    st.session_state["confirm_wipe_all"] = True

if st.session_state.get("confirm_wipe_all"):
    st.error("This will permanently delete every match, innings, and ball-by-ball "
             "record in the database. This cannot be undone.")
    wc1, wc2 = st.columns(2)
    if wc1.button("Yes, wipe everything", type="primary"):
        for m in all_matches:
            db.delete_match(m["match_id"])
        st.session_state["confirm_wipe_all"] = False
        st.success("All match data deleted.")
        st.rerun()
    if wc2.button("Cancel"):
        st.session_state["confirm_wipe_all"] = False
        st.rerun()
utils.card_end()

utils.card_start()
st.markdown("#### About This Build")
st.write(f"**{config.APP_NAME}** v{config.APP_VERSION}")
st.write("Built with Streamlit, SQLite, pandas, NumPy, and Plotly.")
utils.card_end()
