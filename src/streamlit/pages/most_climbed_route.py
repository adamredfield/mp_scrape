import streamlit as st


if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
    st.warning('⚠️ Please enter your Mountain Project URL or User ID on the home page first.')
    st.stop()

st.set_page_config(
    page_title="Your 2024 Climbing Racked",
    page_icon="🧗‍♂️"
)

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.streamlit.streamlit_helper_functions import image_to_base64, get_squared_image
from src.streamlit.filters import render_filters
from src.streamlit.styles import get_spotify_style
import src.analysis.mp_racked_metrics as metrics
import pandas as pd

user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')

years_query = f"""
    SELECT DISTINCT EXTRACT(YEAR FROM date)::int as year
    FROM routes.Ticks
    WHERE user_id = '{user_id}'
    and length(EXTRACT(YEAR FROM date)::text) = 4
    ORDER BY year
"""

available_years_df = conn.query(years_query)
years_df = pd.DataFrame({'date': pd.to_datetime(available_years_df['year'], format='%Y')})

filters = render_filters(years_df, filters_to_include=['date'], filter_title="Choose your filters")
if filters['year_start'] is not None and filters['year_end'] is not None:
    total_routes_df = metrics.total_routes(conn, user_id=user_id, year_start=filters['year_start'], year_end=filters['year_end'])
    route_data = metrics.most_climbed_route(conn, user_id=user_id, year_start=filters['year_start'], year_end=filters['year_end'])


st.markdown(get_spotify_style(), unsafe_allow_html=True)

st.markdown("""
        <style>
        
        .block-container {
            padding-top: 3rem !important; 
        }

        .intro-text {
            color: white;
            font-size: 1.75rem;
            text-align: center;
            line-height: 1.4;
            margin-top: -5.5rem;
            margin-bottom: .5rem;
        }

        .route-card {
            background: #282828;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2.5rem;
            margin-top: 1rem;
        }
        
        .route-title {
            color: white;
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }
            
        .location-text {
            color: #b3b3b3;
            font-size: 1.1rem;
            margin-top: -1rem;
            margin-bottom: .5rem;
        }
            
        .route-link,
        .route-link:link,
        .route-link:visited,
        .route-link:active {
            color: white !important;
            text-decoration: underline !important;
        }
        
        .route-link:hover {
            color: white !important;
            text-decoration: underline !important;
        }
        
        .grade-text {
            color: white;
        }
            
        .stat-container {
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
            margin-bottom: -1rem;
        }
        
        .stat-number {
            color: #1ed760;
            font-size: 1.5rem; 
            margin-bottom: 1rem;
        }
        
        .stat-label {
            color: #b3b3b3;
            font-size: 1.3rem;
        }

        .streamlit-expanderHeader {
            font-size: 1.3rem !important;
            padding: 1rem !important;
            margin-top: 2rem !important; 
        }
        
        .journey-title {
            color: white;
            font-size: 1.5rem;
            margin: 0rem 1rem 1rem;
            text-align: center;
        }
        
        .ascent-container {
            background: #181818;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }        
        .ascent-number {
            color: #1ed760;
            font-weight: 500;
            margin-bottom: 0.3rem;
        }
        .ascent-header {
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
            margin-bottom: 0.3rem;
        }
        
        .ascent-date {
            color: #b3b3b3;
            font-size: 1rem;
        }
        
        .ascent-note {
            color: #b3b3b3;
            font-size: 1rem;
            margin-left: 0rem;
        }
        </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="content-container">', unsafe_allow_html=True)

date_text = (f"in {filters['year_start']}" 
            if filters['year_start'] == filters['year_end']
            else f"between {filters['year_start']} and {filters['year_end']}")

total_routes_count = total_routes_df['count'].sum() if not total_routes_df.empty else 0

if not route_data.empty:

    times_climbed = route_data['times_climbed']
    formatted_date = route_data['first_climbed'].strftime('%b %d')
    day = route_data['first_climbed'].day
    suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    length = route_data['length']
    total_length = length * times_climbed
    formatted_total_length = "{:,}".format(total_length)
    squared_image = get_squared_image(route_data['primary_photo_url'])
    route_url = route_data['route_url']

    needs_break = "between" in date_text.lower()

    # Intro text
    st.markdown(f"""
        <div class="intro-text">
            Out of {total_routes_count} routes{' <br>' if needs_break else ' '}{date_text}<br>
            You couldn't get enough of """, unsafe_allow_html=True)
    
    # Route card
    st.markdown(f"""
        <div class="route-card">
            <div class="route-title">
                <a href="{route_data['route_url']}" target="_blank" class="route-link">{route_data['route_name']}</a> 
                ~ {route_data['grade']}
            </div>
            <div class="location-text">{route_data['specific_location']}</div>
            <div class="stat-container">
                <span class="stat-number">{times_climbed}</span>
                <span class="stat-label">Laps Starting on {formatted_date}{suffix}</span>
            </div>
            <div class="stat-container">
                <span class="stat-number">{formatted_total_length}</span>
                <span class="stat-label">Total Feet Climbed!</span>
    """, unsafe_allow_html=True)

    with st.expander("🏷️ Route Tags"):
        # Check if any tags exist
        has_tags = any(route_data.get(tag_type) for tag_type in ['styles', 'features', 'descriptors', 'rock_type'])
        
        if not has_tags:
            st.markdown("<div class='no-tags'>No tags available for this route</div>", unsafe_allow_html=True)
        else:
            # Only show categories that exist and have tags
            if route_data.get('styles'):
                st.markdown(f"""
                    <div class="tag-category">
                        <div class="tag-header">
                            <span class="tag-icon">⚡</span>
                            <span class="tag-title">Style</span>
                        </div>
                        <div class="tag-list">{route_data['styles']}</div>
                    </div>
                """, unsafe_allow_html=True)
                
            if route_data.get('features'):
                st.markdown(f"""
                    <div class="tag-category">
                        <div class="tag-header">
                            <span class="tag-icon">🏔️</span>
                            <span class="tag-title">Features</span>
                        </div>
                        <div class="tag-list">{route_data['features']}</div>
                    </div>
                """, unsafe_allow_html=True)
                
            if route_data.get('descriptors'):
                st.markdown(f"""
                    <div class="tag-category">
                        <div class="tag-header">
                            <span class="tag-icon">📝</span>
                            <span class="tag-title">Descriptors</span>
                        </div>
                        <div class="tag-list">{route_data['descriptors']}</div>
                    </div>
                """, unsafe_allow_html=True)
                
            if route_data.get('rock_type'):
                st.markdown(f"""
                    <div class="tag-category">
                        <div class="tag-header">
                            <span class="tag-icon">🪨</span>
                            <span class="tag-title">Rock Type</span>
                        </div>
                        <div class="tag-list">{route_data['rock_type']}</div>
                    </div>
                """, unsafe_allow_html=True)

    with st.expander("Click to initiate nostalgia sequence &nbsp;&nbsp;&nbsp;&nbsp;🕹️ &nbsp;&nbsp; 🎮 "):
        if route_data['primary_photo_url']:
            col1, col2, col3 = st.columns([1,2,1])
            with col2:
                st.markdown(f"""
                    <div class="photo-container">
                        <img src="{image_to_base64(squared_image)}" class="route-photo" />
                    </div>
                """, unsafe_allow_html=True)
    
    
    # Process notes
    if route_data is not None:
        ascents = list(zip(route_data['dates'], 
                route_data['types'], 
                route_data['notes']))
        st.markdown('<div class="journey-title">Your Journey Dialing it in</div>', unsafe_allow_html=True)

        for i, (date, tick_type, note) in enumerate(ascents, 1):

            date_type_text = f"{date.strftime('%B %d, %Y')}{f' ({tick_type})' if tick_type else ''}"
            st.markdown(f"""
                <div class="ascent-container">
                    <div class="ascent-header">
                        <span class="ascent-number">Ascent #{i}</span>
                        <span class="ascent-date">{date_type_text}</span>
                    </div>
                    <div class="ascent-note">{note if note else ''}</div>
                </div>
            """, unsafe_allow_html=True)