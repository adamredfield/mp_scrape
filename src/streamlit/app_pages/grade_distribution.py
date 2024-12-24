import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import src.analysis.mp_racked_metrics as metrics
import streamlit as st
import pandas as pd
from src.streamlit.styles import get_spotify_style
import plotly.graph_objects as go
from src.streamlit.filters import render_filters
from streamlit_plotly_events import plotly_events
import json

@st.cache_data
def get_chart_data(_conn, user_id, grade_grain, route_type, year_start, year_end):
    """Cache the data fetching"""
    sends = metrics.get_grade_distribution(
        _conn,
        route_types=route_type,
        level=grade_grain,
        year_start=year_start,
        year_end=year_end,
        user_id=user_id,
        tick_type='send'
    )
    
    falls = metrics.get_grade_distribution(
        _conn,
        route_types=route_type,
        level=grade_grain,
        year_start=year_start,
        year_end=year_end,
        user_id=user_id,
        tick_type='fall'
    )  
    return pd.DataFrame(sends), pd.DataFrame(falls)

@st.cache_data
def create_figure(sends_df, falls_df, ordered_grades):
    fig = go.Figure()

    sends_colors = {
        'Trad': '#34c759',     # Spotify green
        'Sport': '#1e90ff',    # Dodger blue
        'Boulder': '#9370db',   # Medium purple
        'TR': '#40e0d0',       # Turquoise
        'Aid': '#ffd700',      # Gold
        'Alpine': '#ff69b4'    # Hot pink
    }
    falls_colors = {
        'Trad': '#E57373',     # Material Design red (lighter)
        'Sport': '#F44336',    # Material Design red (medium)
        'Boulder': '#D32F2F',  # Material Design red (darker)
        'TR': '#FF8A80',       # Material Design red (accent)
        'Aid': '#C62828',      # Material Design red (deep)
        'Alpine': '#B71C1C'    # Material Design red (darkest)
    }
    
    # clean sends
    for route_type in sends_df['route_type'].unique():
        mask = sends_df['route_type'] == route_type
        fig.add_trace(go.Bar(
            name=f'Sends ({route_type})',
            y=sends_df[mask]['grade'],
            x=-sends_df[mask]['count'],
            orientation='h',
            width=0.5,
            marker_color=sends_colors.get(route_type, '#1ed760'),
            hovertemplate=f"{route_type} Sends: %{{customdata}}<br>Grade: %{{y}}<extra></extra>",
            customdata=abs(sends_df[mask]['count'])
        ))
    
    # falls/hangs
    if not falls_df.empty:
        for route_type in falls_df['route_type'].unique():
            mask = falls_df['route_type'] == route_type
            fig.add_trace(go.Bar(
                name=f'Falls ({route_type})',
                y=falls_df[mask]['grade'],
                x=falls_df[mask]['count'],
                orientation='h',
                width=0.5,
                marker_color=falls_colors.get(route_type, '#E57373'),  
                hovertemplate=f"{route_type} Falls: %{{x}}<br>Grade: %{{y}}<extra></extra>"
            ))

    # Get the maximum absolute value from the data
    max_val = max(abs(min(fig.data[0].x)), max(fig.data[0].x))
    
    # Automatically determine tick interval based on max value
    if max_val <= 10:
        tick_interval = 2
    elif max_val <= 30:
        tick_interval = 5
    else:
        tick_interval = 10
        
    # Generate evenly spaced ticks
    tick_vals = []
    tick_texts = []
    current = -max_val
    while current <= max_val:
        tick_vals.append(current)
        tick_texts.append(str(abs(int(current))))
        current += tick_interval
    
    fig.update_layout(
        barmode='relative',
        bargap=0.1,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend={
        'orientation': 'h',
        'yanchor': 'bottom',
        'y': 1.02,
        'xanchor': 'center',
        'x': 0.4,
        'font': {'color': 'white'},
        'groupclick': 'toggleitem',
        'itemsizing': 'constant'
        },
        xaxis=dict(
            title='Number of Climbs',
            color='white',
            gridcolor='rgba(255,255,255,0.1)',
            zeroline=True,
            zerolinecolor='white',
            zerolinewidth=0.5,
            tickmode='array',
            ticktext=tick_texts,
            tickvals=tick_vals
        ),
        yaxis=dict(
            title='Grade',
            color='white',
            gridcolor='rgba(255,255,255,0.1)',
            categoryorder='array',
            categoryarray=ordered_grades[::-1],
            type='category',
            tickmode='array',
            ticktext=ordered_grades[::-1],
            tickvals=ordered_grades[::-1]
        ),
        height=600
    )
    return fig

def page_grade_distribution(user_id, conn):

    st.markdown("""
        <style>
        .block-container {
            padding-top: 3rem !important; 
        }
        .spotify-header {
            font-size: 1.5rem;
            text-align: center;
            margin: 0;
            padding: 0;
            line-height: 1.2;
        }
        
        .stats-container {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin: 1rem 0;
        }
        
        .total-section {
            text-align: center;
            padding: 1rem;
            background: #282828;
            border-radius: 8px;
            margin: 1rem auto;
            max-width: 300px;
        }
        
        .total-label {
            color: #b3b3b3;
            font-size: 1rem;
            margin-bottom: 0.5rem;
        }
        
        .total-value {
            color: #1ed760;
            font-size: 2rem;
            font-weight: 500;
        }
                
        .grade-header {
            margin-top: 1rem;
            margin-bottom: 2rem;
            text-align: center;
            color: #1ed760;
            font-size: 2rem;
            font-weight: bold;
        }
        .streamlit-expanderHeader {
            background-color: transparent !important;
            font-size: 1.2rem !important;
            color: #1ed760 !important;
            margin-top: 1rem !important;
        }
        .stExpander {
            margin-top: -3rem !important;
            margin-bottom: 2rem !important;
        }
                
        .filter-container {
            padding: 1rem 0;
        }

        @media (max-width: 768px) {
            .total-section {
                margin: 0.5rem auto;
                padding: 0.75rem;
            }
            
            .total-value {
                font-size: 1.5rem;
            }
            
            .spotify-header {
                font-size: 1.25rem;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(get_spotify_style(), unsafe_allow_html=True)

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
        filters_to_include=['grade_grain', 'route_type', 'date'],
        filter_title="Filter your data") 
    
    grade_grain = filters.get('grade_grain', 'base')
    route_type = None if filters.get('route_type', 'All') == 'All' else [filters.get('route_type', 'All')]

    start_date = filters.get('year_start')
    end_date = filters.get('year_end')

    sends_df, falls_df = get_chart_data(
        _conn=conn,
        user_id=user_id,
        grade_grain=grade_grain,
        route_type=route_type,
        year_start=start_date,
        year_end=end_date    
    )

    ordered_grades = sends_df['grade'].tolist()

    most_common_grade = metrics.top_grade(conn,level=grade_grain, user_id=user_id)

    """
    st.markdown(
        f'''
        <div class='total-section'>
            <div class='total-label'>Most Common Grade</div>
            <div class='total-value'>{most_common_grade}</div>
        </div>
        ''',
        unsafe_allow_html=True
    )
    """
    st.markdown("""
    <style>
    .chart-title {
        margin-top: -2rem !important;  # Adjust this value as needed
        margin-bottom: 1rem;
        text-align: center;
        color: white;
        font-size: 24px;
        font-weight: bold;
    }
    </style>
    <div class="chart-title">Your Grade Distribution</div>
""", unsafe_allow_html=True)

    fig = create_figure(sends_df, falls_df, ordered_grades)

  # Create containers
    chart_container = st.container()
    details_container = st.container()


    with chart_container:
        # Enable selection events
        selected = st.plotly_chart(
            fig,
            use_container_width=True,
            config={'displayModeBar': False},
            on_select="rerun",  # Enable selection events
            key="grade_dist_chart"
        )

        # Handle selection events
    if selected and selected.selection and len(selected.selection.points) > 0:
            point = selected.selection.points[0]
            
            
            # Check if we have the expected data
            if all(key in point for key in ['y', 'x', 'curve_number']):
                grade = point['y']
                is_send = float(point['x']) < 0
                curve_number = point['curve_number']
                selected_route_type = fig.data[curve_number].name.split('(')[1].rstrip(')')
                
                details = metrics.get_route_details(
                    conn=conn,
                    grade=grade,
                    route_type=selected_route_type,
                    tick_type='send' if is_send else 'fall',
                    user_id=user_id,
                    grade_grain=grade_grain,
                    year_start=start_date,
                    year_end=end_date
                )

                
                with details_container:
                    st.write(f"### {grade} {selected_route_type} {'Sends' if is_send else 'Falls'}")
                    
                    display_df = pd.DataFrame(details)
                    
                    if not display_df.empty:
                        display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
                        display_df = display_df.drop(columns=['route_type', 'pitches'])
                        display_df['link'] = display_df.apply(
                            lambda x: f"{x['route_url']}#{x['route_name']}", 
                            axis=1
                        )
                        st.dataframe(
                            display_df,
                            column_config={
                                "link": st.column_config.LinkColumn("Route Name",display_text=".*#(.*)"),
                                "original_grade": "Grade",
                                "date": "Date",
                                "tick_type": "Style",
                                "main_area": "Location"
                            },
                            hide_index=True,
                            column_order=["link", "main_area", "date", "tick_type", "original_grade"]
                        )
                    else:
                        st.write("No routes found.")
            else:
                st.write("Please click on a bar in the chart to see details.")
