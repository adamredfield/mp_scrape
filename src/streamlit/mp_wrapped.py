import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.database.utils import create_connection
import src.analysis.analysis_queries as analysis_queries

# Page config
st.set_page_config(
    page_title="2024 Climbing Racked",
    page_icon="🧗‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# Main app
def main():
    # Title
    st.title("Your 2024 Mountain Project Racked 🧗‍♂️")
    
    # Let's start with one visualization
    conn = create_connection()
    cursor = conn.cursor()

    total_routes = cursor.execute("SELECT COUNT(DISTINCT route_id) FROM Ticks WHERE date LIKE '%2024%'").fetchone()[0]

    most_climbed_route = cursor.execute("SELECT r.route_name, COUNT(*) FROM Ticks t JOIN Routes r ON t.route_id = r.id WHERE t.date LIKE '%2024%' GROUP BY r.route_name ORDER BY COUNT(*) DESC LIMIT 1").fetchone()[0]

    top_rated_routes = cursor.execute("SELECT r.route_name, r.avg_stars FROM Routes r JOIN ticks t ON t.route_id = r.id WHERE t.date LIKE '%2024%' ORDER BY r.avg_stars DESC LIMIT 5").fetchall()

    days_climbed = cursor.execute("SELECT COUNT(DISTINCT date) FROM Ticks WHERE date LIKE '%2024%'").fetchone()[0]

    top_climbing_style = cursor.execute("SELECT style, COUNT(*) FROM Ticks t JOIN Routes r ON t.route_id = r.id WHERE t.date LIKE '%2024%' GROUP BY style ORDER BY COUNT(*) DESC LIMIT 1").fetchone()[0]

                # Custom CSS for Spotify-style display
    st.markdown("""
        <style>
        .spotify-container {
            background: linear-gradient(180deg, #FF0080 0%, #7928CA 100%);
            color: white;
            padding: 4rem 2rem;
            border-radius: 20px;
            text-align: center;
            margin: 2rem 0;
        }
        .big-number {
            font-size: 4rem;
            font-weight: 800;
            margin: 1rem 0;
            line-height: 1.2;
        }
        .context-text {
            font-size: 1.2rem;
            opacity: 0.9;
            margin-top: 1rem;
        }
        .fullscreen-div {
            position: relative;
            min-height: 80vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 2rem;
        }
        </style>
        """, unsafe_allow_html=True)
    
    # Display the metric
    st.markdown(f"""
        <div class="fullscreen-div">
            <div class="spotify-container">
                <div>You climbed</div>
                <div class="big-number">{total_routes:,}</div>
                <div>routes this year</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    most_climbed_results = analysis_queries.get_most_climbed_areas(cursor)
    most_climbed_areas_df = pd.DataFrame(most_climbed_results, columns=['Location', 'Visits', 'Avg_Rating'])

    st.markdown("""
        <style>
        .big-number {
            font-size: 60px;
            font-weight: bold;
            color: black;
        }
        .area-name {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 0;
        }
        .visit-count {
            font-size: 18px;
            color: #666;
        }
        .area-container {
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        </style>
    """, unsafe_allow_html=True)

    st.header("Your Top Climbing Areas")

        # Display top 5 areas
    for i, (_, row) in enumerate(most_climbed_areas_df.head().iterrows(), 1):
        with st.container():
            cols = st.columns([1, 4])
            
            # Number column
            with cols[0]:
                st.markdown(f'<div class="big-number">{i}</div>', unsafe_allow_html=True)
            
            # Area details column
            with cols[1]:
                st.markdown(
                    f'''
                    <div class="area-container">
                        <p class="area-name">{row['Location']}</p>
                        <p class="visit-count">{int(row['Visits'])} visits • {row['Avg_Rating']:.1f}⭐</p>
                    </div>
                    ''', 
                    unsafe_allow_html=True
                )

    # Get length data (your existing query)
    results = analysis_queries.get_length_climbed(cursor)
    df = pd.DataFrame(results, columns=['Year', 'Location', 'Length'])

        # Create the length climbed chart (your existing visualization)
    fig = px.bar(
        df,
        x='Length',
        y='Year',
        color='Location',
        title='Length Climbed by Year',
        barmode='stack',
        orientation='h',
        custom_data=['Location', 'Length']
    )

    fig.update_layout(
        xaxis_title="Distance Climbed (Feet)",
        yaxis_title="Year",
        margin=dict(l=20, r=200, t=40, b=20),
        yaxis={'categoryorder': 'category ascending'}
    )
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=True)
    
    
    
    
    
    

    st.header("Your Favorite Route")
    st.subheader("One route again and again and again...")
    
    # Grade Distribution
    st.header("Your Grade Journey")
    
    # Length Stats
    st.header("Distance Covered")
    
    # Evolution Section
    st.header("Your Climbing Evolution")
    
    # Big Wall Section
    st.header("The Big Stuff")
    
    # Solo Section
    st.header("Solo Adventures")


if __name__ == "__main__":
    main()