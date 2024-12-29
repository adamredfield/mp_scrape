import streamlit as st
import pandas as pd
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import src.analysis.fa_queries as fa_queries
from src.streamlit.chart_utils import create_bar_chart

user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')

if 'fa_view_type' not in st.session_state:
    st.session_state.fa_view_type = "All FAs"
if 'selected_fa' not in st.session_state:
    st.session_state.selected_fa = None

top_fas = fa_queries.get_top_first_ascensionists(conn, user_id=user_id, year_start=1900, year_end=2100)
partnerships = fa_queries.get_collaborative_ascensionists(conn, "All FAs", user_id, year_start=1900, year_end=2100)

st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
            max-width: 100%;
        }
        
        .stDataFrame {
            margin-bottom: 5rem !important;  /* Extra space after dataframe */
        }
        
        .spotify-header {
            font-size: 1.5rem;
            text-align: center;
            margin: 0;
            padding: 0;
            line-height: 1.2;
        }
        
        div.stRadio > div {
            flex-direction: column;
            gap: 0.2rem;
            padding: 0rem;
            margin: 1rem;
            position: relative;  
        }
        
        div.stSelectbox {
            position: absolute !important;  
            left: 130px !important;        
            top: -93px !important;          
            width: 225px !important;       
        }
        
        div.stSelectbox label {
            display: none;
        }

        .element-container:has(.js-plotly-plot) {
            margin-bottom: 2rem !important;  /* Increased space between charts */
        }
        
        .element-container:has(.js-plotly-plot):last-of-type {
            margin-bottom: -2 !important;
        }
        
        .js-plotly-plot .plotly .gtitle {
            margin-top: 0rem !important;
        }   
            
        .list-item {
            padding: 0.5rem 0;
            display: flex;
            justify-content: space-between; 
            align-items: center;
            max-width: 65%; 
            margin: 0 auto; 
            gap: 1rem; 
            position: relative;
            cursor: pointer;
        }
        
        .route-list {
            display: none;
            position: absolute;
            left: 105%;  /* Position to the right */
            top: 0;
            background-color: rgba(26, 26, 26, 0.98);  /* Slightly transparent */
            backdrop-filter: blur(8px);  /* Blur effect behind */
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 1rem;
            z-index: 1000;
            width: 400px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }
            
        .list-item:hover .route-list {
            display: block;
            animation: fadeIn 0.2s ease-in-out;
        }   
        @keyframes fadeIn {
            from { opacity: 0; transform: translateX(-10px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        .list-item:hover .route-list {
            display: block;
        }
        .route-item {
            padding: 0.5rem 0;
            color: rgba(255, 255, 255, 0.9);
            font-size: 0.95em;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);  
        }
        .item-name {
            color: white;
        }
    
        .item-details {
            color: white;
                        margin-right: 2rem;  /* Add right margin to move text left */
        }
        .list-item:hover {
            opacity: 0.8;  /* Subtle hover effect */
        }
        .streamlit-expander {
            border: none !important;
            box-shadow: none !important;
            background-color: transparent !important;
        }

        .streamlit-expanderHeader {
            border-bottom: none !important;
            color: white !important;
            font-size: 1em !important;
            padding: 0.5rem 0 !important;
        }

        .streamlit-expanderContent {
            border: none !important;
            background-color: rgba(255, 255, 255, 0.05) !important;
            border-radius: 4px !important;
            margin-left: 1rem !important;
        }

        .route-item {
            padding: 0.4rem 0.8rem;
            color: #aaa;
            font-size: 0.95em;
        }
            
        .dataframe {
            font-size: 0.9em;
            margin: 0 auto;
            max-width: 800px;
        }
        .dataframe td {
            white-space: normal !important;
            padding: 0.5rem !important;
        }
    """, unsafe_allow_html=True)

controls = st.container()
left, middle, right = controls.columns([1, 0.1, 1])

with left:
    view_type = st.radio(
        "",
        ["All FAs", "Individual FA", "FA Team"],
        horizontal=False,
        key="view_type_radio",
        label_visibility="collapsed"
    )

with middle:
    st.write("")

with right:
    if view_type == "Individual FA":
        selected_value = st.selectbox(
            "",
            options=[fa[0] for fa in top_fas],
            key="fa_individual",
            label_visibility="collapsed"
        )
        if 'selected_fa' not in st.session_state or selected_value != st.session_state.selected_fa:
            st.session_state.selected_fa = selected_value
            st.rerun()
    elif view_type == "FA Team":
        selected_value = st.selectbox(
            "",
            options=[p[0] for p in partnerships],
            key="fa_partnership",
            label_visibility="collapsed"
        )
        if 'selected_fa' not in st.session_state or selected_value != st.session_state.selected_fa:
            st.session_state.selected_fa = selected_value
            st.rerun()
    else:
        st.session_state.selected_fa = "All FAs"

    current_selection = st.session_state.selected_fa or "All FAs"

decades = fa_queries.get_first_ascensionist_by_decade(conn, current_selection, user_id, year_start=1900, year_end=2100)
areas = fa_queries.get_first_ascensionist_areas(conn, current_selection, user_id, year_start=1900, year_end=2100)
grades = fa_queries.get_first_ascensionist_grades(conn, current_selection, user_id, year_start=1900, year_end=2100)

if view_type == "Individual FA":
    partners = fa_queries.get_collaborative_ascensionists(conn, current_selection, user_id)
    
if view_type == "All FAs":
    create_bar_chart(
        title="FAs by Decade", 
        x_data=[decade[0] for decade in decades], 
        y_data=[decade[1] for decade in decades],
        orientation='v',
    )

    st.markdown("<h3 style='text-align: center;'>Most Prolific FAs</h3>", unsafe_allow_html=True)
    st.markdown("<div class='list-container'>", unsafe_allow_html=True)
    for fa, count in top_fas:          
        with st.expander(f"{fa} - {count} routes"):
            routes = fa_queries.get_fa_routes(conn, fa, user_id, year_start=1900, year_end=2100)
            for route in routes:
                st.markdown(
                    f"<div class='route-item'>{route[0]}</div>", 
                    unsafe_allow_html=True
                )
    st.markdown("</div>", unsafe_allow_html=True)
else:
    
    create_bar_chart(
        title="FAs by Decade", 
        x_data=[decade[0] for decade in decades], 
        y_data=[decade[1] for decade in decades],
        orientation='v',
    )
    
    create_bar_chart(
        title="Areas Developed by FA", 
        x_data=[area[0] for area in areas], 
        y_data=[area[1] for area in areas],
        orientation='h',
    )
    
    create_bar_chart(
        title="FAs by Grade", 
        x_data=[grade[0] for grade in grades], 
        y_data=[grade[1] for grade in grades],
        orientation='v',
    )
    
    if view_type == "Individual FA":
        st.markdown("<h3 style='text-align: center;'>Frequent Partners</h3>", unsafe_allow_html=True)
        st.markdown("<div class='list-container'>", unsafe_allow_html=True)
        partners = fa_queries.get_collaborative_ascensionists(conn, current_selection, user_id, year_start=1900, year_end=2100)
        for partner, count in partners:
            with st.expander(f"{partner} - {count} routes"):
                routes = fa_queries.get_partnership_routes(conn, current_selection, partner, user_id, year_start=1900, year_end=2100)
                for route in routes:
                    st.markdown(
                        f"<div class='route-item'>{route[0]}</div>", 
                        unsafe_allow_html=True
                    )
        st.markdown("</div>", unsafe_allow_html=True)
    
    if view_type == "FA Team":
        st.markdown("<h3 style='text-align: center;'>Routes Done Together</h3>", unsafe_allow_html=True)
        
        # Split the partnership into individual names
        climber1, climber2 = current_selection.split(" & ")
        partnership_routes = fa_queries.get_partnership_routes(conn, climber1.strip(), climber2.strip(), user_id, year_start=1900, year_end=2100)
        if partnership_routes:
            df = pd.DataFrame(partnership_routes, columns=['Route'])
            
            st.dataframe(
                df,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No routes found for this partnership.")