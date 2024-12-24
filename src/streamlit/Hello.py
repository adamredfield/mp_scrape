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

def main():
    conn = st.connection('postgresql', type='sql')
    
    user_id = get_user_id(conn)
    if user_id:
        st.session_state['user_id'] = user_id
        st.session_state['conn'] = conn
   
if __name__ == "__main__":
    main() 



