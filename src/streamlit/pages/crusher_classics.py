import os
import sys
import streamlit as st
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.streamlit.streamlit_helper_functions import get_squared_image, image_to_base64
from src.streamlit.styles import get_spotify_style
import src.analysis.mp_racked_metrics as metrics
from src.streamlit.filters import render_filters
from src.analysis.filters_ctes import available_years

user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')

st.markdown(get_spotify_style(), unsafe_allow_html=True)

st.markdown("""
    <style>
        /* Move filters up */
        [data-testid="stExpander"] {
            margin-top: -3rem !important;
            margin-bottom: 1rem !important;
        }
        
        /* Adjust tab position */
        [data-testid="stTabs"] {
            margin-top: 0 !important;
        }
        
        /* Remove default margins */
        .block-container {
            padding-top: 1rem !important;
        }
        
        /* Tab styling - clean and minimal */
        button[data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent !important;
            border-radius: 8px;
            color: #888888;
            font-weight: 500;
        }
        
        /* Selected tab styling - just color change */
        button[data-baseweb="tab"][aria-selected="true"] {
            background-color: transparent !important;
            color: #1ed760 !important;
            border: none !important;
        }
        
        /* Hover state - subtle */
        button[data-baseweb="tab"]:hover {
            background-color: transparent !important;
            color: #1ed760;
        }
        
        /* Add space between tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 100px;
            justify-content: center !important;
        }
    </style>
""", unsafe_allow_html=True)

years_df = available_years(conn, user_id)
filters = render_filters(
    df=years_df,
    filters_to_include=['date', 'route_tag'],
    filter_title="Choose your filters",
    conn=conn,
    user_id=user_id
)

start_year = filters.get('year_start')
end_year = filters.get('year_end')
tag_type = filters.get('tag_type')
selected_styles = filters.get('selected_tags')

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
filter_col1, filter_col2, _ = st.columns([1, 1, 2])

top_rated_routes = metrics.get_highest_rated_climbs(
    conn,
    selected_styles=selected_styles,
    route_types=None,
    year_start=start_year,
    year_end=end_year,
    tag_type=tag_type,
    user_id=user_id
).values.tolist()

st.markdown(f"""
    <div class="style-card">
        <div style="display: flex; justify-content: center; gap: 2rem;">
            <div style="text-align: center;">
                <div class="style-title">Your Climbing Style Is...</div>
                <div class="style-description">Trad Dad Core</div>
                <div class="style-subtitle">Based on your {start_year} climbing data</div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
            
        [data-testid="stExpander"] {
            margin-top: -3rem !important;
            margin-bottom: 0 !important;  /* Reduced from 1rem */
        }          


        .style-card {
            background: rgba(30, 215, 96, 0.1);
            border: 1px solid rgba(30, 215, 96, 0.2);
            border-radius: 10px;
            padding: 1.5rem;
            margin-top: -5rem !important;  /* Reduced from 1rem */
            margin-bottom: 1rem;
            text-align: center;
        }
        
        .style-title {
            color: #888;
            font-size: 1rem;
            margin-bottom: 0.5rem;
        }
        
        .style-description {
            color: #1ed760;
            font-size: 2rem;
            font-weight: bold;
            margin: 0.5rem 0;
        }
        
        .style-subtitle {
            color: #888;
            font-size: 0.9rem;
        }
    </style>
""", unsafe_allow_html=True)


tab1, tab2 = st.tabs(["🏔️ Top Routes", "🏷️ Style Analysis"])

with tab1:

    tag_data = metrics.top_tags(
        conn, 
        tag_type, 
        user_id=user_id,
        year_start=start_year,
        year_end=end_year
    )
    tag_df = pd.DataFrame(tag_data, columns=['Type', 'Tag', 'Count'])

# Display routes in the grid
    for route_name, main_area, route, grade, stars, route_id, tags, photo_url, route_url in top_rated_routes:
        with st.expander(f"{route_name} • {main_area} • ⭐ {stars:.1f}"):
            if photo_url:
                img = image_to_base64(get_squared_image(photo_url))
                
            st.markdown(f"""
                <div class="route-card">
                    <div class="route-image-container">
                        <img src="{img}" 
                                class="route-image" 
                                onerror="this.src='https://cdn.shopify.com/s/files/1/0049/9271/1909/products/Mountain-Climbing_1024x1024.jpg'">
                    </div>
                    <div class="route-info">
                        <div class="route-stats">
                            <span style="color: #b3b3b3;">{tags}</span>
                        </div>
                        <div class="route-link">
                            <a href="{route_url}" target="_blank" style="color: #1ed760; text-decoration: none;">
                                View on Mountain Project →
                            </a>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <style>
            /* Expander styling */
            .streamlit-expanderHeader {
                background-color: rgba(255, 255, 255, 0.05) !important;
                border-radius: 8px !important;
                margin-bottom: 0.5rem !important;
                border: none !important;
            }
            
            .streamlit-expanderHeader:hover {
                background-color: rgba(255, 255, 255, 0.1) !important;
            }
            
            /* Remove default expander styling */
            .streamlit-expanderContent {
                border: none !important;
                background-color: transparent !important;
            }
            
            .route-link {
                margin-top: 1rem;
                text-align: center;
            }
        </style>
    """, unsafe_allow_html=True)

with tab2:
    st.markdown(f"<h2 class='spotify-header'>Top {tag_type.replace('_', ' ').title()}s</h2>", unsafe_allow_html=True)
    
    counts = tag_df['Count'].fillna(0)
    max_count = counts.max() if len(counts) > 0 else 1

    for i, (_, tag, count) in enumerate(zip(tag_df['Type'], tag_df['Tag'], counts), 1):
        num_bars = min(10, round((count / max_count) * 10)) if max_count > 0 else 0
        frequency_bars = '|' * num_bars
        
        st.markdown(f"""
            <div class="tag-item">
                <div>
                    <span class="item-number">{i}. </span>
                    <span class="item-name">{tag}</span>
                </div>
                <div class="item-details">
                    <span style="color: #1ed760;">{frequency_bars}</span> {int(count)} routes
                </div>
            </div>
        """, unsafe_allow_html=True)
