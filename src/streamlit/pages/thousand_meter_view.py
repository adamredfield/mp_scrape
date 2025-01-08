import streamlit as st
import plotly.express as px
from datetime import datetime
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import src.analysis.mp_racked_metrics as metrics
from src.streamlit.styles import get_spotify_style
from src.streamlit.filters import  date_filter
from src.analysis.filters_ctes import available_years
import pandas as pd

st.markdown(get_spotify_style(), unsafe_allow_html=True)

user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')

years_df = available_years(conn, user_id)

def get_highest_grade(grades, grade_sort_df):
    if grades.isna().all():
        return None
    valid_grades = grades.dropna()
    if len(valid_grades) == 0:
        return None
    
    grade_orders = pd.merge(
        pd.DataFrame({'grade': valid_grades}),
        grade_sort_df[['grade', 'sort_order']],
        on='grade',
        how='left'
    )
    if len(grade_orders) == 0:
        return None
    return grade_orders.loc[grade_orders['sort_order'].idxmax(), 'grade']

def period_filter():
    period_filter_type = st.radio(
        "",
        options=["All Time", "By Season", "By Month"],
        horizontal=True,
        key="period_filter__type_radio",
        label_visibility="collapsed"
    )

    if period_filter_type == "All Time":
        return "all", None
    
    elif period_filter_type == "By Season":
        season = st.selectbox(
            "Season",
            options=['Winter', 'Spring', 'Summer', 'Fall'],
            format_func=lambda x: x
        )
        return "season", season
    
    else: 
        month = st.selectbox(
            "Month",
            options=range(1, 13),
            format_func=lambda x: datetime(2000, x, 1).strftime('%B')
        )
        return "month", month

if 'filter_state' not in st.session_state:
    st.session_state.filter_state = {
        'period_type': None,
        'period_value': None,
        'year_start': None,
        'year_end': None
    }

year_start, year_end = date_filter(years_df)
period_type, period_value = period_filter()

current_state = {
    'period_type': period_type,
    'period_value': period_value,
    'year_start': year_start,
    'year_end': year_end
}

if current_state != st.session_state.filter_state:
    st.session_state.filter_state = current_state.copy()
    st.rerun()

if year_start is not None and year_end is not None:
    stats_df = metrics.get_period_stats(
        conn=conn,
        user_id=user_id,
        period_type=period_type,
        period_value=period_value,
        year_start=year_start,
        year_end=year_end
    )

    if period_type == 'season' and period_value:
        seasonal_data = stats_df[stats_df['period'].str.startswith(period_value)]
        
        grade_sort_query = """
        SELECT grade, grade_system, sort_order 
        FROM routes.grade_sort 
        WHERE grade_system IN ('YDS', 'Boulder', 'Aid')
        """
        grade_sort_df = conn.query(grade_sort_query)
        
        sport_grades = grade_sort_df[grade_sort_df['grade_system'] == 'YDS']
        boulder_grades = grade_sort_df[grade_sort_df['grade_system'] == 'Boulder']
        aid_grades = grade_sort_df[grade_sort_df['grade_system'] == 'Aid']
        
        total_days = seasonal_data['days_logged'].sum()
        total_distance = seasonal_data['total_distance'].sum()
        total_pitches = seasonal_data['total_pitches'].sum()
        total_routes = seasonal_data['total_routes_climbed'].sum()
        highest_sport = get_highest_grade(seasonal_data['highest_sport_grade'], sport_grades)
        highest_trad = get_highest_grade(seasonal_data['highest_trad_grade'], sport_grades)
        highest_boulder = get_highest_grade(seasonal_data['highest_boulder'], boulder_grades)
        highest_aid = get_highest_grade(seasonal_data['highest_aid'], aid_grades)
        
        stats_df = pd.DataFrame([{
            'period': f"{period_value} {year_start}-{year_end}",
            'days_logged': total_days,
            'highest_trad_grade': highest_trad,
            'highest_sport_grade': highest_sport,
            'highest_boulder': highest_boulder,
            'highest_aid': highest_aid,
            'avg_distance_per_day': float(total_distance) / float(total_days) if total_days > 0 else 0,
            'avg_pitches_per_day': float(total_pitches) / float(total_days) if total_days > 0 else 0,
            'total_distance': float(total_distance),
            'total_pitches': float(total_pitches),
            'total_routes_climbed': int(total_routes),
            'total_unique_routes': None,
            'avg_routes_per_day': float(total_routes) / float(total_days) if total_days > 0 else 0,
            'avg_route_length': float(total_distance) / float(total_routes) if total_routes > 0 else 0
        }])
    elif period_type == 'month' and period_value:
        month_name = datetime(2000, period_value, 1).strftime('%b')
        monthly_data = stats_df[stats_df['period'].str.contains(month_name)]

        grade_sort_query = """
        SELECT grade, grade_system, sort_order 
        FROM routes.grade_sort 
        WHERE grade_system IN ('YDS', 'Boulder', 'Aid')
        """
        grade_sort_df = conn.query(grade_sort_query)

        sport_grades = grade_sort_df[grade_sort_df['grade_system'] == 'YDS']
        boulder_grades = grade_sort_df[grade_sort_df['grade_system'] == 'Boulder']
        aid_grades = grade_sort_df[grade_sort_df['grade_system'] == 'Aid']
        highest_sport = get_highest_grade(monthly_data['highest_sport_grade'], sport_grades)
        highest_trad = get_highest_grade(monthly_data['highest_trad_grade'], sport_grades)  # Trad uses YDS
        highest_boulder = get_highest_grade(monthly_data['highest_boulder'], boulder_grades)
        highest_aid = get_highest_grade(monthly_data['highest_aid'], aid_grades)
        total_days = monthly_data['days_logged'].sum()
        total_distance = monthly_data['total_distance'].sum()
        total_pitches = monthly_data['total_pitches'].sum()
        total_routes = monthly_data['total_routes_climbed'].sum()
                
        stats_df = pd.DataFrame([{
            'period': f"{month_name} {year_start}-{year_end}",
            'days_logged': total_days, #
            'highest_trad_grade': highest_trad,#
            'highest_sport_grade': highest_sport,#
            'highest_boulder': highest_boulder,#
            'highest_aid': highest_aid,#
            'avg_distance_per_day': float(total_distance) / float(total_days) if total_days > 0 else 0,
            'avg_pitches_per_day': float(total_pitches) / float(total_days) if total_days > 0 else 0,
            'total_distance': float(total_distance), #
            'total_pitches': float(total_pitches), #
            'total_routes_climbed': int(total_routes), #
            'total_unique_routes': None,  # Set to None for multiple years
            'avg_routes_per_day': float(total_routes) / float(total_days) if total_days > 0 else 0,
            'avg_route_length': float(total_distance) / float(total_routes) if total_routes > 0 else 0
        }])
    elif period_type == 'all':
        stats_df = stats_df[stats_df['period'] == 'All Time']
    
    st.markdown("""
    <style>
                        .block-container {
            padding-bottom: 10rem !important;
            max-width: 100%;
        }
    .stat-card {
        background-color: rgba(32, 33, 35, 0.7);
        border-radius: 10px;
        padding: 10px;
        margin: 10px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center; 
    }

    .card-title {
        color: white;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 15px;
        text-align: center;
    }

    .stat-label {
        color: rgba(255, 255, 255, 0.8);
        font-size: 14px;
        font-weight: 500;
        margin-bottom: 5px;
    }

    .stat-value {
        color: #1DB954;
        font-size: 24px;
        font-weight: 700;
    }

    .grade-pill {
        background-color: #1DB954;
        color: black;
        padding: 5px 15px;
        border-radius: 15px;
        font-weight: 600;
        display: inline-block;
        margin: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="stat-card">
        <div class="card-title">💪 Practice Makes Perfect</div>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
            <div>
                <div class="stat-label">Days on Rock</div>
                <div class="stat-value">{} Days</div>
            </div>
            <div>
                <div class="stat-label">Total Distance</div>
                <div class="stat-value">{:,.0f} ft</div>
            </div>
            <div>
                <div class="stat-label">Total Pitches</div>
                <div class="stat-value">{}</div>
            </div>
            <div>
                <div class="stat-label">Routes Climbed</div>
                <div class="stat-value">{}</div>
            </div>
        </div>
    </div>
    """.format(
        stats_df['days_logged'].iloc[0],
        stats_df['total_distance'].iloc[0],
        stats_df['total_pitches'].iloc[0],
        stats_df['total_routes_climbed'].iloc[0]
    ), unsafe_allow_html=True)

    # Personal Leaderboard Section
    st.markdown("""
    <div class="stat-card">
        <div class="card-title">🏆 Personal Leaderboard</div>
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; text-align: center;">
            <div>
                <div class="stat-label">Sport</div>
                <div class="grade-pill">{}</div>
            </div>
            <div>
                <div class="stat-label">Trad</div>
                <div class="grade-pill">{}</div>
            </div>
            <div>
                <div class="stat-label">Boulder</div>
                <div class="grade-pill">{}</div>
            </div>
            <div>
                <div class="stat-label">Aid</div>
                <div class="grade-pill">{}</div>
            </div>
        </div>
    </div>
    """.format(
        stats_df['highest_sport_grade'].iloc[0] or '-',
        stats_df['highest_trad_grade'].iloc[0] or '-',
        stats_df['highest_boulder'].iloc[0] or '-',
        stats_df['highest_aid'].iloc[0] or '-'
    ), unsafe_allow_html=True)

    # Getting After It Section
    st.markdown("""
    <div class="stat-card">
        <div class="card-title">🚀 Getting After It</div>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
            <div>
                <div class="stat-label">Daily Distance</div>
                <div class="stat-value">{:.0f} ft</div>
            </div>
            <div>
                <div class="stat-label">Daily Pitches</div>
                <div class="stat-value">{:.1f}</div>
            </div>
            <div>
                <div class="stat-label">Routes per Day</div>
                <div class="stat-value">{:.1f}</div>
            </div>
            <div>
                <div class="stat-label">Avg Route Height</div>
                <div class="stat-value">{:.0f} ft</div>
            </div>
        </div>
    </div>
    """.format(
        stats_df['avg_distance_per_day'].iloc[0],
        stats_df['avg_pitches_per_day'].iloc[0],
        stats_df['avg_routes_per_day'].iloc[0],
        stats_df['avg_route_length'].iloc[0]
    ), unsafe_allow_html=True)