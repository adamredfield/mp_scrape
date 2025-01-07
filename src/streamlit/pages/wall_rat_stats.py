import streamlit as st
import pandas as pd
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.streamlit.streamlit_helper_functions import get_squared_image
from src.streamlit.styles import get_spotify_style
import src.analysis.mp_racked_metrics as metrics
from src.streamlit.chart_utils import create_gradient_bar_chart

user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')

try:
    df = metrics.get_bigwall_routes(conn,user_id=user_id, pitch_preference=st.session_state.pitches_preference)
    
    if df.empty:
        st.error("No big wall routes found for 2024")

    st.markdown(get_spotify_style(), unsafe_allow_html=True)
    st.markdown("""
        <style>
            .block-container {
                padding-bottom: 5rem;
                max-width: 100%;
            }
            
            .spotify-header {
                font-size: 1.5rem;
                text-align: center;
                margin: 0;
                padding: 0;
                line-height: 1.2;
            }
            
            .streamlit-expander {
                border: none !important;
                box-shadow: none !important;
                background-color: transparent !important;
            }
            .streamlit-expanderHeader {
                background-color: transparent !important;
                font-size: 1em !important;
                color: #F5F5F5 !important;
                padding: 0.5rem !important;
            }
            
            .streamlit-expanderContent {
                background-color: rgba(255, 255, 255, 0.05) !important;
                border: none !important;
                border-radius: 4px !important;
            }
            
            .route-details {
                padding: 0.5rem;
                font-size: 0.9em;
            }
            
            .route-image {
                margin-top: 0.5rem;
                border-radius: 4px;
                overflow: hidden;
            }
            
            .stats-container {
                display: flex;
                justify-content: center;
                gap: 2rem;
                margin: 1rem 0;
            }
            
            .stat-box {
                text-align: center;
            }
            
            .stat-label {
                font-size: 0.9rem;
                color: #888;
            }
                
            .stat-value {
                font-size: 1.2rem;
                font-weight: bold;
                color: #F5F5F5;
            }
            
            .streamlit-expanderHeader svg {
                font-size: 3em !important;
                vertical-align: middle !important;
            }
            
            .streamlit-expander {
                border: none !important;
                background-color: transparent !important;
            }
                
            /* Add space after the plotly chart */
            .js-plotly-plot {
                margin-bottom: 10rem !important;
            } 
        </style>
    """, unsafe_allow_html=True)
    
    with st.expander("Filters"):
        available_grades = sorted([g for g in df['commitment_grade'].unique() if pd.notna(g)])
        selected_grades = st.multiselect(
            'Filter by Commitment Grade:',
            options=available_grades,
            key='commitment_grade_filter'
        )

        route_types = st.multiselect(
            'Filter by Route Type:',
            options=['Trad', 'Sport', 'Aid', 'Alpine'],
            key='route_type_filter'
        )

        min_length = 500
        max_length = int(df['length'].max())
        length_filter = st.slider(
            'Minimum Route Length (ft):',
            min_value=min_length,
            max_value=max_length,
            value=min_length,
            step=100,
            key='length_filter'
        )

        available_years = sorted(df['date'].dt.year.unique())
        
        date_filter_type = st.radio(
            "Date Range",
            options=["Single Year", "Custom Range"],
            horizontal=True
        )

        if date_filter_type == "Single Year":
            year_start = year_end = st.selectbox(
                'Year',
                options=sorted(df['date'].dt.year.unique(), reverse=True),
                index=sorted(df['date'].dt.year.unique(), reverse=True).index(2024)
            )
        else:
            col1, col2 = st.columns(2)
            with col1:
                year_start = st.selectbox(
                    'From', 
                    options=available_years,
                    index=0  # Default to earliest year
                )   
            with col2:
                valid_end_years = [y for y in available_years if y >= year_start]
                year_end = st.selectbox(
                    'To', 
                    options=valid_end_years,
                    index=len(valid_end_years) - 1 
                )

    filtered_df = df
    if selected_grades:
        filtered_df = filtered_df[filtered_df['commitment_grade'].isin(selected_grades)]
    if route_types:
        route_type_mask = filtered_df['route_type'].apply(
            lambda x: any(rt.lower() in str(x).lower() for rt in route_types)
        )
        filtered_df = filtered_df[route_type_mask]
    filtered_df = filtered_df[filtered_df['length'] >= length_filter]
    filtered_df = filtered_df[
        (filtered_df['date'].dt.year >= year_start) & (filtered_df['date'].dt.year <= year_end)
    ]

    st.markdown(
        f"""
        <div style="display: flex; justify-content: flex-start; gap: 3rem; margin-top: -2rem;">
            <div class='total-section' style="margin-left: 1rem;">  
                <div class='total-label'>Total Big Walls</div>
                <div class='total-value'>{len(filtered_df)}</div>
            </div>
            <div class='total-section'>
                <div class='total-label'>Total Length</div>
                <div class='total-value'>{int(filtered_df['length'].sum()):,} ft</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    
    st.markdown("<div class='list-container'>", unsafe_allow_html=True)
    for i, (_, route) in enumerate(filtered_df.iterrows(), 1):
        expander_label = f"{i}. {route.route_name} - {route.grade} {route.commitment_grade or ''}"
        with st.expander(expander_label):
            st.markdown(
                f"""
                <div class='route-details' style='margin-bottom: 1rem;'>
                    <div style='color: #aaa;'>
                        Length: {route.length:,} ft<br>
                        Area: {route.area}<br>
                        Styles: {route.styles}<br>
                        Features: {route.features}<br>
                        Descriptors: {route.descriptors}<br>
                        Rock Type: {route.rock_type}<br>
                        <a href='{route.route_url}' target='_blank' style='color: #1ed760;'>View on Mountain Project</a>
                    </div>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
            if pd.notna(route.primary_photo_url):
                img = get_squared_image(route.primary_photo_url)
                if img:
                    st.markdown(
                        f"""
                        <div style="width: 100%;">
                            <img src="{route.primary_photo_url}" 
                                style="width: 100%; 
                                        object-fit: cover; 
                                        margin: 0; 
                                        padding: 0;"
                                alt="{route.route_name}">
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    st.markdown("</div>", unsafe_allow_html=True)

    fig = create_gradient_bar_chart(
    df=filtered_df,
    x_col='length',
    y_col='main_area',
    title='Big Wall Lengths by Area'
    )
    st.plotly_chart(fig, use_container_width=True,     config={
    'scrollZoom': False,
    'displayModeBar': False,
})
except Exception as e:
    st.error(f"Error: {str(e)}")