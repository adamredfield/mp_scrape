import os
import sys
import streamlit as st
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import src.analysis.mp_racked_metrics as metrics
from src.streamlit.filters import render_filters
from src.analysis.filters_ctes import available_years
from src.analysis.mp_racked_metrics import tag_relationships
from streamlit_extras.stylable_container import stylable_container
from src.streamlit.styles import get_spotify_style


st.markdown(get_spotify_style(), unsafe_allow_html=True)

user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')

years_df = available_years(conn, user_id)
filters = render_filters(
    df=years_df,
    filters_to_include=['date', 'route_type'],
    filter_title="Choose your filters",
    conn=conn,
    user_id=user_id 
)

start_year = filters.get('year_start')
end_year = filters.get('year_end')
tag_selections = filters.get('tag_selections', {})
route_types = filters.get('route_type')

st.markdown("""
    <style>
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 10rem !important;  
        }
            [data-testid="stExpander"] {
            margin-bottom: -.75rem !important;  
        }
        
        .tag-name {
            color: #EEEEEE;
            font-size: 1rem;
            min-width: 120px;
        }
        
        .bar-container {
                flex-grow: 1;
                margin: 0; 
                padding: 0;
        }
        
        .frequency-bar {
            background: #1ed760;
            height: 4px;
            border-radius: 2px;
        }
        
        .count {
            color: #F5F5F5;
            font-size: 0.9rem;
            min-width: 80px;
            text-align: right;
        }  

    </style>
""", unsafe_allow_html=True)

def create_drill_down_bars(conn,tag_type, related_data, user_id, year_start, year_end, route_types):
    if 'selected_tag' not in st.session_state:
        st.session_state.selected_tag = None

    if not st.session_state.selected_tag:
        tag_data = metrics.top_tags(
            conn, 
            tag_type, 
            user_id=user_id,
            year_start=year_start,
            year_end=end_year
        )
    
        tag_df = pd.DataFrame(tag_data, columns=['Type', 'Tag', 'Count']).head(10)
        counts = tag_df['Count'].fillna(0)
        max_count = counts.max() if len(counts) > 0 else 1

        with stylable_container(
            key="tag_chart",
            css_styles="""
                [data-testid="stVerticalBlock"] > div {
                    position: relative;
                    margin-bottom: 5px;
                    height: 10px;
                }
                
                .stButton {
                    position: absolute !important;
                    top:  10px !important;
                    left: 0 !important;
                    width: 100% !important;
                    height: 100% !important;  /* Fill container height */
                    z-index: 2 !important;
                    margin: 0 !important;
                    padding: 8px !important;  /* Remove padding from button container */
                }
                
                .stButton button {
                    width: 100% !important;
                    height: 100% !important;
                    background: none !important;
                    border: none !important;
                    cursor: pointer !important;
                    padding: 8px !important;  /* Add padding to button element instead */
                }

                .tag-item {
                    position: absolute !important;
                    top: 0 !important;
                    left: 0 !important;
                    width: 100% !important;
                    height: 100% !important; 
                    margin: 0 !important;
                    padding: 8px !important;
                    pointer-events: none !important;
                    z-index: 1 !important;
                    display: flex !important;
                    align-items: center !important;
                }

                .stButton button:hover {
                    background-color: rgba(30, 215, 96, 0.1) !important;
                }
                """
        ):

            for i, (_, tag, count) in enumerate(zip(tag_df['Type'], tag_df['Tag'], counts), 1):
                percentage = (count / max_count) * 100 if max_count > 0 else 0
                
                row = st.container()
                with row:
                    if st.button("", key=f"btn_{tag}", use_container_width=True):
                        st.session_state.selected_tag = tag
                        st.rerun()
                    
                    st.markdown(f"""
                        <div class="tag-item"">
                            <div class="tag-name">{i}. {tag}</div>
                            <div class="bar-container">
                                <div class="frequency-bar" style="width: {percentage}%;"></div>
                            </div>
                            <div class="count">{int(count)} routes</div>
                        </div>
                    """, unsafe_allow_html=True)
    else:
        related_data = tag_relationships(
            conn=conn,
            primary_type=tag_type,
            secondary_type=related_data,
            route_types=route_types,
            year_start=year_start,
            year_end=end_year,
            user_id=user_id
        )
    
        related_df = pd.DataFrame(related_data)
        filtered_df = related_df[
            (related_df['parent'] == st.session_state.selected_tag) |
            (related_df['id'].str.startswith(f"{st.session_state.selected_tag}_")) 
        ].sort_values('count', ascending=False)

        with stylable_container(
            key="related_tags",
            css_styles="""
                [data-testid="stVerticalBlock"] > div {
                    position: relative;
                    margin-bottom: 5px;
                    height: 40px !important;
                    height: 10px;
                }
                .tag-item {
                    position: absolute !important;
                    top: 0 !important;
                    left: 0 !important;
                    width: 100% !important;
                    height: 100% !important; 
                    margin: 0 !important;
                    padding: 8px !important;
                    pointer-events: none !important;
                    z-index: 1 !important;
                    display: flex !important;
                    align-items: center !important;
                }
            """
        ):
        
            if not filtered_df.empty:
                max_related = filtered_df['count'].max()
                for i, (_, row) in enumerate(filtered_df.iterrows(), 1):
                    container = st.container() 
                    with container:
                        percentage = (row['count'] / max_related) * 100
                        st.markdown(f"""
                            <div class="tag-item">
                                <div class="tag-name">{i}. {row['label'].split('<br>')[0]}</div>
                                <div class="bar-container">
                                    <div class="frequency-bar" style="width: {percentage}%;"></div>
                                </div>
                                <div class="count">{int(row['count'])} routes</div>
                            </div>
                        """, unsafe_allow_html=True)
            if st.button("← Back to All Tags"):
                st.session_state.selected_tag = None
                st.rerun()

col1, col2 = st.columns(2)

with col1:
    previous_primary = st.session_state.get('primary_tag', None)
    primary_tag = st.selectbox(
        "Primary Tag",
        options=['style', 'feature', 'descriptor', 'rock_type'],
        format_func=lambda x: {
            'style': 'Climbing Style',
            'feature': 'Route Feature',
            'descriptor': 'Route Characteristic',
            'rock_type': 'Rock Type'
        }[x],
        key="primary_tag"
    )
    if previous_primary != primary_tag:
        st.session_state.selected_tag = None

with col2:
    previous_related = st.session_state.get('related_tag', None)
    related_tag = st.selectbox(
        "Related Tag",
        options=[opt for opt in ['style', 'feature', 'descriptor', 'rock_type'] if opt != st.session_state.primary_tag],
        format_func=lambda x: {
            'style': 'Climbing Style',
            'feature': 'Route Feature',
            'descriptor': 'Route Characteristic',
            'rock_type': 'Rock Type'
        }[x],
        key="related_tag"
    )
    if previous_related != related_tag:
        st.session_state.selected_tag = None

create_drill_down_bars(
    conn=conn,
    tag_type=primary_tag,
    related_data=related_tag,
    user_id=user_id,
    year_start=start_year,
    year_end=end_year,
    route_types=route_types
)