import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import streamlit as st
from src.streamlit.streamlit_helper_functions import get_user_id
from styles import get_all_styles, get_wrapped_styles, get_diamond_styles, get_routes_styles

from src.streamlit.app_pages.most_climbed_route import page_most_climbed_route
from src.streamlit.app_pages.first_ascents import page_first_ascents
from src.streamlit.app_pages.bigwalls import page_bigwall_routes
from src.streamlit.app_pages.total_length import page_total_length
from src.streamlit.app_pages.biggest_day import page_biggest_day
from src.streamlit.app_pages.top_routes import page_top_routes
from src.streamlit.app_pages.areas import page_areas_breakdown
from src.streamlit.app_pages.grade_distribution import page_grade_distribution

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

conn = st.connection('postgresql', type='sql')

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 0

def main():
    
    user_id = get_user_id(conn)
    if not user_id:
        return

    if 'page' not in st.session_state:
        st.session_state.page = 0

    # Page mapping
    pages = {
        0: lambda: page_most_climbed_route(user_id, conn),
        1: lambda: page_first_ascents(user_id, conn),
        2: lambda: page_bigwall_routes(user_id, conn),
        3: lambda: page_grade_distribution(user_id, conn),
        4: lambda: page_areas_breakdown(user_id, conn)
        #8: lambda: page_total_length(user_id),
        #7: lambda: page_biggest_day(user_id),
        #5: lambda: page_top_routes(user_id),


    }

    # Apply styles based on current page
    current_page = st.session_state.page
    if current_page in [0, 1]:  # Total length and biggest day pages
        st.markdown(get_wrapped_styles(), unsafe_allow_html=True)
    elif current_page in [2, 3]:  # Total routes and most climbed pages
        st.markdown(get_diamond_styles(), unsafe_allow_html=True)
    elif current_page in [4, 5, 6]:  # Top routes, areas, and grades pages
        st.markdown(get_routes_styles(), unsafe_allow_html=True)
    else:
        st.markdown(get_all_styles(), unsafe_allow_html=True)

    # Display current page
    if current_page in pages:
        pages[current_page]()
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 18, 1])
    
    with col1:
        if st.session_state.page > 0:
            if st.button("← Prev"):
                st.session_state.page -= 1
                st.rerun()
    
    with col3:
        if st.session_state.page < len(pages) - 1:
            if st.button("Next →"):
                st.session_state.page += 1
                st.rerun()

if __name__ == "__main__":
    main() 

