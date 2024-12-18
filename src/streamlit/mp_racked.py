import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.streamlit.streamlit_helper_functions import check_if_user_exists, get_latest_tick, handle_queue_processing
from styles import get_all_styles, wrapped_template, diamond_template, get_wrapped_styles, get_diamond_styles, get_routes_styles
from dotenv import load_dotenv
import streamlit as st
import src.analysis.mp_racked_metrics as metrics
import pandas as pd
import plotly.graph_objects as go
import json
import boto3
from datetime import datetime

sqs = boto3.client('sqs',
        region_name=st.secrets["aws"]["region"],
        aws_access_key_id=st.secrets["aws"]["access_key_id"],
        aws_secret_access_key=st.secrets["aws"]["secret_access_key"])

# Page config
st.set_page_config(
    page_title="Your 2024 Climbing Racked",
    page_icon="🧗‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

load_dotenv()

conn = st.connection('postgresql', type='sql')

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 0



def get_user_id():
    """Handle user identification"""
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'data_status' not in st.session_state:
        st.session_state.data_status = None

    # First check if we're in an update
    if ('waiting_for_update' in st.session_state and 
        st.session_state.waiting_for_update):
        verify_user_exists(conn, st.session_state.user_id)
        return None

    if st.session_state.user_id is None:
        st.title("Mountain Project Racked")
        
        col1, col2 = st.columns([2,1])
        with col1:
            user_input = st.text_input(
                "Enter your Mountain Project URL or User ID",
                placeholder="e.g., https://www.mountainproject.com/user/200362278/doctor-choss or 200362278/doctor-choss"
            )
        
        with col2:
            if st.button("Submit"):
                if user_input:
                    # Extract user_id from URL or use direct input
                    if "mountainproject.com" in user_input:
                        try:
                            user_id = user_input.split("/user/")[1].strip("/")
                            st.write(f"Extracted from URL: {user_id}")
                        except IndexError:
                            st.error("Invalid Mountain Project URL")
                            return None
                    else:
                        user_id = user_input.strip().strip('/')
                    
                    st.session_state.user_id = user_id
                    st.session_state.data_status = None  # Reset data status
                    st.rerun()
                else:
                    st.error("Please enter a user ID")

        st.markdown("""
        ### How to find your User ID:
        1. Go to [Mountain Project](https://www.mountainproject.com)
        2. Log in and click your profile
        3. Copy your profile URL or ID from the address bar
        """)
        return None
    if st.session_state.data_status is None:     
        # Verify user exists in database
        if verify_user_exists(conn, st.session_state.user_id):
            st.session_state.data_status = 'ready'
            st.rerun()
        return None

    return st.session_state.user_id

def trigger_user_scrape(user_id):
    """Send message to SQS to trigger scrape"""

    new_scrape_queue_url = st.secrets["aws"]["new_scrape_queue_url"]

    if not new_scrape_queue_url:
        st.error("SQS Queue URL not configured")
        return False

    message = {
        'user_id': user_id,
        'source': 'streamlit_app',
        'action': 'new_user_scrape'
    }

    try:
        sqs.send_message(
            QueueUrl=new_scrape_queue_url,
            MessageBody=json.dumps(message)
        )
        st.session_state.scrape_requested = True
        st.session_state.scrape_time = datetime.now()
        st.session_state.initial_delay = True
        st.session_state.start_time = datetime.now()
        return True
    except Exception as e:
        st.error(f"Failed to trigger scrape: {str(e)}")
        return False

def verify_user_exists(conn, user_id):
    if 'waiting_for_update' in st.session_state and st.session_state.waiting_for_update:
        handle_queue_processing(conn, user_id, sqs)
        return None

    exists = check_if_user_exists(conn, user_id)

    if exists:
        latest_insert, latest_route, tick_date = get_latest_tick(conn, user_id)

        st.info(f"Your ticks up to {tick_date.strftime('%Y-%m-%d')} are already in the database.\n\n"
                f"Your data was last updated on {latest_insert.strftime('%Y-%m-%d')}")

        st.write(f"""
            Have you climbed and logged additional routes since {latest_route}?  \n    
            We want your data to be as accurate as possible.  \n
            Please only refresh if you have climbed and logged additional routes.  \n
            Data collection isn't free for the creator of this app. 🙏
        """)

        col1, col2 = st.columns([1,2])
        with col1:
            with st.empty():
                if st.button("Refresh Data"):
                    st.info("Initiating data update...")
                    if trigger_user_scrape(user_id):
                        st.session_state.waiting_for_update = True
                        st.session_state.initial_delay = True
                        st.session_state.start_time = datetime.now()
                        st.rerun()
        with col2:
            if st.button("Continue with existing data"):
                st.session_state.data_status = 'ready'
                return True
        
        if st.session_state.get('data_status') != 'ready':
            st.stop()
    else:
        with st.empty():
            st.warning("Your data has not been collected yet.")
        if trigger_user_scrape(user_id):
            st.session_state.waiting_for_update = True
            st.session_state.initial_delay = True
            st.session_state.start_time = datetime.now()
            st.rerun()
        return False

def page_total_length(user_id):
    """First page showing total length climbed"""
    length_data = metrics.get_length_climbed(conn, year='2024', user_id=user_id)
    length_df = pd.DataFrame(length_data, columns=['Year', 'Location', 'Length'])
    total_length = length_df['Length'].sum()

    el_caps = total_length / 3000  # El Cap height in feet
    # Only show decimal if not a whole number
    el_caps_str = f"{el_caps:.1f}" if el_caps % 1 != 0 else f"{int(el_caps)}"
    
    formatted_length = f"{int(total_length):,}"
    
    main_text = f"You climbed<br>{formatted_length}<br>feet this year"
    subtitle = f"That's like climbing {el_caps_str} El Caps! 🏔️"
    st.markdown(wrapped_template(main_text, subtitle), unsafe_allow_html=True)

def page_biggest_day(user_id):
    """Biggest climbing day page"""
    try:
        biggest_day = metrics.biggest_climbing_day(conn, user_id=user_id)
        
        if not biggest_day:
            st.error("No climbing data found for 2024")
            return
            
        date = biggest_day[0]
        routes = biggest_day[1]
        total_length = int(biggest_day[2])
        areas = biggest_day[3].rstrip(" & ")

        formatted_date = date.strftime('%b %d')
        day = date
        if day in [1, 21, 31]:
            suffix = 'st'
        elif day in [2, 22]:
            suffix = 'nd'
        elif day in [3, 23]:
            suffix = 'rd'
        else:
            suffix = 'th'
        
        # Format routes list
        route_list = routes.split(" | ")
        formatted_routes = "<br>".join(route_list)
        
        main_text = f"Your biggest climbing day<br>was {formatted_date}{suffix} with<br>{total_length:,d} feet of GNAR GNAR"
        st.markdown(
            wrapped_template(
                main_text=main_text,
                subtitle=f"You Climbed these rigs in {areas}",
                detail_text=formatted_routes
            ),
            unsafe_allow_html=True
        )
        
    except Exception as e:
        st.error(f"Error: {str(e)}")

def page_total_routes(user_id):
    """Second page showing total routes"""
    total_routes = metrics.total_routes(conn, user_id=user_id)
    
    main_text = f"You climbed {total_routes:,} routes<br>this year"
    subtitle = "And one route again, and again, and again..."
    st.markdown(diamond_template(main_text, subtitle), unsafe_allow_html=True)

def page_most_climbed(user_id):
    """Page showing most repeated route"""
    route_data = metrics.most_climbed_route(conn, user_id=user_id)
    
    if route_data:
        route_name = route_data[0]
        notes = route_data[1]
        first_date = route_data[2]
        times_climbed = route_data[3]

        formatted_date = first_date.strftime('%b %d')
        day = first_date.day

        if day in [1, 21, 31]:
            suffix = 'st'
        elif day in [2, 22]:
            suffix = 'nd'
        elif day in [3, 23]:
            suffix = 'rd'
        else:
            suffix = 'th'

        note_list = notes.split(" | ") if notes else []
        note_list.reverse()
        
        formatted_notes = ""
        if note_list:
            formatted_notes = "Let's relive some memories:<br><br>"
            formatted_notes += "<br>".join([
                f'<div style="max-width: 1000px;">Ascent #{i+1}: "{note.strip()}"</div>'
                for i, note in enumerate(note_list)
                if note.strip()
            ])
        
        main_text = f"Your most climbed route was<br>{route_name}"
        subtitle = f"You climbed it {times_climbed} times"
        detail_text = f"starting on {formatted_date}{suffix}<br><br>{formatted_notes}"
        
        st.markdown(diamond_template(main_text, subtitle, detail_text), unsafe_allow_html=True)

def get_spotify_style():
    return """
        <style>
        .stApp {
            background-color: black !important;
        }
        
        .content-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .spotify-header {
            color: #1ed760;
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            text-align: center;
        }
        
        .list-item {
            margin: 0.25rem 0;
            text-align: left;
            padding-left: 40%;
        }
        
        .item-number {
            color: #1ed760;
            font-size: 1.2rem;
        }
        
        .item-name {
            color: white;
            font-size: 1.2rem;
        }
        
        .item-details {
            color: #b3b3b3;
            font-size: 0.9rem;
            margin-top: -0.2rem;
        }
        
        .total-section {
            margin-top: 2rem;
            text-align: center;
        }
        
        .total-label {
            color: #1ed760;
            font-size: 1.2rem;
            margin-bottom: 0.5rem;
        }
        
        .total-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: white;
        }
        </style>
    """

def page_top_routes(user_id):
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
    tag_df = pd.DataFrame(tag_data, columns=['Type', 'Tag', 'Count']).head(5)
    
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
    
    # Top Routes Column
    with left_col:
        st.markdown("<h2 class='spotify-header'>Your Top Routes</h2>", unsafe_allow_html=True)
        for i, (route, grade, stars, votes, tags) in enumerate(top_rated_routes[:5], 1):
            st.markdown(
                f"""
                <div class='list-item'>
                    <div>
                        <span class='item-number'>{i}. </span>
                        <span class='item-name'>{route}</span>
                    </div>
                    <div class='item-details'>⭐ {stars:.1f} stars &bull; {grade}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
    # Top Tags Column
    with right_col:
        st.markdown(f"<h2 class='spotify-header'>Top {tag_type.replace('_', ' ').title()}</h2>", unsafe_allow_html=True)
        
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

def page_areas_breakdown(user_id):
    """Page showing top states and areas"""
    states = metrics.states_climbed(conn, user_id=user_id)
    sub_areas = metrics.sub_areas_climbed(conn, user_id=user_id)
    total_states = metrics.regions_climbed(conn, user_id=user_id)
    total_areas = metrics.regions_sub_areas(conn, user_id=user_id)
    
    # Apply Spotify styling
    st.markdown(get_spotify_style(), unsafe_allow_html=True)
    
    # Create a centered layout with three columns for the top sections
    left_spacer, col1, middle_spacer, col2, right_spacer = st.columns([0.5, 2, 0.5, 2, 1.5])
    
    # States column
    with col1:
        st.markdown("<h2 class='spotify-header'>Top States</h2>", unsafe_allow_html=True)
        for i, (state, days, routes) in enumerate(states[:5], 1):
            st.markdown(
                f"""
                <div class='list-item'>
                    <div>
                        <span class='item-number'>{i}. </span>
                        <span class='item-name'>{state}</span>
                    </div>
                    <div class='item-details'>{days} days • {routes} routes</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        st.markdown(
            f"""
            <div class='total-section'>
                <div class='total-label'>Total States</div>
                <div class='total-value'>{total_states}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Areas column
    with col2:
        st.markdown("<h2 class='spotify-header'>Top Areas</h2>", unsafe_allow_html=True)
        for i, (area, days, routes) in enumerate(sub_areas[:5], 1):
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
            <div class='total-section'>
                <div class='total-label'>Total Areas</div>
                <div class='total-value'>{total_areas}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Add spacing before the chart section
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    
    # Add filter for the length chart
    filter_col1, filter_col2, _ = st.columns([1, 1, 2])
    
    with filter_col1:
        area_type = st.selectbox(
            "Group Length By",
            options=['region', 'main_area'],
            format_func=lambda x: x.replace('_', ' ').title(),
            key='length_filter_type'
        )
    
    # Get length data based on selected filter
    length_data = metrics.get_length_climbed(conn, area_type=area_type, year='2024', user_id=user_id)
    length_df = pd.DataFrame(length_data, columns=['Year', 'Location', 'Length'])
    
    # Create horizontal bar chart
    fig = go.Figure(data=[
        go.Bar(
            y=length_df['Location'],
            x=length_df['Length'],
            orientation='h',
            marker_color='#1ed760',  # Spotify green
        )
    ])
    
    # Update layout with dark theme
    fig.update_layout(
        paper_bgcolor='black',
        plot_bgcolor='black',
        title={
            'text': f'Length Climbed by {area_type.replace("_", " ").title()}',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'color': 'white', 'size': 20}
        },
        xaxis_title="Distance Climbed (Feet)",
        yaxis_title=area_type.replace("_", " ").title(),
        margin=dict(l=20, r=20, t=50, b=20),
        height=400,
        xaxis=dict(
            color='white',
            gridcolor='#333333',
            showgrid=True
        ),
        yaxis=dict(
            color='white',
            gridcolor='#333333',
            showgrid=False,
            categoryorder='total ascending'  # Sort by length climbed
        ),
        font=dict(
            color='white'
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

def page_grade_distribution(user_id):
    """Page showing grade distribution and most common grade"""
    # Add filter above the chart
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])
    
    with filter_col1:
        grade_level = st.selectbox(
            "Grade Detail Level",
            options=['base', 'granular', 'original'],
            format_func=lambda x: x.title(),
            key='grade_level_filter'
        )
    
    # Get the data based on selected grade level
    grade_dist = metrics.get_grade_distribution(conn, route_types=None, level=grade_level, year='2024', user_id=user_id)
    top_grade = metrics.top_grade(conn,level=grade_level, user_id=user_id)
    
    # Apply Spotify styling
    st.markdown(get_spotify_style(), unsafe_allow_html=True)
    
    # Create a centered layout
    left_spacer, content, right_spacer = st.columns([0.5, 2, 0.5])
    
    with content:
        st.markdown("<h2 class='spotify-header'>Your Grades</h2>", unsafe_allow_html=True)
        
        # Display top grade
        st.markdown(
            f"""
            <div class='total-section'>
                <div class='total-label'>Most Common Grade</div>
                <div class='total-value'>{top_grade}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Create DataFrame for plotting
        df = pd.DataFrame(grade_dist)
        
        # Create bar chart using Graph Objects with dark theme
        fig = go.Figure(data=[
            go.Bar(
                x=df['Grade'],
                y=df['Percentage'],
                marker_color='#1ed760'  # Spotify green
            )
        ])
        
        # Update layout with dark theme
        fig.update_layout(
            paper_bgcolor='black',
            plot_bgcolor='black',
            title={
                'text': 'Grade Distribution',
                'y': 0.9,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'color': 'white', 'size': 20}
            },
            xaxis_title="Grade",
            yaxis_title="Percentage of Climbs (%)",
            bargap=0.1,
            margin=dict(t=50, l=50, r=20, b=50),
            height=400,
            xaxis=dict(
                type='category',
                categoryorder='array',
                categoryarray=df['Grade'],
                color='white',
                gridcolor='#333333'
            ),
            yaxis=dict(
                color='white',
                gridcolor='#333333'
            ),
            font=dict(
                color='white'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)

def main():
    
    user_id = get_user_id()
    if not user_id:
        return

    if 'page' not in st.session_state:
        st.session_state.page = 0

    # Page mapping
    pages = {
        0: lambda: page_total_length(user_id),
        1: lambda: page_biggest_day(user_id),
        2: lambda: page_total_routes(user_id),
        3: lambda: page_most_climbed(user_id),
        4: lambda: page_top_routes(user_id),
        5: lambda: page_areas_breakdown(user_id),
        6: lambda: page_grade_distribution(user_id)
    }

    # Apply styles based on current page
    current_page = st.session_state.page
    if current_page in [0, 1]:  # Total length and biggest day pages
        st.markdown(get_wrapped_styles(), unsafe_allow_html=True)
    elif current_page in [2, 3]:  # Total routes and most climbed pages
        st.markdown(get_diamond_styles(), unsafe_allow_html=True)
    elif current_page in [4, 5, 6]:  # Top routes, areas, and grades pages
        st.markdown(get_routes_styles(), unsafe_allow_html=True)
    else:
        st.markdown(get_all_styles(), unsafe_allow_html=True)

    # Display current page
    if current_page in pages:
        pages[current_page]()
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 18, 1])
    
    with col1:
        if st.session_state.page > 0:
            if st.button("← Prev"):
                st.session_state.page -= 1
                st.rerun()
    
    with col3:
        if st.session_state.page < len(pages) - 1:
            if st.button("Next →"):
                st.session_state.page += 1
                st.rerun()

if __name__ == "__main__":
    main() 