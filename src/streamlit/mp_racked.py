import streamlit as st

st.set_page_config(
    page_title="Your 2024 Climbing Racked",
    page_icon="🧗‍♂️",
    layout="centered",
    initial_sidebar_state="collapsed",
)


import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)
from src.streamlit.streamlit_helper_functions import get_user_id
from src.streamlit.styles import get_navigation_style

st.markdown(get_navigation_style(), unsafe_allow_html=True)

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if st.session_state['authenticated']:
    with st.sidebar:
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

conn = st.connection('postgresql', type='sql')

if not st.session_state['authenticated']:
    def empty_page():
        pass
    pg = st.navigation([st.Page(empty_page, title="Mountain Project Racked")], position="hidden")
    pg.run()

    user_id = get_user_id(conn)
    if user_id:
        st.session_state['user_id'] = user_id
        st.session_state['conn'] = conn
        st.session_state['authenticated'] = True
        st.rerun()

    st.stop()

pg = st.navigation({
    "Overview": [
        st.Page("pages/grade_pyramid.py", 
                title="Grade Pyramid of Giza", 
                icon="📊", 
                default=True),
        st.Page("pages/going_the_distance.py", 
                title="Going the Distance", 
                icon="🏃"),
        st.Page("pages/classics_chaser.py", 
                title="Classics Chaser", 
                icon="⭐"),
    ],
    "Analysis": [
        st.Page("pages/wall_rat_stats.py", 
                title="Wall Rat Stats", 
                icon="🐀"),
        st.Page("pages/fa_legacy.py", 
                title="FA Legacy", 
                icon="⚡"),
        st.Page("pages/dialing_it_in.py", 
                title="Dialing It In", 
                icon="🎯"),
    ],
})

try:
    pg.run()
except Exception as e:
    st.error(f"Something went wrong: {str(e)}", icon=":material/error:")
