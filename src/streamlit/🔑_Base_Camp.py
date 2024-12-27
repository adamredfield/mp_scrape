import streamlit as st

st.set_page_config(
    page_title="Your 2024 Climbing Racked",
    page_icon="🧗‍♂️",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)
from src.streamlit.streamlit_helper_functions import get_user_id
from src.streamlit.styles import get_navigation_style

def main():

    st.markdown(get_navigation_style(), unsafe_allow_html=True)

    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False

    conn = st.connection('postgresql', type='sql')
    
    if not st.session_state['authenticated']:
        user_id = get_user_id(conn)
        if user_id:
            st.session_state['user_id'] = user_id
            st.session_state['conn'] = conn
            st.session_state['authenticated'] = True
            st.switch_page("pages/📊_Grade_Distribution.py")

if __name__ == "__main__":
    main() 



