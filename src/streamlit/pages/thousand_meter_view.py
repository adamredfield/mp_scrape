from datetime import datetime, timedelta
import calendar
from src.analysis.filters_ctes import estimated_lengths_cte
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import src.analysis.mp_racked_metrics as metrics
import streamlit as st
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.analysis.filters_ctes import available_years, get_pitch_preference_lengths
from src.streamlit.filters import render_filters
from src.streamlit.styles import get_spotify_style
from src.analysis.filters_ctes import add_user_filter


st.markdown(get_spotify_style(), unsafe_allow_html=True)

if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "📊 Stats"

st.markdown("""
    <style>
        /* Center just the tab labels */
        [data-baseweb="tab-list"] {
            display: flex;
            justify-content: center;
            gap: 10rem;
        }
        /* Center radio buttons */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            display: flex;
            justify-content: center;
        }
        
        /* If needed, also adjust the space between tabs and first card */
        .stTabs [data-baseweb="tab-list"] {
            margin-top: 1rem;  /* Adjust this value as needed */
        }

        /* Center the radio options themselves */
        div[role="radiogroup"] {
            display: flex;
            justify-content: center;
            gap: 1rem;         
        }
    </style>
""", unsafe_allow_html=True)

user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')

years_df = available_years(conn, user_id)

filter_results = render_filters(
    df=years_df,
    filters_to_include=['date', 'period'],
    filter_title="Filter Options",
    conn=conn,
    user_id=user_id
)

year_start = filter_results['year_start']
year_end = filter_results['year_end']
period_type = filter_results['period_type']
period_value = filter_results['period_value']


def display_year(
        climbing_days_df,
        year=None,
        time_period='Full Year',
        period_value=None,
        show_colorbar=True):
    if year is None:
        year = datetime.now().year

    year = int(year)

    seasons = {
        'Winter': {
            'dates': (datetime(year, 1, 1).date(), datetime(year, 3, 31).date()),
            'months': ['Jan', 'Feb', 'Mar']
        },
        'Spring': {
            'dates': (datetime(year, 4, 1).date(), datetime(year, 6, 30).date()),
            'months': ['Apr', 'May', 'Jun']
        },
        'Summer': {
            'dates': (datetime(year, 7, 1).date(), datetime(year, 9, 30).date()),
            'months': ['Jul', 'Aug', 'Sep']
        },
        'Fall': {
            'dates': (datetime(year, 10, 1).date(), datetime(year, 12, 31).date()),
            'months': ['Oct', 'Nov', 'Dec']
        }
    }
    if time_period == 'season':
        if period_value not in seasons:
            raise ValueError(
                f"Invalid season: {period_value}. Must be one of {
                    list(
                        seasons.keys())}")
        d1, d2 = seasons[period_value]['dates']
        month_names = seasons[period_value]['months']
    elif time_period == 'month':
        month_num = int(period_value)
        if not (1 <= month_num <= 12):
            raise ValueError(f"Invalid month number: {month_num}")
        d1 = datetime(year, month_num, 1).date()
        d2 = datetime(
            year, month_num, calendar.monthrange(
                year, month_num)[1]).date()
        month_names = [calendar.month_abbr[month_num]]
    else:  # Full Year
        d1 = datetime(year, 1, 1).date()
        d2 = datetime(year, 12, 31).date()
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    number_of_days = (d2 - d1).days + 1
    data = np.zeros(number_of_days)

    if 'date' in climbing_days_df.columns:
        climbing_days_df['date'] = pd.to_datetime(climbing_days_df['date'])
        mask = (climbing_days_df['date'].dt.date >= d1) & (
            climbing_days_df['date'].dt.date <= d2)
        period_data = climbing_days_df[mask]
        for idx, row in period_data.iterrows():
            day_of_year = (row['date'].date() - d1).days
            if 0 <= day_of_year < number_of_days:
                data[day_of_year] = row['distance_climbed']

    dates_in_year = [(datetime(d1.year, d1.month, d1.day) + timedelta(days=i))
                     for i in range(number_of_days)]
    weekdays_in_year = [i.weekday() for i in dates_in_year]

    weeknumber_of_dates = []
    for i in dates_in_year:
        inferred_week_no = int(i.strftime("%V"))
        if inferred_week_no >= 52 and i.month == 1:
            weeknumber_of_dates.append(0)
        elif inferred_week_no == 1 and i.month == 12:
            weeknumber_of_dates.append(53)
        else:
            weeknumber_of_dates.append(inferred_week_no)

    text = [f"{d.strftime('%Y-%m-%d')}: {int(dist)}ft climbed"
            for d, dist in zip(dates_in_year, data)]

    colorscale = [
        [0, 'rgb(15,15,15)'],        # Darker background for 0
        [0.1, 'rgb(45,50,120)'],
        [0.25, 'rgb(65,105,180)'],   # Brighter blue (~600ft)
        [0.4, 'rgb(80,180,180)'],    # Teal (~1000ft)
        [0.6, 'rgb(120,210,120)'],   # Light green (~2000ft)
        [1.0, 'rgb(200,250,0)']      # Bright yellow (3000ft+)
    ]

    if time_period == 'season' or time_period == 'month':
        unique_weeks = sorted(set(weeknumber_of_dates))
        if time_period == 'season':
            total_weeks = len(unique_weeks)
            if total_weeks < 3:
                month_positions = unique_weeks
            else:
                month_positions = [
                    unique_weeks[0], 
                    unique_weeks[total_weeks // 2], 
                    unique_weeks[-1]  
                ]
        else:  
            month_positions = [unique_weeks[len(unique_weeks) // 2]]
    else:
        month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if number_of_days == 366:
            month_days[1] = 29
        month_positions = (np.cumsum(month_days) - 15) / 7

    fig = go.Figure(data=[
        go.Heatmap(
            x=weeknumber_of_dates,
            y=weekdays_in_year,
            z=data,
            text=text,
            hoverinfo='text',
            xgap=3,
            ygap=3,
            colorscale=colorscale,
            showscale=show_colorbar,
            zmin=0,
            zmax=3000,
            colorbar=dict(
                orientation='h',
                thickness=10,
                lenmode='fraction',
                len=1,
                y=1.05,
                x=0.5,
                xanchor='center',
                yanchor='bottom',
                ticktext=['0', '1000', '2000', '3000'],
                tickvals=[0, 1000, 2000, 3000],
                tickmode='array',
                bgcolor='rgba(0,0,0,0)',
                tickfont=dict(
                    color='#9e9e9e',
                    size=10
                ),
                title=''
            )
        )
    ])

    # month separator lines
    kwargs = dict(
        mode='lines',
        line=dict(
            color='#9e9e9e',
            width=1,
        ),
        hoverinfo='skip',
        showlegend=False
    )

    for date, dow, wkn in zip(
            dates_in_year, weekdays_in_year, weeknumber_of_dates):
        if date.day == 1:
            fig.add_trace(
                go.Scatter(
                    x=[wkn - .5, wkn - .5],
                    y=[dow - .5, 6.5],
                    **kwargs,
                )
            )
            if dow:
                fig.add_trace(
                    go.Scatter(
                        x=[wkn - .5, wkn + .5],
                        y=[dow - .5, dow - .5],
                        **kwargs,
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=[wkn + .5, wkn + .5],
                        y=[dow - .5, -.5],
                        **kwargs,
                    )
                )

    fig.update_layout(
        plot_bgcolor='black',
        paper_bgcolor='black',
        font_color='white',
        height=150,
        yaxis=dict(
            showticklabels=False,
            showline=False,
            showgrid=False,
            zeroline=False,
            autorange="reversed",
            ticks="",
            showticksuffix="none",
            fixedrange=True  # Add this line
        ),
        xaxis=dict(
            showline=False,
            showgrid=False,
            zeroline=False,
            tickmode='array',
            ticktext=month_names,
            tickvals=month_positions,
            fixedrange=True  # Add this line
        ),
        font={'size': 10, 'color': '#9e9e9e'},
        margin=dict(
            t=0,
            l=0,
            r=0,
            b=40,
            pad=0
        ),
    )
    return fig


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
    if len(grade_orders) == 0 or grade_orders['sort_order'].isna().all():
        return None
    return grade_orders.loc[grade_orders['sort_order'].idxmax(), 'grade']


if 'filter_state' not in st.session_state:
    st.session_state.filter_state = {
        'period_type': None,
        'period_value': None,
        'year_start': None,
        'year_end': None
    }

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
        year_end=year_end,
        pitch_preference=st.session_state.pitches_preference
    )

tab1, tab2 = st.tabs(["Stats", "Visualizations"])

with tab1:
    if current_state != st.session_state.filter_state:
        st.session_state.filter_state = current_state.copy()
        # Preserve the active tab through the rerun
        stored_tab = st.session_state.active_tab
        st.rerun()

    stats_df['avg_distance_per_day'] = (
        stats_df['total_distance'] /
        stats_df['days_logged']).round(0)
    stats_df['avg_pitches_per_day'] = (
        stats_df['total_pitches'] /
        stats_df['days_logged']).round(1)
    stats_df['avg_routes_per_day'] = (
        stats_df['non_boulder_routes'] /
        stats_df['days_logged']).round(1)
    stats_df['avg_route_length'] = (
        stats_df['non_boulder_distance'] /
        stats_df['non_boulder_routes']).round(0)

    stats_df = stats_df.fillna(0)

    if period_type == 'season' and period_value:
        seasonal_data = stats_df[stats_df['period'].str.startswith(
            period_value)]

        grade_sort_query = """
        SELECT grade, grade_system, sort_order
        FROM routes.grade_sort
        WHERE grade_system IN ('YDS', 'Boulder', 'Aid')
        """
        grade_sort_df = conn.query(grade_sort_query)

        sport_grades = grade_sort_df[grade_sort_df['grade_system'] == 'YDS']
        boulder_grades = grade_sort_df[grade_sort_df['grade_system'] == 'Boulder']
        aid_grades = grade_sort_df[grade_sort_df['grade_system'] == 'Aid']

        total_days = seasonal_data['days_logged'].sum() or 0
        total_distance = seasonal_data['total_distance'].sum() or 0
        total_pitches = seasonal_data['total_pitches'].sum() or 0
        total_routes = seasonal_data['non_boulder_routes'].sum() or 0
        highest_sport = get_highest_grade(
            seasonal_data['highest_sport_grade'], sport_grades)
        highest_trad = get_highest_grade(
            seasonal_data['highest_trad_grade'], sport_grades)
        highest_boulder = get_highest_grade(
            seasonal_data['highest_boulder'], boulder_grades)
        highest_aid = get_highest_grade(
            seasonal_data['highest_aid'], aid_grades)

        stats_df = pd.DataFrame([{
            'period': f"{period_value} {year_start}-{year_end}",
            'days_logged': total_days,
            'highest_trad_grade': highest_trad,
            'highest_sport_grade': highest_sport,
            'highest_boulder': highest_boulder,
            'highest_aid': highest_aid,
            'total_distance': float(total_distance),
            'total_pitches': float(total_pitches),
            'total_routes_climbed': int(total_routes),
            'total_unique_routes': None,
            'non_boulder_distance': seasonal_data['non_boulder_distance'].sum() or 0,
            'non_boulder_routes': seasonal_data['non_boulder_routes'].sum() or 0,
            'boulder_distance': seasonal_data['boulder_distance'].sum() or 0,
            'boulder_routes': seasonal_data['boulder_routes'].sum() or 0, 
            'roped_days': seasonal_data['roped_days'].sum() or 0
        }])
        stats_df['avg_distance_per_day'] = (
            stats_df['total_distance'] /
            stats_df['days_logged']).round(0)
        stats_df['avg_pitches_per_day'] = (
            stats_df['total_pitches'] /
            stats_df['days_logged']).round(1)
        stats_df['avg_routes_per_day'] = (
            stats_df['non_boulder_routes'] /
            stats_df['days_logged']).round(1)
        stats_df['avg_route_length'] = (
            stats_df['non_boulder_distance'] /
            stats_df['non_boulder_routes']).round(0)
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
        highest_sport = get_highest_grade(
            monthly_data['highest_sport_grade'], sport_grades)
        highest_trad = get_highest_grade(
            monthly_data['highest_trad_grade'],
            sport_grades)  # Trad uses YDS
        highest_boulder = get_highest_grade(
            monthly_data['highest_boulder'], boulder_grades)
        highest_aid = get_highest_grade(
            monthly_data['highest_aid'], aid_grades)
        total_days = monthly_data['days_logged'].sum()
        total_distance = monthly_data['total_distance'].sum()
        total_pitches = monthly_data['total_pitches'].sum()
        total_routes = monthly_data['non_boulder_routes'].sum()

        stats_df = pd.DataFrame([{
            'period': f"{month_name} {year_start}-{year_end}",
            'days_logged': total_days,
            'highest_trad_grade': highest_trad,
            'highest_sport_grade': highest_sport,
            'highest_boulder': highest_boulder,
            'highest_aid': highest_aid,
            'total_distance': float(total_distance),
            'total_pitches': float(total_pitches),
            'total_routes_climbed': int(total_routes),
            'total_unique_routes': None,  # Set to None for multiple years,
            'non_boulder_distance': monthly_data['non_boulder_distance'].sum() or 0,
            'non_boulder_routes': monthly_data['non_boulder_routes'].sum() or 0,
            'boulder_distance': monthly_data['boulder_distance'].sum() or 0,
            'boulder_routes': monthly_data['boulder_routes'].sum() or 0,
            'roped_days': monthly_data['roped_days'].sum() or 0
        }])
        stats_df['avg_distance_per_day'] = (
            stats_df['total_distance'] /
            stats_df['days_logged']).round(0)
        stats_df['avg_pitches_per_day'] = (
            stats_df['total_pitches'] /
            stats_df['days_logged']).round(1)
        stats_df['avg_routes_per_day'] = (
            stats_df['non_boulder_routes'] /
            stats_df['days_logged']).round(1)
        stats_df['avg_route_length'] = (
            stats_df['non_boulder_distance'] /
            stats_df['non_boulder_routes']).round(0)
    elif period_type == 'all':
        stats_df = stats_df[stats_df['period'] == 'Full Year']

    st.markdown("""
    <style>
    .stExpander {
        margin-top: -1rem !important;
        margin-bottom: -1rem !important;
    }
    .card-subtitle {
        color: rgba(255, 255, 255, 0.7);
        font-size: 0.9rem;
        text-align: center;
        margin: -10px 0 0px 0;  /* Negative top margin to bring it closer to title */
    }

    /* Reduce space between filter expander and first card */
    .block-container {
        margin-bottom: 10rem !important;
        max-width: 100%;
        }
    .stMain{
        margin-top: -1rem;}

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
        margin-bottom: 5px;
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


    print(f"Days logged: {stats_df['days_logged'].iloc[0]}")
    print(f"Total pitches: {stats_df['total_pitches'].iloc[0]}")
    print(f"Non boulder routes: {stats_df['non_boulder_routes'].iloc[0]}")
    print(f"Non boulder distance: {stats_df['non_boulder_distance'].iloc[0]}")
    print(f"Total routes climbed: {stats_df['total_routes_climbed'].iloc[0]}")
    print(f"Boulder routes: {stats_df['total_routes_climbed'].iloc[0] - stats_df['non_boulder_routes'].iloc[0]}")
    print(f"Boulder distance: {stats_df['boulder_distance'].iloc[0]}")

    st.markdown(
        """
        <div class="stat-card">
            <div class="card-title">💪 Practice Makes Perfect</div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
                <!-- Column 1: Time Metrics -->
                <div style="display: flex; flex-direction: column; gap: 20px;">
                    <div>
                        <div class="stat-label">Days on Rock</div>
                        <div class="stat-value">{:,.0f} Days</div>
                    </div>
                    <div>
                        <div class="stat-label">Total Pitches</div>
                        <div class="stat-value">{:,.0f}</div>
                    </div>
                </div>
                <!-- Column 2: Roped Metrics -->
                <div style="display: flex; flex-direction: column; gap: 20px;">
                    <div>
                        <div class="stat-label">Roped Routes</div>
                        <div class="stat-value">{:,.0f}</div>
                    </div>
                    <div>
                        <div class="stat-label">Rope Distance</div>
                        <div class="stat-value">{:,.0f} ft</div>
                    </div>
                </div>
                <!-- Column 3: Boulder Metrics -->
                <div style="display: flex; flex-direction: column; gap: 20px;">
                    <div>
                        <div class="stat-label">Boulders</div>
                        <div class="stat-value">{:,.0f}</div>
                    </div>
                    <div>
                        <div class="stat-label">Boulder Distance</div>
                        <div class="stat-value">{:,.0f} ft</div>
                    </div>
                </div>
            </div>
        </div>
        """.format(
            stats_df['days_logged'].iloc[0],
            stats_df['total_pitches'].iloc[0],
            stats_df['non_boulder_routes'].iloc[0],
            stats_df['non_boulder_distance'].iloc[0],
            stats_df['boulder_routes'].iloc[0],
            stats_df['boulder_distance'].fillna(0).iloc[0]),
        unsafe_allow_html=True)

    st.markdown("""
    <div class="stat-card">
        <div class="card-title">🏆 Personal Leaderboard</div>
        <div class="card-subtitle">Highest Grade Sent</div>
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

    st.markdown(
        """
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
                <div class="stat-label">Avg Route Length</div>
                <div class="stat-value">{:.0f} ft</div>
            </div>
        </div>
    </div>
    """.format(
            stats_df['non_boulder_distance'].iloc[0] /
            stats_df['roped_days'].iloc[0],
            stats_df['avg_pitches_per_day'].iloc[0],
            stats_df['non_boulder_routes'].iloc[0] /
            stats_df['roped_days'].iloc[0],
            stats_df['non_boulder_distance'].iloc[0] /
            stats_df['non_boulder_routes'].iloc[0]),
        unsafe_allow_html=True)

with tab2:
    if year_start is not None and year_end is not None:
        period_filter = ""
        if period_type == 'season':
            if period_value == 'Winter':
                period_filter = """
                    AND (
                        (EXTRACT(MONTH FROM date) IN (1, 2, 3))
                    )
                """
            else:
                season_ranges = {
                    'Spring': 'AND EXTRACT(MONTH FROM date) BETWEEN 4 AND 6',
                    'Summer': 'AND EXTRACT(MONTH FROM date) BETWEEN 7 AND 9',
                    'Fall': 'AND EXTRACT(MONTH FROM date) BETWEEN 10 AND 12'
                }
                period_filter = season_ranges[period_value]
        elif period_type == 'month':
            try:
                month_num = int(period_value)
                period_filter = f"AND EXTRACT(MONTH FROM date) = {month_num}"
            except (TypeError, ValueError):
                # If it's a month name, convert it to number
                month_num = datetime.strptime(period_value, '%B').month
                period_filter = f"AND EXTRACT(MONTH FROM date) = {month_num}"

        daily_climbs_query = f"""
        {estimated_lengths_cte}
        SELECT
            t.date,
            SUM(COALESCE(r.length_ft, el.estimated_length, 0)) as distance_climbed
        FROM routes.ticks t
        JOIN routes.routes r ON r.id = t.route_id
        LEFT JOIN estimated_lengths el ON el.id = t.route_id
        WHERE 1=1
        {add_user_filter(user_id)}
        AND EXTRACT(YEAR FROM date) BETWEEN {year_start} AND {year_end}
        {period_filter}
        GROUP BY t.date
        ORDER BY t.date
        """
        daily_climbs = conn.query(daily_climbs_query)

        years = list(range(year_end, year_start - 1, -1))
        latest_year = years[0]
        st.markdown(f"""
            <h4 style='
                margin: 0;
                padding: 0;
                font-size: 16px;
                color: white;
                line-height: 1;
            '>{latest_year}</h4>
        """, unsafe_allow_html=True)

        fig = display_year(
            daily_climbs,
            year=latest_year,
            time_period=period_type,
            period_value=period_value
        )
        st.plotly_chart(
            fig, use_container_width=True, config={
                'displayModeBar': False,
                'scrollZoom': False,
                'doubleClick': False,
                'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d'],
            })
        if len(years) > 1:
            with st.expander("📅 View Previous Years"):
                for year in years[1:]:
                    st.markdown(f"""
                        <h4 style='
                            margin: 0;
                            padding: 0;
                            font-size: 16px;
                            color: white;
                            line-height: 1;
                            margin-bottom: -20px;
                        '>{year}</h4>
                    """, unsafe_allow_html=True)

                    fig = display_year(
                        daily_climbs,
                        year=year,
                        time_period=period_type,
                        period_value=period_value,
                        show_colorbar=False
                    )
                    st.plotly_chart(
                        fig, use_container_width=True, config={
                            'displayModeBar': False,
                            'scrollZoom': False,
                            'doubleClick': False,
                            'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d'],
                        })

    metric = st.radio(
        "",
        ["Length (ft)", "Pitches"],
        horizontal=True,
        key="monthly_metric"
    )

    def get_metrics_query(
            period_type,
            year_start,
            year_end,
            user_id,
            pitch_preference):
        if period_type == 'season':
            metrics_query = f"""
            {estimated_lengths_cte},
            seasonal_data AS (
                SELECT
                    EXTRACT(YEAR FROM t.date)::text || ' ' ||
                    CASE
                        WHEN EXTRACT(MONTH FROM t.date) IN (12, 1, 2) THEN 'Winter'
                        WHEN EXTRACT(MONTH FROM t.date) IN (3, 4, 5) THEN 'Spring'
                        WHEN EXTRACT(MONTH FROM t.date) IN (6, 7, 8) THEN 'Summer'
                        ELSE 'Fall'
                    END as period,
                    SUM({get_pitch_preference_lengths(pitch_preference)}) as total_length,
                    COUNT(DISTINCT t.date) as days_climbed,
                    SUM(r.pitches) as total_pitches
                FROM routes.ticks t
                JOIN routes.routes r ON r.id = t.route_id
                LEFT JOIN estimated_lengths el ON el.id = t.route_id
                WHERE 1=1
                {add_user_filter(user_id)}
                AND EXTRACT(YEAR FROM date) BETWEEN {year_start} AND {year_end}
                GROUP BY
                    EXTRACT(YEAR FROM t.date),
                        CASE
                            WHEN EXTRACT(MONTH FROM t.date) IN (12, 1, 2) THEN 'Winter'
                            WHEN EXTRACT(MONTH FROM t.date) IN (3, 4, 5) THEN 'Spring'
                            WHEN EXTRACT(MONTH FROM t.date) IN (6, 7, 8) THEN 'Summer'
                            ELSE 'Fall'
                        END
                )
                SELECT *
                FROM seasonal_data
                ORDER BY
                    SPLIT_PART(period, ' ', 1)::int,
                    CASE SPLIT_PART(period, ' ', 2)
                        WHEN 'Winter' THEN 1
                        WHEN 'Spring' THEN 2
                        WHEN 'Summer' THEN 3
                        WHEN 'Fall' THEN 4
                    END
                """
        else:
            is_multiple_years = year_start != year_end

            if is_multiple_years:
                metrics_query = f"""
                {estimated_lengths_cte}
                SELECT
                    EXTRACT(YEAR FROM t.date)::text as period,
                    SUM({get_pitch_preference_lengths(pitch_preference)}) as total_length,
                    COUNT(DISTINCT t.date) as days_climbed,
                    SUM(r.pitches) as total_pitches
                FROM routes.ticks t
                JOIN routes.routes r ON r.id = t.route_id
                LEFT JOIN estimated_lengths el ON el.id = t.route_id
                WHERE 1=1
                {add_user_filter(user_id)}
                AND EXTRACT(YEAR FROM date) BETWEEN {year_start} AND {year_end}
                GROUP BY EXTRACT(YEAR FROM t.date)
                ORDER BY period
                """
            else:
                metrics_query = f"""
                {estimated_lengths_cte}
                SELECT
                    TO_CHAR(DATE_TRUNC('month', t.date), 'Month') as period,
                    SUM({get_pitch_preference_lengths(pitch_preference)}) as total_length,
                    COUNT(DISTINCT t.date) as days_climbed,
                    SUM(r.pitches) as total_pitches
                FROM routes.ticks t
                JOIN routes.routes r ON r.id = t.route_id
                LEFT JOIN estimated_lengths el ON el.id = t.route_id
                WHERE 1=1
                {add_user_filter(user_id)}
                AND EXTRACT(YEAR FROM date) = {year_start}
                GROUP BY
                    EXTRACT(MONTH FROM t.date),
                    TO_CHAR(DATE_TRUNC('month', t.date), 'Month')
                ORDER BY
                    EXTRACT(MONTH FROM t.date)
                """
        query = metrics_query
        return conn.query(query)

    data = get_metrics_query(
        period_type,
        year_start,
        year_end,
        user_id,
        pitch_preference=st.session_state.pitches_preference)

    fig = go.Figure()

    if metric == "Length (ft)":
        y_data = data['total_length']
        color = '#1DB954'
    else:
        y_data = data['total_pitches']
        color = '#1DB954'

    fig.add_trace(go.Bar(
        x=data['period'],
        y=y_data,
        marker_color=color,
        showlegend=False
    ))

    fig.update_layout(
        plot_bgcolor='black',
        paper_bgcolor='black',
        font_color='white',
        height=300,
        margin=dict(t=10, l=60, r=30, b=75),
        yaxis=dict(
            gridcolor='rgba(255, 255, 255, 0.1)',
            tickfont=dict(color='#E6EAF1'),
            title=dict(
                text=metric,
                font=dict(color='#E6EAF1')
            ),
            fixedrange=True  # Add this line
        ),
        xaxis=dict(
            tickformat='%b',
            gridcolor='rgba(255, 255, 255, 0.1)',
            fixedrange=True  
        )
    )

    st.plotly_chart(
        fig, use_container_width=True, config={
            'displayModeBar': False,
            'scrollZoom': False,
            'doubleClick': False,
            'modeBarButtonsToRemove': ['zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d'],
        })
