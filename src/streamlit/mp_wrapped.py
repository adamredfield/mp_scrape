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
import src.analysis.mp_wrapped_metrics as mp_wrapped_metrics

# Page config
st.set_page_config(
    page_title="2024 Climbing Racked",
    page_icon="🧗‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

conn = create_connection()
cursor = conn.cursor()

total_routes = mp_wrapped_metrics.total_routes(cursor)

most_climbed_route = mp_wrapped_metrics.most_climbed_route(cursor)

top_rated_routes = mp_wrapped_metrics.top_rated_routes(cursor)

days_climbed = mp_wrapped_metrics.days_climbed(cursor)

top_climbing_style = mp_wrapped_metrics.top_climbing_style(cursor)

top_grade = mp_wrapped_metrics.top_grade(cursor, "granular")

length_climbed = analysis_queries.get_length_climbed(cursor, year='2024')

# Main app
def main():
    # Title
    st.title("Your 2024 Mountain Project Racked 🧗‍♂️")

    # Basic metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Routes Climbed", mp_wrapped_metrics.total_routes(cursor))
    with col2:
        st.metric("Days Climbed", mp_wrapped_metrics.days_climbed(cursor))
    with col3:
        st.metric("Most Common Style", mp_wrapped_metrics.top_climbing_style(cursor))

    # Detailed metrics
    st.subheader("Most Climbed Route")
    st.write(mp_wrapped_metrics.most_climbed_route(cursor))

    st.subheader("Top Rated Routes")
    top_rated = mp_wrapped_metrics.top_rated_routes(cursor)
    for route, stars in top_rated:
        st.write(f"{route}: {stars}⭐")

    st.subheader("Biggest Climbing Day")
    st.write(mp_wrapped_metrics.biggest_climbing_day(cursor))

    st.subheader("Length Climbed")
    col1, col2 = st.columns([1, 2])
    
    # Calculate total length climbed
    length_data = analysis_queries.get_length_climbed(cursor, year='2024')
    length_df = pd.DataFrame(length_data, columns=['Year', 'Location', 'Length'])
    total_length = length_df['Length'].sum()
    
    with col1:
        st.metric("2024 Total", f"{int(total_length):,} ft")
        el_caps = total_length / 3000  # El Cap height in feet
        # Only show decimal if not a whole number
        el_caps_str = f"{el_caps:.1f}" if el_caps % 1 != 0 else f"{int(el_caps)}"
        st.write(f"That's like climbing **{el_caps_str}** El Caps! 🏔️")
    
    with col2:
        # Add custom CSS for styling
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
        .length-count {
            font-size: 18px;
            color: #666;
        }
        .area-container {
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }
        </style>
        """, unsafe_allow_html=True)

        # Sort the dataframe by length in descending order
        length_df_sorted = length_df.sort_values('Length', ascending=False)

        # Display top areas by length
        for i, (_, row) in enumerate(length_df_sorted.head().iterrows(), 1):
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
                            <p class="length-count">{int(row['Length'])} ft • {row['Location']}</p>
                        </div>
                        ''', 
                        unsafe_allow_html=True
                    )

    st.subheader("Most Common Grade")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Top Grade", top_grade)
    with col2:
        grade_dist = analysis_queries.get_grade_distribution(cursor, route_types=None, level="base", year='2024')
        
        # Create DataFrame for plotting
        df = pd.DataFrame(grade_dist)
        
  # Create bar chart using Graph Objects
        fig = go.Figure(data=[
            go.Bar(
                x=df['Grade'],
                y=df['Percentage'],
                text=df['Count'],
                textposition='auto'
            )
        ])
        
        # Update layout
        fig.update_layout(
            title='Grade Distribution',
            xaxis_title="Grade",
            yaxis_title="Percentage of Climbs (%)",
            bargap=0.1,
            margin=dict(t=30, l=50, r=20, b=50),
            height=350,
            xaxis=dict(
                type='category',
                categoryorder='array',
                categoryarray=df['Grade']
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)


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

    # Get length data
    results = analysis_queries.get_length_climbed(cursor)
    df = pd.DataFrame(results, columns=['Year', 'Location', 'Length'])

        # Create the length climbed chart
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

    conn.close()

if __name__ == "__main__":
    main()