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


st.markdown("""   
     <style>
        /* Filter spacing from top of page */
        div[data-testid="stExpander"] {
            margin-top: 0rem;
        }

        /* Card spacing from filter */
        div:has(> .style-card) {
            margin-top: 0rem !important;  /* Adjust this value as needed */
        }

        /* Tab spacing from card */
        [data-testid="stTabs"] {
            margin-top: -1rem !important;
        }

        /* Center tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 90px;
            justify-content: center !important;
        }
        
    .stExpander {
        border: none !important;
        padding: 0 !important;
        
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

top_rated_routes = metrics.get_highest_rated_climbs(
    conn,
    selected_styles=selected_styles,
    route_types=None,
    year_start=start_year,
    year_end=end_year,
    tag_type=tag_type,
    user_id=user_id
).values.tolist()

st.markdown("""
    <style>
        /* Remove default Streamlit expander styling */
        .stExpander {
            border: none !important;
            background-color: rgba(255, 255, 255, 0.05) !important;
            border-radius: 8px !important;
            margin-bottom: 8px !important;
        }
        
        /* Remove the default border and background */
        .streamlit-expanderHeader {
            background-color: transparent !important;
            border: none !important;
            color: white !important;
        }
        
        /* Style the expander content container */
        .streamlit-expanderContent {
            border: none !important;
            background-color: transparent !important;
        }
        
        /* Dark background for each expander */
        div[data-testid="stExpander"] {
            background: rgba(0, 0, 0, 0.2) !important;å
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
        }

        /* Hover effect */
        div[data-testid="stExpander"]:hover {
            background: rgba(255, 255, 255, 0.05) !important;
        }

        /* Move filters up */
        section[data-testid="stSidebar"] > div {
            padding-top: 1rem !important;
        }
        
        /* Adjust main container padding */
        .block-container {
            padding-top: 1rem !important;
        }
        /* Adjust main container padding */
        .block-container {
            padding-top: 2rem !important;
        }
        
        /* Style card positioning */
        .style-card {
            background: transparent;
            border: 1px solid #1ed760;
            border-radius: 10px;
            padding: 1.5rem;
            margin: -4rem 0 2rem 0;  /* Increased negative top margin */
            text-align: center;
            position: relative;  /* Add position relative */
            z-index: 1;  /* Ensure card stays above other elements
        }
                    /* Tab content spacing */
        .stTabs [data-baseweb="tab-list"] {
            margin-bottom: 1rem !important;  /* Uniform spacing after tab list */
        }
        
        /* Tabs positioning */
        [data-testid="stTabs"] {
            margin-top: 0 !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Remove default margins from expanders */
        [data-testid="stExpander"] {
            margin-top: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)

tag_data = metrics.top_tags(
    conn, 
    tag_type, 
    user_id=user_id,
    year_start=start_year,
    year_end=end_year
)
tag_df = pd.DataFrame(tag_data, columns=['Type', 'Tag', 'Count'])

tab1, tab2 = st.tabs(["🏔️ Top Routes", "🏷️ Style Analysis"])

with tab1:
    st.markdown("""
        <style>
            .stExpander {
                border: none !important;
                background-color: rgba(255, 255, 255, 0.05) !important;
                border-radius: 8px !important;
                margin-bottom: 8px !important;
                padding: 16px;
            }
            
            .stExpander:hover {
                background-color: rgba(255, 255, 255, 0.08) !important;
            }
        </style>
    """, unsafe_allow_html=True)

    for route_name, main_area, route, grade, stars, route_id, tags, photo_url, route_url in top_rated_routes:
        if photo_url:
            img = get_squared_image(photo_url)
            
        # Create the expander title using pure markdown
        expander_title = rf"""
    **{route_name}** :green[{grade}] {"⭐" * int(stars)}
        """.strip()
        
        with st.expander(expander_title, expanded=False):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.image(img)
            
            with col2:
                st.markdown("### Route Details")
                st.markdown(f"""
                    - **Location:** {main_area}
                    - **Type:** {tags}
                    - **Length:** 60 ft
                    - **Season:** Spring, Fall
                    - **Protection:** Bolts
                    
                    [:green[View on Mountain Project ↗]]({route_url})
                """)



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
