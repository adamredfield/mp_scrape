import streamlit as st
import os
import sys
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.analysis.filters_ctes import available_years
import src.analysis.mp_racked_metrics as metrics
from src.streamlit.styles import get_spotify_style
from src.streamlit.filters import render_filters
from src.streamlit.streamlit_helper_functions import image_to_base64, get_squared_image

user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')

years_df = available_years(conn, user_id)

filters = render_filters(
    years_df,
    filters_to_include=['date'],
    filter_title="Choose your filters")
if filters['year_start'] is not None and filters['year_end'] is not None:
    total_routes_df = metrics.total_routes(
        conn,
        user_id=user_id,
        year_start=filters['year_start'],
        year_end=filters['year_end'])
    route_data = metrics.most_climbed_route(
        conn,
        user_id=user_id,
        year_start=filters['year_start'],
        year_end=filters['year_end'],
        pitch_preference=st.session_state.pitches_preference)

st.markdown(get_spotify_style(), unsafe_allow_html=True)

st.markdown("""
        <style>
        /* Main container */
        .block-container {
            padding-bottom: 10rem !important;
            max-width: 100%;
        }
        .intro-text {
            color: #F5F5F5;
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
            color: #F5F5F5;
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }

        .location-text {
            color: #F5F5F5;
            font-size: 1.1rem;
            margin-top: -1rem;
            margin-bottom: .5rem;
        }

        .route-link,
        .route-link:link,
        .route-link:visited,
        .route-link:active {
            color: #F5F5F5 !important;
            text-decoration: underline !important;
        }

        .route-link:hover {
            color: #F5F5F5 !important;
            text-decoration: underline !important;
        }

        .grade-text {
            color: #F5F5F5;
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
            color: #F5F5F5;
            font-size: 1.3rem;
        }
        f
        .journey-title {
            color: #F5F5F5;
            font-size: 1.5rem;
            margin: 0rem 1rem 1rem;
            text-align: center;
        }

        .ascent-container {
            background: rgba(18, 18, 18, 0.95);
            border: 1px solid #282828;
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1rem;
            transition: border-color 0.3s ease;
        }

        .ascent-number {
            color: #1ed760;
            font-weight: 500;
            font-size: 1.1rem;
        }
        .ascent-header {
            display: flex;
            align-items: baseline;
            gap: 0.5rem;
            margin-bottom: 0.3rem;
        }

        .ascent-date {
            color: #F5F5F5;
            font-size: 1rem;
        }

        .ascent-note {
            color: #F5F5F5;
            font-size: 1rem;
            margin-top: 0.5rem;
            line-height: 1.4;
        }

        </style>
    """, unsafe_allow_html=True)

st.markdown('<div class="content-container">', unsafe_allow_html=True)

date_text = (f"in {filters['year_start']}"
             if filters['year_start'] == filters['year_end']
             else f"between {filters['year_start']} and {filters['year_end']}")

total_routes_count = total_routes_df['count'].sum(
) if not total_routes_df.empty else 0

if not route_data.empty and len(
        route_data) > 0 and route_data.iloc[0]['times_climbed'] > 1:
    if isinstance(route_data, pd.Series):
        route_data = pd.DataFrame([route_data])
    if len(route_data) > 1:
        route_options = [
            f"{row['route_name']} ({row['grade']})" for _, row in route_data.iterrows()]

        selected_route = st.selectbox(
            "",
            options=route_options,
            label_visibility="collapsed"
        )

        # Get index of selected route and filter routes_data
        selected_idx = route_options.index(selected_route)
        display_route_data = route_data.iloc[selected_idx]
    else:
        display_route_data = route_data.iloc[0]

    times_climbed = display_route_data['times_climbed']
    formatted_date = display_route_data['first_climbed'].strftime('%b %d')
    day = display_route_data['first_climbed'].day
    suffix = 'th' if 11 <= day <= 13 else {
        1: 'st',
        2: 'nd',
        3: 'rd'}.get(
        day %
        10,
        'th')
    length = display_route_data['length']
    total_length = length * times_climbed
    formatted_total_length = "{:,}".format(total_length)
    squared_image = get_squared_image(display_route_data['primary_photo_url'])
    route_url = display_route_data['route_url']

    needs_break = "between" in date_text.lower()

    st.markdown(f"""
        <div style="
            text-align: center;
            margin: {'-9rem' if len(route_data) > 1 else '-5rem'} 0 0.5rem;
        ">
            <div style="
                color: #F5F5F5;
                font-size: 1.3rem;
                margin-bottom: 0.3rem;
            ">
                Out of {total_routes_count} routes {date_text}
            </div>
            <div style="
                color: #F5F5F5;
                font-size: 1.4rem;
                font-weight: 500;
            ">
                {"You climbed these routes the most" if len(route_data) > 1 else "You couldn't get enough of"}
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div style="
            background: rgba(18, 18, 18, 0.95);
            border: 1px solid #1ed760;
            border-radius: 10px;
            padding: 1rem 1rem;
            text-align: center;
            margin-bottom: 1rem;
        ">
            <div style="
                color: #F5F5F5;
                font-size: 1.1rem;
                margin-bottom: 0.5rem;
            ">
                <a href="{display_route_data['route_url']}" target="_blank" style="color: #F5F5F5; text-decoration: none;">
                    {display_route_data['route_name']}
                </a>
                ~ {display_route_data['grade']}
            </div>
            <div style="
                color: #F5F5F5;
                font-size: 1.5rem;
                font-weight: bold;
                margin: 0.5rem 0;
            ">
                {formatted_total_length} ft
            </div>
            <div style="
                color: #F5F5F5;
                font-size: 1rem;
            ">
                ≈ {times_climbed} Laps starting on {formatted_date}{suffix}
            </div>
        </div>
    """, unsafe_allow_html=True)

    with st.expander("🏷️ Route Tags"):
        has_tags = any(display_route_data.get(tag_type) for tag_type in [
                       'styles', 'features', 'descriptors', 'rock_type'])

        if not has_tags:
            st.markdown(
                "<div class='no-tags'>No tags available for this route</div>",
                unsafe_allow_html=True)
        else:
            if display_route_data.get('styles'):
                st.markdown(f"""
                    <div class="tag-category">
                        <div class="tag-header">
                            <span class="tag-icon">⚡</span>
                            <span class="tag-title">Style</span>
                        </div>
                        <div class="tag-list">{display_route_data['styles']}</div>
                    </div>
                """, unsafe_allow_html=True)

            if display_route_data.get('features'):
                st.markdown(f"""
                    <div class="tag-category">
                        <div class="tag-header">
                            <span class="tag-icon">🏔️</span>
                            <span class="tag-title">Features</span>
                        </div>
                        <div class="tag-list">{display_route_data['features']}</div>
                    </div>
                """, unsafe_allow_html=True)

            if display_route_data.get('descriptors'):
                st.markdown(f"""
                    <div class="tag-category">
                        <div class="tag-header">
                            <span class="tag-icon">📝</span>
                            <span class="tag-title">Descriptors</span>
                        </div>
                        <div class="tag-list">{route_data['descriptors']}</div>
                    </div>
                """, unsafe_allow_html=True)

            if display_route_data.get('rock_type'):
                st.markdown(f"""
                    <div class="tag-category">
                        <div class="tag-header">
                            <span class="tag-icon">🪨</span>
                            <span class="tag-title">Rock Type</span>
                        </div>
                        <div class="tag-list">{display_route_data['rock_type']}</div>
                    </div>
                """, unsafe_allow_html=True)

    with st.expander("Click to initiate nostalgia sequence &nbsp;&nbsp;&nbsp;&nbsp;🕹️ &nbsp;&nbsp; 🎮 "):
        if display_route_data['primary_photo_url']:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown(f"""
                    <div class="photo-container">
                        <img src="{image_to_base64(squared_image)}" class="route-photo" />
                    </div>
                """, unsafe_allow_html=True)

    if display_route_data is not None:
        ascents = list(zip(display_route_data['dates'],
                           display_route_data['types'],
                           display_route_data['notes']))
        st.markdown(
            '<div class="journey-title">Your Journey Dialing it in</div>',
            unsafe_allow_html=True)

        for i, (date, tick_type, note) in enumerate(ascents, 1):

            date_type_text = f"{
                date.strftime('%B %d, %Y')}{
                f' ({tick_type})' if tick_type else ''}"
            st.markdown(f"""
                <div class="ascent-container">
                    <div class="ascent-header">
                        <span class="ascent-number">Ascent #{i}</span>
                        <span class="ascent-date">{date_type_text}</span>
                    </div>
                    <div class="ascent-note">{note if note else ''}</div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.info(f"You didn't climb any routes more than once {date_text}.")
