import streamlit as st

st.set_page_config(
    page_title="Stats Overview - Mountain Project Racked",
    page_icon="📊",
    layout="wide"
)

import os
import sys
import pandas as pd
import plotly.graph_objects as go

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import src.analysis.mp_racked_metrics as metrics
from src.streamlit.streamlit_helper_functions import image_to_base64, get_squared_image
from src.streamlit.styles import get_spotify_style
from src.streamlit.filters import render_filters

def get_day_type(length):
    # Sort achievements by length requirement
    sorted_achievements = sorted(day_types.items(), key=lambda x: x[1][0], reverse=True)
    
    # Find the highest achievement that's not exceeding the length
    for name, (threshold, emoji) in sorted_achievements:
        if length >= threshold:
            return f"{name} {emoji}"
    
    return "Cragging Day 🧗‍♂️"  # Fallback

st.markdown(get_spotify_style(), unsafe_allow_html=True)

# Then add page-specific styles
st.markdown("""
    <style>
        /* Stats Overview page specific styles */
        .stat-card {
            background: rgba(30, 215, 96, 0.1);
            border: 1px solid rgba(30, 215, 96, 0.2);
            border-radius: 10px;
            padding: 1.5rem;
            text-align: center;
            height: 100%;
        }
        
        .stat-card h3 {
            color: #888;
            font-size: 1rem;
            margin-bottom: 1rem;
        }
        
        .big-number {
            color: #1ed760;
            font-size: 2.5rem;
            font-weight: bold;
            margin: 0.5rem 0;
        }
        
        .subtitle {
            color: #888;
            font-size: 0.9rem;
        }
        /* Biggest Day specific styles */
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
        
        /* Mobile responsiveness */
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

# Check authentication
if 'authenticated' not in st.session_state or not st.session_state['authenticated']:
    st.warning('⚠️ Please enter your Mountain Project URL or User ID on the home page first.')
    st.stop()

user_id = st.session_state.user_id
conn = st.session_state.conn

try:
    years_query = f"""
    SELECT DISTINCT EXTRACT(YEAR FROM date)::int as year
    FROM routes.Ticks
    WHERE user_id = '{user_id}'
    and length(EXTRACT(YEAR FROM date)::text) = 4
    ORDER BY year
    """
    available_years_df = conn.query(years_query)
    years_df = pd.DataFrame({'date': pd.to_datetime(available_years_df['year'], format='%Y')})

    filters = render_filters(
    df=years_df,
    filters_to_include=['date'],
    filter_title="Filter your data") 

    start_year = filters.get('year_start')
    end_year = filters.get('year_end')
    
    # Create three columns for the top stats
    col1, col2, col3 = st.columns(3)
    
    # Column 1: Total Length
    with col1:
        length_data = metrics.get_length_climbed(conn, user_id=user_id, year_start=start_year, year_end=end_year)
        length_df = pd.DataFrame(length_data, columns=['Year', 'Location', 'Length'])
        total_length = length_df['Length'].sum()
        el_caps = total_length / 3000
        el_caps_str = f"{el_caps:.1f}" if el_caps % 1 != 0 else f"{int(el_caps)}"
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
    
    # Add spacing
    st.markdown("<br>", unsafe_allow_html=True)
    

    tab1, tab2, tab3 = st.tabs(
        ["📍 Areas", "📅 Biggest Day", "📊 Length Analysis"])
    
    with tab1:
        # Your areas breakdown code here
        states = metrics.states_climbed(conn, user_id=user_id)
        sub_areas = metrics.sub_areas_climbed(conn, user_id=user_id)
        # ... rest of your areas code ...
    
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
                # Regular achievements
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
                "Emperor Face Day": (4900, "👑"),   #
                # Special combinations
                "Yosemite Double Day": (5000, "⚡🌓"),     # El Cap + Half Dome
                "El Cap Double Day": (6000, "⚡⚡"),        # Two El Cap routes
                "Yosemite Triple Day": (7200, "👑⚡🌓"),    # El Cap + Half Dome + Mt Watkins
            }
       
            if 'current_day_index' not in st.session_state:
                st.session_state.current_day_index = 0
            if 'needs_verification' not in st.session_state:
                st.session_state.needs_verification = True

            biggest_days = metrics.biggest_climbing_day(
                conn, 
                user_id=user_id,
                year_start=start_year,
                year_end=end_year    
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
                for route, url, photo in zip(route_list, route_urls, photo_urls):
                    route_parts = route.split(" ~ ")
                    route_name = route_parts[0]
                    route_details = route_parts[1] if len(route_parts) > 1 else ""
                    route_details_list.append((route_name, route_details, url, photo))

                major_routes_exist = any(grade.strip() in ["V", "VI", "VII"] for grade in commitment_grades)
          
                if st.session_state.needs_verification and major_routes_exist:
                    major_route = next((route for route, grade in zip(route_list, commitment_grades) 
                                        if grade.strip() in ["V", "VI", "VII"]), None)
                    
                    if major_route:
                        route_name = major_route.split(" ~ ")[0]
                    
                        col1, col2 = st.columns([2,1])
                        with col1:
                            st.markdown("### Verify Single-Day Ascent")
                            st.markdown("""
                                The biggest day found includes a BIGWALL.
                                
                                Please confirm if it was completed in a single day.
                                
                                If yes, BEASTMODE and carry on.
                                
                                If not, we'll check your next biggest day.
                            """)

                            response = st.radio(
                                f"Was {route_name} completed in a single day?",
                                options=["Select an option", "Yes", "No"],
                                key=f"verify_{date.strftime('%Y%m%d')}"
                            )

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

                    else: # response == "Yes"
                        st.session_state.shown_big_day_prompts = True   

                if st.session_state.get('shown_big_day_prompts', False) or not major_routes_exist:
                    if start_year == end_year:
                        day = date.day
                        suffix = 'th' if 11 <= day <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                        formatted_date = date.strftime(f'%B %d{suffix}')
                    else:
                        formatted_date = date.strftime('%B %d, %Y')
                        
                    st.markdown(
                        f"""
                        <div style="display: flex; justify-content: center; gap: 0.5rem; margin: 0.5rem;">
                            <div class='total-section'>
                                <div class='stat-group'>
                                    <div class='stat-item'>
                                        <div class='total-label'>Total Length</div>
                                        <div class='total-value'>{total_length:,} ft</div>
                                    </div>
                                    <div class='stat-item'>
                                        <div class='total-label'>Routes</div>
                                        <div class='total-value'>{num_routes}</div>
                                    </div>
                                    <div class='stat-item'>
                                        <div class='achievement-text'>{get_day_type(total_length)}</div>
                                    </div>
                                </div>
                            </div>
                            <div class='total-section'>
                                <div class='stat-group'>
                                    <div class='stat-item'>
                                        <div class='total-label'>Date</div>
                                        <div class='total-value'>{formatted_date}</div>
                                    </div>
                                    <div class='stat-item'>
                                        <div class='total-label'>Area</div>
                                        <div class='total-value area-value' style="font-size: 1rem;">{areas}</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    # Add spacing
                    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
                    
                    for i, (route_name, route_details, url, photo) in enumerate(route_details_list, 1):    
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
                
        
    with tab3:
        # Your length analysis code here
        # ... your existing length analysis and chart ...
        pass

except Exception as e:
    st.error(f"Error: {str(e)}")