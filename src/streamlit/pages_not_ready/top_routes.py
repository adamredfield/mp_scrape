import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import src.analysis.mp_racked_metrics as metrics
import streamlit as st
import pandas as pd
from src.streamlit.streamlit_helper_functions import get_squared_image

def page_top_routes(user_id, conn):
    """Page showing top rated routes and tags"""
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    filter_col1, filter_col2, _ = st.columns([1, 1, 2])
    
    with filter_col1:
        tag_type = st.selectbox(
            "Route Characteristics",
            options=['style', 'feature', 'descriptor', 'rock_type'],
            format_func=lambda x: x.replace('_', ' ').title(),
            key='tag_type_filter'
        )
    
    # Get tag data for filter options
    tag_data = metrics.top_tags(conn, tag_type, user_id=user_id)
    tag_df = pd.DataFrame(tag_data, columns=['Type', 'Tag', 'Count']).head(10)
    
    # Calculate max_count from the actual Count column
    max_count = tag_df['Count'].max() if not tag_df.empty else 1
    
    with filter_col2:
        selected_styles = st.multiselect(
            f"Filter by {tag_type.replace('_', ' ').title()}",
            options=tag_df['Tag'].tolist(),
            key='style_filter'
        )
        
    # Get filtered routes based on selected styles
    top_rated_routes = metrics.get_highest_rated_climbs(
        conn,
        selected_styles=selected_styles,
        route_types=None,  # route_types
        year='2024', # year
        tag_type=tag_type,
        user_id=user_id
    ).values.tolist()

    # Create a centered layout with two columns
    left_col, right_col = st.columns(2)
    
    st.markdown("""
        <style>
        .route-container {
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Top Routes Column
    with left_col:
        st.markdown("<h2 class='spotify-header'>Your Top Routes</h2>", unsafe_allow_html=True)
        for i, (route, grade, stars, route_id, tags, photo_url, route_url) in enumerate(top_rated_routes[:10], 1):
            with st.container():
                cols = st.columns([1, 10])
                with cols[0]:
                    if photo_url:
                        img = get_squared_image(photo_url)
                        st.image(
                            img, # Fixed width for thumbnail
                            output_format="JPEG"  # Better for photos
                        )
            with cols[1]:
                st.markdown(
                    f"""
                    <div class='list-item'>
                        <div>
                            <span class='item-number'>{i}. </span>
                            <span class='item-name'>
                                <a href="{route_url}" target="_blank" style="color: inherit; text-decoration: none; border-bottom: 1px dotted #888;">
                                    {route}
                                </a>
                            </span>
                        </div>
                        <div class='item-details'>⭐ {stars:.1f} stars &bull; {grade}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    
    # Top Tags Column
    with right_col:
        st.markdown(f"<h2 class='spotify-header'>Top {tag_type.replace('_', ' ').title()}s</h2>", unsafe_allow_html=True)
        
        counts = tag_df['Count'].fillna(0)
        max_count = counts.max() if len(counts) > 0 else 1

        for i, (_, tag, count) in enumerate(zip(tag_df['Type'], tag_df['Tag'], counts), 1):
            # Calculate number of bars based on proportion of max count
            num_bars = min(10, round((count / max_count) * 10)) if max_count > 0 else 0
            frequency_bars = '|' * num_bars
            
            st.markdown(
                f"""
                <div class='list-item'>
                    <div>
                        <span class='item-number'>{i}. </span>
                        <span class='item-name'>{tag}</span>
                    </div>
                    <div class='item-details'>
                        <span style="color: #1ed760;">{frequency_bars}</span> {int(count)} routes
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )