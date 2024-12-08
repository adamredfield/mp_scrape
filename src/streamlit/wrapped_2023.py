import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import streamlit as st
from src.database.utils import create_connection
import src.analysis.mp_wrapped_metrics as metrics
import src.analysis.analysis_queries as analysis_queries
import pandas as pd
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="Your 2024 Climbing Racked",
    page_icon="🧗‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 0

# Styling
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    .stApp {
        background: black;
    }
    
    .wrapped-container {
        position: relative;
        height: 100vh;
        width: 100vw;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: white;
        text-align: center;
        padding: 0;
        margin: 0;
        background: black;
        overflow: hidden;
    }
    
    .top-pattern {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 45vh;
        background: linear-gradient(to bottom right, #FF1CAE, #FF0080);
        clip-path: polygon(
            0 0,
            10% 0, 10% 8%,
            20% 8%, 20% 16%,
            30% 16%, 30% 24%,
            40% 24%, 40% 32%,
            50% 32%, 50% 40%,
            60% 40%, 60% 48%,
            70% 48%, 70% 56%,
            80% 56%, 80% 64%,
            90% 64%, 90% 72%,
            100% 72%, 100% 0
        );
    }
    
    .bottom-pattern {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 45vh;
        background: linear-gradient(to top left, #FF1CAE, #FF0080);
        clip-path: polygon(
            0 28%,
            10% 28%, 10% 36%,
            20% 36%, 20% 44%,
            30% 44%, 30% 52%,
            40% 52%, 40% 60%,
            50% 60%, 50% 68%,
            60% 68%, 60% 76%,
            70% 76%, 70% 84%,
            80% 84%, 80% 92%,
            90% 92%, 90% 100%,
            0 100%
        );
    }
    
    .big-text {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 4.5rem;
        font-weight: 900;
        line-height: 1.2;
        margin: 0;
        padding: 0;
        text-align: center;
        z-index: 10;
    }
    
    .subtitle-text {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 2rem;
        font-weight: 400;
        margin-top: 3rem;
        z-index: 10;
    }
    
    .route-list {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 1.5rem;
        font-weight: 400;
        margin-top: 1.5rem;
        z-index: 10;
    }
    
    .diamond-pattern {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 25vh;
        background: linear-gradient(to right, #4B0082, #00BFFF);
        clip-path: polygon(
            0 0, 100% 0,              /* Top edge */
            100% 25%, 80% 25%,        /* Right top step */
            60% 25%, 40% 25%,         /* Middle space */
            20% 25%, 0 25%            /* Left top step */
        );
    }
    
    .diamond-pattern-right {
        position: absolute;
        top: 0;
        right: 0;
        width: 20vw;
        height: 40vh;
        background: linear-gradient(to right, #4B0082, #00BFFF);
        clip-path: polygon(
            0 0,                      /* Top left */
            100% 0,                   /* Top right */
            100% 100%,                /* Bottom right */
            0 40%                     /* Bottom point */
        );
    }
    
    .diamond-pattern-left {
        position: absolute;
        top: 0;
        left: 0;
        width: 20vw;
        height: 40vh;
        background: linear-gradient(to right, #4B0082, #00BFFF);
        clip-path: polygon(
            0 0,                      /* Top left */
            100% 0,                   /* Top right */
            100% 40%,                 /* Bottom point */
            0 100%                    /* Bottom left */
        );
    }
    
    .diamond-bottom-right {
        position: absolute;
        bottom: 0;
        right: 0;
        width: 20vw;
        height: 40vh;
        background: linear-gradient(to right, #4B0082, #00BFFF);
        clip-path: polygon(
            0 60%,                    /* Top point */
            100% 0,                   /* Top right */
            100% 100%,                /* Bottom right */
            0 100%                    /* Bottom left */
        );
    }
    
    .diamond-bottom-left {
        position: absolute;
        bottom: 0;
        left: 0;
        width: 20vw;
        height: 40vh;
        background: linear-gradient(to right, #4B0082, #00BFFF);
        clip-path: polygon(
            0 0,                      /* Top left */
            100% 60%,                 /* Top point */
            100% 100%,                /* Bottom right */
            0 100%                    /* Bottom left */
        );
    }
    
    .top-routes-container {
        background: #ffff00;
        color: black;
        padding: 2rem;
        min-height: 100vh;
        width: 100vw;
    }
    
    .route-title {
        font-family: 'Helvetica Neue', sans-serif;
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 2rem;
    }
    
    .route-row {
        display: flex;
        align-items: center;
        margin-bottom: 1.5rem;
        gap: 1rem;
    }
    
    .route-number {
        font-size: 2.5rem;
        font-weight: 700;
        min-width: 3rem;
    }
    
    .route-info {
        display: flex;
        flex-direction: column;
    }
    
    .route-name {
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0;
    }
    
    .route-rating {
        font-size: 1.2rem;
        color: #333;
        margin: 0;
    }
    
    .big-number {
        font-size: 3rem;
        font-weight: 700;
        color: black;
    }
    
    .area-container {
        background: transparent;
        padding: 0.5rem;
    }
    
    .area-name {
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0;
        color: black;
    }
    
    .length-count {
        font-size: 1.2rem;
        color: #333;
        margin: 0;
    }
    </style>
""", unsafe_allow_html=True)

def wrapped_template(main_text, subtitle=None, detail_text=None):
    """Standardized template for Wrapped pages"""
    return f"""
        <div class="wrapped-container">
            <div class="top-pattern"></div>
            <div class="bottom-pattern"></div>
            <div class="big-text">
                {main_text}
            </div>
            {f'<div class="subtitle-text">{subtitle}</div>' if subtitle else ''}
            {f'<div class="route-list">{detail_text}</div>' if detail_text else ''}
        </div>
    """

def diamond_template(main_text, subtitle=None, detail_text=None):
    """Diamond pattern template for total routes page"""
    return f"""
        <div class="wrapped-container">
            <div class="diamond-pattern-left"></div>
            <div class="diamond-pattern-right"></div>
            <div class="diamond-bottom-left"></div>
            <div class="diamond-bottom-right"></div>
            <div class="big-text">
                {main_text}
            </div>
            {f'<div class="subtitle-text">{subtitle}</div>' if subtitle else ''}
            {f'<div class="route-list">{detail_text}</div>' if detail_text else ''}
        </div>
    """

def page_total_length():
    """First page showing total length climbed"""
    conn = create_connection()
    cursor = conn.cursor()
    length_data = analysis_queries.get_length_climbed(cursor, year='2024')
    length_df = pd.DataFrame(length_data, columns=['Year', 'Location', 'Length'])
    total_length = length_df['Length'].sum()
    
    formatted_length = f"{int(total_length):,}"
    
    main_text = f"You climbed<br>{formatted_length}<br>feet this year"
    st.markdown(wrapped_template(main_text), unsafe_allow_html=True)

def page_biggest_day():
    """Biggest climbing day page"""
    conn = create_connection()
    cursor = conn.cursor()
    
    try:
        biggest_day = metrics.biggest_climbing_day(cursor)
        
        if not biggest_day:
            st.error("No climbing data found for 2024")
            return
            
        date = biggest_day[0]
        routes = biggest_day[1]
        total_length = int(biggest_day[2])
        
        # Format routes list
        route_list = routes.split(" | ")
        formatted_routes = "<br>".join(route_list)
        
        main_text = f"Your biggest climbing day<br>was {date} with<br>{total_length:,d} feet"
        st.markdown(
            wrapped_template(
                main_text=main_text,
                subtitle="What did you climb?",
                detail_text=formatted_routes
            ),
            unsafe_allow_html=True
        )
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        
    finally:
        conn.close()

def page_total_routes():
    """Second page showing total routes"""
    conn = create_connection()
    cursor = conn.cursor()
    total_routes = metrics.total_routes(cursor)
    conn.close()
    
    main_text = f"You climbed {total_routes:,} routes<br>this year"
    subtitle = "And one route again, and again, and again..."
    st.markdown(diamond_template(main_text, subtitle), unsafe_allow_html=True)

def page_most_climbed():
    """Page showing most repeated route"""
    conn = create_connection()
    cursor = conn.cursor()
    route_data = metrics.most_climbed_route(cursor)
    conn.close()
    
    if route_data:
        route_name = route_data[0]
        notes = route_data[1]
        first_date = route_data[2]
        times_climbed = route_data[3]

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
        
        main_text = f"Your top route was<br>{route_name}"
        subtitle = f"You climbed it {times_climbed} times"
        detail_text = f"starting on {first_date}<br><br>{formatted_notes}"
        
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

def page_top_routes():
    """Page showing top rated routes"""
    conn = create_connection()
    cursor = conn.cursor()
    top_rated_routes = metrics.top_rated_routes(cursor)
    conn.close()
    
    # Apply Spotify styling
    st.markdown(get_spotify_style(), unsafe_allow_html=True)
    
    # Create a centered layout with three columns
    left_spacer, content, right_spacer = st.columns([0.5, 2, 0.5])
    
    with content:
        st.markdown("<h2 class='spotify-header'>Your Top Routes</h2>", unsafe_allow_html=True)
        
        for i, (route, stars) in enumerate(top_rated_routes[:5], 1):
            st.markdown(
                f"""
                <div class='list-item'>
                    <div>
                        <span class='item-number'>{i}. </span>
                        <span class='item-name'>{route}</span>
                    </div>
                    <div class='item-details'>⭐ {stars} stars</div>
                </div>
                """,
                unsafe_allow_html=True
            )

def page_areas_breakdown():
    """Page showing top states and areas"""
    conn = create_connection()
    cursor = conn.cursor()
    states = metrics.states_climbed(cursor)
    sub_areas = metrics.sub_areas_climbed(cursor)
    total_states = metrics.regions_climbed(cursor)
    total_areas = metrics.regions_sub_areas(cursor)
    conn.close()
    
    # Create a centered layout with three columns - adjusted ratios to move everything left
    left_spacer, col1, middle_spacer, col2, right_spacer = st.columns([0.5, 2, 0.5, 2, 1.5])
    
    # Common styles
    header_style = "color: #1ed760; font-size: 1.5rem; margin-bottom: 0.5rem; text-align: center;"
    list_style = "margin: 0.25rem 0; text-align: left; padding-left: 40%;"
    total_style = "margin-top: 2rem; text-align: center;"
    
    # States column
    with col1:
        st.markdown(f"<h2 style='{header_style}'>Top States</h2>", unsafe_allow_html=True)
        for i, (state, days, routes) in enumerate(states[:5], 1):
            st.markdown(
                f"""
                <div style='{list_style}'>
                    <div style='font-size: 1.2rem;'>
                        <span style='color: #1ed760;'>{i}. </span>
                        <span style='color: white;'>{state}</span>
                    </div>
                    <div style='color: #b3b3b3; font-size: 0.9rem; margin-top: -0.2rem;'>{days} days • {routes} routes</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        # Add total states at the bottom
        st.markdown(
            f"""
            <div style='{total_style}'>
                <div style='color: #1ed760; font-size: 1.2rem; margin-bottom: 0.5rem;'>Total States</div>
                <div style='font-size: 2.5rem; font-weight: bold; color: white;'>{total_states}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Areas column
    with col2:
        st.markdown(f"<h2 style='{header_style}'>Top Areas</h2>", unsafe_allow_html=True)
        for i, (area, days, routes) in enumerate(sub_areas[:5], 1):
            st.markdown(
                f"""
                <div style='{list_style}'>
                    <div style='font-size: 1.2rem;'>
                        <span style='color: #1ed760;'>{i}. </span>
                        <span style='color: white;'>{area}</span>
                    </div>
                    <div style='color: #b3b3b3; font-size: 0.9rem; margin-top: -0.2rem;'>{days} days • {routes} routes</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        # Add total areas at the bottom
        st.markdown(
            f"""
            <div style='{total_style}'>
                <div style='color: #1ed760; font-size: 1.2rem; margin-bottom: 0.5rem;'>Total Areas</div>
                <div style='font-size: 2.5rem; font-weight: bold; color: white;'>{total_areas}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

def page_grade_distribution():
    """Page showing grade distribution and most common grade"""
    conn = create_connection()
    cursor = conn.cursor()
    
    # Get the data
    grade_dist = analysis_queries.get_grade_distribution(cursor, route_types=None, level="base", year='2024')
    top_grade = metrics.top_grade(cursor, level="base")  # Assuming this function exists, create if needed
    conn.close()

    
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
                text=df['Count'],
                textposition='auto',
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
    # Page mapping
    pages = {
        0: page_total_length,
        1: page_biggest_day,
        2: page_total_routes,
        3: page_most_climbed,
        4: page_top_routes,
        5: page_areas_breakdown,
        6: page_grade_distribution
    }
    
    # Display current page
    if st.session_state.page in pages:
        pages[st.session_state.page]()
    
    # Next button
    if st.session_state.page < len(pages) - 1:
        col1, col2 = st.columns([20, 1])
        with col2:
            if st.button("Next →"):
                st.session_state.page += 1

if __name__ == "__main__":
    main() 