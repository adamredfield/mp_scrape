import os
import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.streamlit.streamlit_helper_functions import get_squared_image, image_to_base64
import src.analysis.mp_racked_metrics as metrics
from src.streamlit.filters import render_filters
from src.analysis.filters_ctes import available_years
from src.streamlit.styles import get_spotify_style

# Apply Spotify styling
st.markdown(get_spotify_style(), unsafe_allow_html=True)

# Initialize connection and session state
user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')

# Render filters
years_df = available_years(conn, user_id)
filters = render_filters(
    df=years_df,
    filters_to_include=['date', 'route_tag', 'route_type'],
    filter_title="Choose your filters",
    conn=conn,
    user_id=user_id 
)

# Get filter values
start_year = filters.get('year_start')
end_year = filters.get('year_end')
tag_selections = filters.get('tag_selections', {})
route_types = filters.get('route_type')

# Add spacing
st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
st.markdown("""
    <style>
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 10rem !important;  /* Add padding at bottom */
        }
                        /* Style for the analysis container */
        .analysis-container {
            margin-bottom: 3rem;  /* Add space after the analysis section */
            overflow-y: auto;     /* Enable vertical scrolling if needed */
            max-height: calc(100vh - 300px);  /* Adjust height considering headers */
        }
        .tag-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            margin-bottom: 0.3rem;
        }
        
        .tag-name {
            color: #EEEEEE;
            font-size: 1rem;
            min-width: 120px;
        }
        
        .bar-container {
                flex-grow: 1;
                margin: 0;  /* Added margin on both sides */
                padding: 0;
        }
        
        .frequency-bar {
            background: #1ed760;
            height: 4px;
            border-radius: 2px;
        }
        
        .count {
            color: #B3B3B3;
            font-size: 0.9rem;
            min-width: 80px;
            text-align: right;
        }
    </style>
""", unsafe_allow_html=True)

tag_type = st.selectbox(
    "Choose Analysis Type",
    options=['style', 'feature', 'descriptor', 'rock_type']
)

tag_data = metrics.top_tags(
    conn, 
    tag_type, 
    user_id=user_id,
    year_start=start_year,
    year_end=end_year
)

tag_df = pd.DataFrame(tag_data, columns=['Type', 'Tag', 'Count']).head(10)


counts = tag_df['Count'].fillna(0)
max_count = counts.max() if len(counts) > 0 else 1

for i, (_, tag, count) in enumerate(zip(tag_df['Type'], tag_df['Tag'], counts), 1):
    percentage = (count / max_count) * 100 if max_count > 0 else 0
    
    st.markdown(f"""
        <div class="tag-item">
            <div class="tag-name">{i}. {tag}</div>
            <div class="bar-container">
                <div class="frequency-bar" style="width: {percentage}%;"></div>
            </div>
            <div class="count">{int(count)} routes</div>
        </div>
    """, unsafe_allow_html=True)