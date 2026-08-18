"""
pages/1_Home.py
----------------
Thin wrapper page so "Home" appears explicitly in Streamlit's sidebar
navigation. All rendering logic lives in app.render_home() to avoid
duplicating code between the main entry point and this page.
"""

import streamlit as st
import utils
from app import render_home

utils.apply_theme()
render_home()
