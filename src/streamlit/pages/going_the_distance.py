import plotly.graph_objects as go
import streamlit as st
import pandas as pd
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.streamlit.filters import render_filters
from src.streamlit.styles import get_spotify_style
from src.streamlit.streamlit_helper_functions import image_to_base64, get_squared_image
import src.analysis.mp_racked_metrics as metrics
from src.analysis.filters_ctes import available_years
from streamlit_cookies_controller import CookieController

cookie_controller = CookieController()

current_page = st.query_params.get("page", "Going the Distance")
cookie_controller.set('current_page', current_page)

if not st.session_state.get('authenticated'):
    st.switch_page("mp_racked.py")
def get_day_type(length):
    sorted_achievements = sorted(
        day_types.items(),
        key=lambda x: x[1][0],
        reverse=True)

    # Find the highest achievement that's not exceeding the length
    for name, (threshold, emoji) in sorted_achievements:
        if length >= threshold:
            return f"{name} {emoji}"


st.markdown(get_spotify_style(), unsafe_allow_html=True)

st.markdown("""
    <style>
        .block-container {
            margin-top: -3rem !important;
            padding-bottom: 10rem !important;
            max-width: 100%;
        }
        div[data-testid="stExpander"] {
            margin-top: -30px !important;
        }

        div[role="tabpanel"] div[data-testid="stExpander"] {
            margin-top: 0 !important;
            margin-bottom: 10px !important;
        }

        .stat-card {
            background: black !important;
            border: 1px solid #1ed760 !important;
            border-radius: 10px !important;
            padding: 1rem 0.3rem !important;
            text-align: center !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3)
            margin-bottom: 0.5rem !important;
            color: #F5F5F5 !important;
            display: flex !important;
            flex-direction: column;
            justify-content: center !important;
            gap: 0.2rem
        }

        div:has(> .stat-card) {
            margin-top: 1rem !important;
        }

        .stat-card h3 {
            color: #F5F5F5 !important;
            font-size: 1.1rem !important;
            margin-bottom: -1rem !important;
            font-weight: normal !important;
            line-height: 1;
        }

        .big-number {
            color: #F5F5F5 !important;
            font-size: 1.5rem !important;
            font-weight: bold !important;
            margin: .3rem 0 !important;
            line-height: 1;
        }

        .subtitle {
            color: #F5F5F5 !important;
            font-size: 1rem !important;
            margin: 0.2rem !important;
            line-height: 1 !important;
        }

        .total-section {
            background: rgba(30, 215, 96, 0.1);
            border-radius: 8px;
            flex: 1;
            padding: 0.5rem;
            min-width: 200px;
        }

        .stat-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .stat-item {
            text-align: center;
            padding: 0.25rem 0;
        }

        .total-label {
            color: #888;
            font-size: 0.8rem;
            margin-bottom: 0.25rem;
            line-height: 1;
        }

        .total-value {
            color: #1ed760;
            font-size: 1.2rem;
            font-weight: bold;
            line-height: 1.2;
        }

        .achievement-text {
            color: #1ed760;
            font-size: 0.9rem;
            font-weight: 500;
            margin-top: 0.25rem;
            opacity: 0.9;
            text-align: center;
        }

        @media (max-width: 768px) {
            .achievement-text {
                font-size: 0.8rem;
            }
        }

        [data-testid="stTabs"] {
            margin-top: 2rem !important;
        }
        .total-section {
            background: rgba(30, 215, 96, 0.1);
            border-radius: 8px;
            flex: 1;
            padding: 0.5rem;
            min-width: 200px;
            margin-top: -10px;  /* Add this line to pull cards up */
        }

        [data-testid="stTabs"] {
            margin-top: -1rem !important;  /* Reduce from 2rem to 1rem */
        }

        @media (max-width: 768px) {
            .total-section {
                min-width: 150px;
            }

            .total-value {
                font-size: 1rem;
            }

            .stat-divider {
                margin: 0 0.5rem;
            }
    </style>
""", unsafe_allow_html=True)

if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
    st.warning(
        '⚠️ Please enter your Mountain Project URL or User ID on the home page first.')
    st.stop()

user_id = st.session_state.user_id
conn = st.session_state.conn

try:
    years_df = available_years(conn, user_id)

    filters = render_filters(
        df=years_df,
        filters_to_include=['date'],
        filter_title="Choose your year range")

    start_year = filters.get('year_start')
    end_year = filters.get('year_end')

    col1, col2, col3 = st.columns(3)

    with col1:
        length_data = metrics.get_length_climbed(
            conn,
            user_id=user_id,
            year_start=start_year,
            year_end=end_year,
            pitch_preference=st.session_state.pitches_preference)
        length_df = pd.DataFrame(
            length_data, columns=[
                'Year', 'Location', 'Length'])
        total_length = length_df['Length'].sum()
        el_caps = total_length / 3000
        el_caps_str = f"{
            el_caps:.1f}" if el_caps % 1 != 0 else f"{
            int(el_caps)}"
        formatted_length = f"{int(total_length):,}"

        st.markdown(
            f"""
            <div class='stat-card'>
                <h3>Total Length Climbed</h3>
                <div class='big-number'>{formatted_length} ft</div>
                <div class='subtitle'>≈ {el_caps_str} El Caps 🏔️</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("""
    <style>
        /* Add space between tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 100px;
            justify-content: center !important;
        }

        .stTabs {
            padding: 0 12px;
        }
    </style>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(
        ["📍 Areas", "📅 Biggest Day"])

    with tab1:
        st.markdown("""
            <div style='
                text-align: center;
                color: #F5F5F5;
                margin-bottom: 5px;
            '>
                Group Areas By
            </div>
        """, unsafe_allow_html=True)

        st.markdown(
            "<div style='margin-top: 5px;'></div>",
            unsafe_allow_html=True)

        container = st.container()
        with container:
            st.markdown("""
            <style>
                /* Target only this specific radio group */
                .element-container:has(#area-filter-radio-after) + div div[role="radiogroup"] {
                    display: flex;
                    justify-content: center;
                    gap: 10px;
                }
                .element-container:has(#area-filter-radio-after) + div {
                    margin-bottom: -50px;  /* Adjust this value as needed */
                    margin-top: -35px;
                }
            </style>
        """, unsafe_allow_html=True)
            st.markdown(
                '<span id="area-filter-radio-after"></span>',
                unsafe_allow_html=True)
            area_type = st.radio(
                "",
                options=[
                    ('region', 'States/Regions'),
                    ('sub_area', 'Sub Areas')
                ],
                format_func=lambda x: x[1],
                key='area_filter_type',
                horizontal=True,
                label_visibility='collapsed'
            )

        st.markdown("</div>", unsafe_allow_html=True)

        if area_type[0] == 'region':
            areas_data = metrics.states_climbed(
                conn, user_id=user_id, year_start=start_year, year_end=end_year)
            total_count = metrics.regions_climbed(
                conn, user_id=user_id, year_start=start_year, year_end=end_year)
            title = "Top States/Regions"
        else:
            areas_data = metrics.sub_areas_climbed(
                conn, user_id=user_id, year_start=start_year, year_end=end_year)
            total_count = metrics.regions_sub_areas(
                conn, user_id=user_id, year_start=start_year, year_end=end_year)
            title = "Top Areas"

        st.markdown("""
            <style>
                .area-section {
                    background: #282828;
                    border-radius: 8px;
                    padding: 1rem;
                    margin-bottom: 2rem;
                }

                .section-title {
                    color: #F5F5F5;
                    font-size: 1.3rem;
                    margin-bottom: 1rem;
                    text-align: center;
                }

                .list-item {
                    display: flex;
                    justify-content: space-between;
                    align-items: baseline;
                    margin-bottom: 0.5rem;
                    padding: 0.5rem;
                    border-radius: 4px;
                    max-width: 400px;
                    margin-left: auto;
                    margin-right: auto;
                }

                .list-item:hover {
                    background: rgba(255, 255, 255, 0.1);
                }

                .rank {
                    color: #1ed760;
                    margin-right: 0.5rem;
                }

                .name {
                    color: #F5F5F5;
                    flex-grow: 1;
                }

                .stats {
                    color: #F5F5F5;
                    font-size: 0.8rem;
                    text-align: right;
                }

                .total-count {
                    text-align: center;
                    color: #1ed760;
                    font-size: 1.2rem;
                    margin-top: 1rem;
                    padding-top: 0.5rem;
                    border-top: 1px solid rgba(255, 255, 255, 0.1);
                }
        """, unsafe_allow_html=True)

        for i, (area, days, routes) in enumerate(areas_data[:5], 1):
            st.markdown(
                f"""
                <div class='list-item'>
                    <div>
                        <span class='item-number'>{i}. </span>
                        <span class='item-name'>{area}</span>
                    </div>
                    <div class='item-details'>{days} days • {routes} routes</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown(
            f"""
            <div style='text-align: center; padding: 12px; color: #F5F5F5; font-size: 1.4rem;'>
                Total {title.split()[1]}: <span style='color: #1ed760;'>{total_count}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        length_data = metrics.get_length_climbed(
            conn,
            area_type=area_type[0],
            year_start=filters['year_start'],
            year_end=filters['year_end'],
            user_id=user_id
        )
        length_df = pd.DataFrame(
            length_data, columns=[
                'Year', 'Location', 'Length'])

        st.markdown(
            "<div style='margin-top: 40px;'></div>",
            unsafe_allow_html=True)

        fig = go.Figure(data=[
            go.Bar(
                y=length_df['Location'],
                x=length_df['Length'],
                orientation='h',
                marker_color='#1ed760',
            )
        ])

        fig.update_layout(
            paper_bgcolor='black',
            plot_bgcolor='black',
            title={
                'text': f'Length Climbed by {area_type[1]}',
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'color': '#F5F5F5', 'size': 20}
            },
            xaxis_title="Distance Climbed (Feet)",
            yaxis_title=None,
            margin=dict(l=5, r=5, t=50, b=20),
            height=400,
            xaxis=dict(
                color='#F5F5F5',
                gridcolor='#333333',
                showgrid=True,
                fixedrange=True
            ),
            yaxis=dict(
                color='#F5F5F5',
                gridcolor='#333333',
                showgrid=False,
                categoryorder='total ascending',
                fixedrange=True
            ),
            font=dict(
                color='#F5F5F5'
            )
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        try:
            if 'previous_filter_state' not in st.session_state:
                st.session_state.previous_filter_state = (None, None)

            current_filter_state = (start_year, end_year)

            if current_filter_state != st.session_state.previous_filter_state:
                st.session_state.current_day_index = 0
                st.session_state.needs_verification = True
                st.session_state.shown_big_day_prompts = False
                st.session_state.previous_filter_state = current_filter_state

            day_types = {
                "Cragging Day": (0, "🧗‍♂️"),
                "Castleton Day": (400, "🏰"),
                "Devil's Tower Day": (700, "😈"),
                "Diamond Day": (1000, "💎"),
                "Washington Column": (1200, "🏔️"),
                "Lost Arrow Day": (1400, "🎯"),
                "Sentinel Day": (1600, "⚔️"),
                "Half Dome Day": (2000, "🌓"),
                "Mt Watkins Day": (2200, "🌲"),
                "Grand Teton Day": (2500, "🗻"),
                "NIAD Day": (3000, "⚡"),
                "SIAD Day": (3500, "⭐"),
                "Cerro Torre Day": (4000, "🗡️"),
                "Great Trango Day": (4400, "🌎"),
                "Emperor Face Day": (4900, "👑"),  

                "Yosemite Double Day": (5000, "⚡🌓"), 
                "El Cap Double Day": (6000, "⚡⚡"),    
                "Yosemite Triple Day": (7200, "👑⚡🌓"),
            }

            if 'current_day_index' not in st.session_state:
                st.session_state.current_day_index = 0
            if 'needs_verification' not in st.session_state:
                st.session_state.needs_verification = True

            biggest_days = metrics.biggest_climbing_day(
                conn,
                user_id=user_id,
                year_start=start_year,
                year_end=end_year,
                pitch_preference=st.session_state.pitches_preference
            )

            if st.session_state.current_day_index < len(biggest_days):
                current_day = biggest_days[st.session_state.current_day_index]

                date = current_day[0]
                routes = current_day[1]
                commitment_grades = current_day[2].split(" | ")
                total_length = int(current_day[3])
                areas = current_day[4].rstrip(" & ")
                route_urls = current_day[5].split(" | ")
                photo_urls = current_day[6].split(" | ")
                route_list = routes.split(" | ")
                num_routes = len(route_list)

                route_details_list = []
                for route, url, photo in zip(
                        route_list, route_urls, photo_urls):
                    route_parts = route.split(" ~ ")
                    route_name = route_parts[0]
                    route_details = route_parts[1] if len(
                        route_parts) > 1 else ""
                    route_details_list.append(
                        (route_name, route_details, url, photo))

                major_routes_exist = any(
                    grade.strip() in [
                        "V", "VI", "VII"] for grade in commitment_grades)

                if st.session_state.needs_verification and major_routes_exist:
                    major_route = next((route for route, grade in zip(route_list, commitment_grades)
                                        if grade.strip() in ["V", "VI", "VII"]), None)

                    if major_route:
                        route_name = major_route.split(" ~ ")[0]

                        st.markdown("""
                            <style>
                            .element-container:has(#verify-radio-after) + div div[role="radiogroup"] {
                                display: flex;
                                flex-direction: column;
                                margin-left: 20px;
                                margin-top: -120px;
                                position: relative;
                                z-index: 9999;
                            }
                            .st-emotion-cache-1cvow4s {
                                position: relative;
                                z-index: 0;
                        }
                                    
                            /* Add z-index to individual radio options */
                            div[role="radio"] {
                                position: relative;  /* Add this */
                                z-index: 1001;      /* Add this */
                            }
                            .element-container:has(#verify-button-after) + div button {
                                display: flex;
                                justify-content: center;
                                margin-top: -115px;
                                margin-left: 80px;
                                border: 1px solid #1ed760 !important;
                                border-radius: 20px;
                                background: rgba(30, 215, 96, 0.1)
                                color: #F5F5F5 !important;
                                transition: all 0.3s ease !important;
                                z-index: 1000;
                            }
                            </style>

                        """, unsafe_allow_html=True)

                        st.markdown(f"""
                            <div style="
                                background: black;
                                border: 1px solid #1ed760;
                                border-radius: 10px;
                                padding: 1rem;
                                margin-bottom: 1rem;
                                ">
                                <div style="
                                    color: #1ed760;
                                    font-size: 1.2rem;
                                    margin-bottom: 1rem;
                                    font-weight: bold;
                                    text-align: center;
                                ">🚨 Big Fucking Wall Detected 🚨</div>
                                <div style="
                                    color: #F5F5F5;
                                    font-size: 1rem;
                                    line-height: 1.5;
                                    margin-bottom: 4rem;
                                ">
                                    Please confirm if you climbed it IAD.<br><br>
                                    If yes...Pound a piton. Drink a Cobra.<br><br>
                                    If not, who doesn't love sleeping on El Cap.<br><br>
                                    Did you climb <strong>{route_name}</strong> IAD on <strong>{date.strftime('%m-%d-%y')}</strong>?
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

                        st.markdown(
                            '<span id="verify-radio-after"></span>',
                            unsafe_allow_html=True)
                        response = st.radio(
                            "",
                            options=["Yes", "No"],
                            key=f"verify_{date.strftime('%Y%m%d')}"
                        )

                        st.markdown(
                            '<span id="verify-button-after"></span>',
                            unsafe_allow_html=True)
                        if st.button("Confirm"):
                            if response == "Select an option":
                                st.warning("Please select Yes or No.")
                            elif response == "No":
                                st.session_state.current_day_index += 1
                                st.rerun()
                            else:
                                st.session_state.needs_verification = False
                                st.session_state.shown_big_day_prompts = True
                                st.rerun()

                    else:  # response == "Yes"
                        st.session_state.shown_big_day_prompts = True

                if st.session_state.get(
                        'shown_big_day_prompts', False) or not major_routes_exist:
                    if start_year == end_year:
                        day = date.day
                        suffix = 'th' if 11 <= day <= 13 else {
                            1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                        formatted_date = date.strftime(f'%b %d{suffix}')
                    else:
                        formatted_date = date.strftime('%b %d, %Y')

                    with st.container():
                        st.markdown(f"""
                            <div style="
                                background: rgba(18, 18, 18, 0.95);
                                border: 1px solid #1ed760;
                                border-radius: 10px;
                                padding: 1.5rem;
                                margin: 1rem 0;
                                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
                            ">
                                <div style="display: flex; justify-content: space-around; align-items: flex-start; gap: 1.1rem;">
                                    <div style="flex: 1.1; text-align: center;">
                                        <div style="color: #FEFEFE;">Total Length</div>
                                        <div style="color: #FEFEFE; font-size: 1.1rem; font-weight: bold; margin: 0.5rem 0;">{total_length:,} ft</div>
                                        <div style="color: #FEFEFE;">Routes</div>
                                        <div style="color: #FEFEFE; font-size: 1.1rem; font-weight: bold;">{num_routes}</div>
                                    </div>
                                    <div style="flex: 1.1; text-align: center;">
                                        <div style="color: #FEFEFE;">Date</div>
                                        <div style="color: #FEFEFE; font-size: 1.1rem; font-weight: bold; margin: 0.5rem 0;">{formatted_date}</div>
                                        <div style="color: #FEFEFE;">Area</div>
                                        <div style="color: #FEFEFE; font-size: 1.1rem;F5F5F5-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{areas}</div>
                                    </div>
                                </div>
                            </div>
                                    <div style="
                                    text-align: center;
                                    color: #FEFEFE;
                                    font-size: 1.2rem;
                                    font-weight: 500;
                                    margin: 0.5rem 0 1.5rem 0;
                                    letter-spacing: 0.5px;
                                ">
                                    {get_day_type(total_length)}
                                </div>
                        """, unsafe_allow_html=True)

                    for i, (route_name, route_details, url,
                            photo) in enumerate(route_details_list, 1):
                        with st.expander(f"{i}. {route_name}"):
                            st.markdown(
                                f"""
                                <div class='route-details' style='margin-bottom: 1rem;'>
                                    <div style='color: #aaa;'>
                                        {route_details}<br>
                                        <a href='{url}' target='_blank' style='color: #1ed760;'>
                                            View on Mountain Project
                                        </a>
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                            if photo:
                                img = get_squared_image(photo)
                                if img:
                                    st.markdown(
                                        f"""
                                        <div style="width: 100%;">
                                            <img src="{image_to_base64(img)}"
                                                style="width: 100%;
                                                        object-fit: cover;
                                                        margin: 0;
                                                        padding: 0;
                                                        border-radius: 4px;"
                                                alt="{route_name}">
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
        except Exception as e:
            st.error(f"Error: {str(e)}")

except Exception as e:
    st.error(f"Error: {str(e)}")
