import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import streamlit as st
from src.database.utils import create_connection
import src.analysis.mp_wrapped_metrics as metrics
import src.analysis.analysis_queries as analysis_queries
import pandas as pd

# Page config
st.set_page_config(
    page_title="Your 2023 Climbing Wrapped",
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

def main():
    # Page mapping
    pages = {
        0: page_total_length,
        2: page_total_routes,
        3: page_most_climbed,
        1: page_biggest_day,
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