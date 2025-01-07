import streamlit as st
import pandas as pd
from streamlit_float import *
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import src.analysis.mp_racked_metrics as metrics
from src.streamlit.styles import get_spotify_style
from src.streamlit.filters import render_filters
from src.analysis.filters_ctes import available_years

user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')

if 'filter_expander_state' not in st.session_state:
    st.session_state.filter_expander_state = False 
if 'offset' not in st.session_state:
    st.session_state.offset = 0
if 'all_loaded_routes' not in st.session_state:
    st.session_state.all_loaded_routes = []
if 'jump_index' not in st.session_state:
    st.session_state.jump_index = None
if 'previous_filters' not in st.session_state:
    st.session_state.previous_filters = None

ROUTES_PER_PAGE = 25

st.markdown(get_spotify_style(), unsafe_allow_html=True)

st.markdown("""
    <style>
        /* Remove extra padding at the top */
        .block-container {
            padding-top: 4rem !important;
        }     
    </style>
""", unsafe_allow_html=True)

col1, col2 = st.columns(2)

st.markdown("""
    <style>
        /* Style for expanded filter */
        .streamlit-expanderContent {
            background-color: black !important;
        }
        
        /* Optional: style the expander header too */
        .streamlit-expanderHeader {
            background-color: black !important;
        }
            
        .stButton {
            margin-bottom: 3rem !important;
            position: relative;
            z-index: 2;
        }

    </style>
""", unsafe_allow_html=True)

filter_container = st.container()

with filter_container:
    years_df = available_years(conn, user_id)
    default_years = (2000, 2100)
    filters = render_filters(
        df=years_df,
        filters_to_include=['route_tag', 'route_type', 'climbed_routes', 'fa', 'grade', 'fa_year'],
        filter_title="Choose your filters",
        conn=conn,
        user_id=user_id,
        default_years=default_years
    )

    tag_selections = filters.get('tag_selections', {})
    route_types = filters.get('route_type')
    climbed_filter = filters.get('climbed_filter', 'All Routes')
    fa_selection = filters.get('fa_filter', 'All FAs')
    grade_system, grade_range = filters.get('grade_filter', (None, None)) 
    fa_year_values = filters.get('fa_year', [None, None])
    fa_year_start = fa_year_values[0] 
    fa_year_end = fa_year_values[1]


st.markdown(get_spotify_style(), unsafe_allow_html=True)

current_filters = {
    'tag_selections': tag_selections,
    'route_types': route_types,
    'climbed_filter': climbed_filter,
    'fa_selection': fa_selection,
    'grade_filter': (grade_system, grade_range),
    'fa_year_filter': (fa_year_start, fa_year_end)
}


if st.session_state.previous_filters != current_filters:
    st.session_state.offset = 0
    st.session_state.all_loaded_routes = []
    st.session_state.previous_filters = current_filters
    st.rerun()

routes_container = st.container(height=1000, border=False)
with routes_container:
    new_routes = metrics.get_routes_for_route_finder(
        conn,
        offset=st.session_state.offset, 
        routes_per_page=ROUTES_PER_PAGE, 
        tag_selections=tag_selections, 
        route_types=route_types, 
        climbed_filter=climbed_filter, 
        user_id=user_id, 
        fa_selection=fa_selection, 
        grade_system=grade_system, 
        grade_range=grade_range, 
        fa_year_start=fa_year_start, 
        fa_year_end=fa_year_end
    )
    
    if not new_routes.empty:
        new_records = new_routes.to_dict('records')
        existing_ids = {route['id'] for route in st.session_state.all_loaded_routes}
        new_unique_routes = [
            route for route in new_records 
            if route['id'] not in existing_ids
        ]
        st.session_state.all_loaded_routes.extend(new_unique_routes)
    for i, route in enumerate(st.session_state.all_loaded_routes):
        climbed_icon = "✅ " if route['climbed'] else ""
        expander_title = f' **{climbed_icon}{i + 1}. {route['route_name']}** - {route['main_area']} :green[{route['grade']}]'
        
        with st.expander(expander_title, expanded=False):
            col1, col2 = st.columns([1, 2])
            
            #with col1:
                #if route['photo_url']:
                #    load_and_display_image(route['id'], route['photo_url'], route['route_name'])
            
            with col2:
                length_display = f"{route['length_ft']:.0f}" if pd.notna(route['length_ft']) else ""
                pitches_display = str(route['pitches']) if pd.notna(route['pitches']) else ""

                st.markdown(f"""
                    - **Location:** {route['specific_location']}
                    - **Type:** {route['route_type']}
                    - **Choss Index:** ⭐ {route['choss_adjusted_benchmark']:.2f} ({route['num_votes']} votes)
                    - **Length:** {length_display} ft - {pitches_display} pitches
                    - **Styles:** {route['styles']}
                    - **Features:** {route['features']}
                    - **Descriptors:** {route['descriptors']}
                    - **Rock Type:** {route['rock_type']}
                """)
                
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Load More Routes"):
            st.session_state.offset += ROUTES_PER_PAGE
            st.rerun()

filter_container.float(
    float_css_helper(
        top="4rem",
        background="black",
        padding=".25rem",
        left="49%",
        width="min(800px, 85vw)",
        transform="translateX(-50%)",
        position="fixed",
        z_index="999"
    )
)

routes_container.float(
    float_css_helper(
        top="10rem",
        bottom="10rem",
        left="49%",
        transform="translateX(-50%)",
        width="min(800px, 85vw)",
        height="100vh",
        padding=".25rem",
        padding_bottom="15rem",
        overflow_y="auto",
        overflow_x="hidden",
        z_index="1" 
    )
)