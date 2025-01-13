import src.analysis.mp_racked_metrics as metrics
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import os
import sys
from src.analysis.mp_racked_metrics import grade_sort_key

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.analysis.filters_ctes import available_years
from src.streamlit.filters import render_filters
from src.streamlit.styles import get_spotify_style
from streamlit_cookies_controller import CookieController

cookie_controller = CookieController()

current_page = st.query_params.get("page", "Grade Pyramid")
cookie_controller.set('current_page', current_page)

if not st.session_state.get('authenticated'):
    st.switch_page("mp_racked.py")

user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')

years_df = available_years(conn, user_id)

filters = render_filters(
    df=years_df,
    filters_to_include=['grade_grain', 'route_type', 'date', 'tick_type'],
    filter_title="Filter your data")


@st.cache_data
def get_chart_data(_conn, user_id, grade_grain, route_type,
                   year_start, year_end, tick_types=None):
    """Cache the data fetching"""
    sends = metrics.get_grade_distribution(
        _conn,
        route_types=route_type,
        level=grade_grain,
        year_start=year_start,
        year_end=year_end,
        user_id=user_id,
        tick_types=tick_types,
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

    send_hover_template = """
    %{y}<br>
    <b style='color: #1ed760'>%{customdata} sends</b><br>
    <i>Click for details</i>
    <extra></extra>"""

    fall_hover_template = """
    %{y}<br>
    <b style='color: #E57373'>%{x} falls</b><br>
    <i>Click for details</i>
    <extra></extra>"""

    # sends
    for route_type in sends_df['route_type'].unique():
        mask = sends_df['route_type'] == route_type
        fig.add_trace(go.Bar(
            name=f'Sends ({route_type})',
            y=sends_df[mask]['grade'],
            x=-sends_df[mask]['count'],
            orientation='h',
            width=0.8,
            marker=dict(
                color=sends_colors.get(route_type, '#1ed760'),
                opacity=0.8,
                line=dict( 
                    width=1,
                    color='rgba(255,255,255,0.3)'
                )
            ),
            hovertemplate=send_hover_template,
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

    # Tick interval based on max value
    if max_val <= 10:
        tick_interval = 2
    elif max_val <= 30:
        tick_interval = 5
    else:
        tick_interval = 10

    # evenly spaced ticks
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
        margin=dict(l=10, r=10, t=60, b=10),
        legend={
            'orientation': 'h',
            'yanchor': 'bottom',
            'y': 1.02,
            'xanchor': 'center',
            'x': 0.4,
            'font': {'color': '#F5F5F5'},
            'groupclick': 'toggleitem',
            'itemsizing': 'constant'
        },
        xaxis=dict(
            title='Number of Climbs',
            color='#F5F5F5',
            gridcolor='rgba(255,255,255,0.1)',
            zeroline=True,
            zerolinecolor='#F5F5F5',
            zerolinewidth=0.5,
            tickmode='array',
            ticktext=tick_texts,
            tickvals=tick_vals,
            fixedrange=True,
            rangeslider=dict(visible=False),
            constrain='domain'
        ),
        yaxis=dict(
            title='Grade',
            color='#F5F5F5',
            gridcolor='rgba(255,255,255,0.1)',
            categoryorder='array',
            categoryarray=ordered_grades[::-1],
            type='category',
            tickmode='array',
            ticktext=ordered_grades[::-1],
            tickvals=ordered_grades[::-1],
            fixedrange=True,
            constrain='domain'
        ),
        dragmode=False,
        clickmode='event',
        hovermode='closest',
        height=600
    )
    return fig


st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 10rem !important;
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
        color: #F5F5F5;
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
        margin-top: -3.5rem !important;
        margin-bottom: -3rem !important;
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

grade_grain = filters.get('grade_grain', 'base')
route_type = filters.get('route_type') if filters.get('route_type') else None

start_date = filters.get('year_start')
end_date = filters.get('year_end')

sends_df, falls_df = get_chart_data(
    _conn=conn,
    user_id=user_id,
    grade_grain=grade_grain,
    route_type=route_type,
    year_start=start_date,
    year_end=end_date,
    tick_types=filters.get('tick_type')
)

if sends_df.empty:
    st.stop()

all_grades = set(sends_df['grade'].tolist())
if not falls_df.empty:
    all_grades.update(falls_df['grade'].tolist())

ordered_grades = sorted(list(all_grades), 
                       key=lambda x: grade_sort_key(x)) 

fig = create_figure(sends_df, falls_df, ordered_grades)


chart_container = st.container()
details_container = st.container()

with chart_container:
    selected = st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            'scrollZoom': False,
            'displayModeBar': False,
            'doubleClick': False,
            'dragmode': False,
            'responsive': True,
            'showAxisDragHandles': False,
            'showAxisRangeEntryBoxes': False,
            'showTips': False,
            'modeBarButtonsToRemove': [
                'zoom',
                'pan',
                'select',
                'lasso2d',
                'zoomIn2d',
                'zoomOut2d',
                'autoScale2d',
                'resetScale2d'
            ],
            'editable': False,
            'edits': {
                'legendPosition': False,
                'legendText': False,
                'annotationPosition': False,
                'annotationTail': False,
                'annotationText': False
            }
        },
        on_select="rerun",
        key="grade_dist_chart"
    )

if selected and selected.selection and len(selected.selection.points) > 0:
    point = selected.selection.points[0]

    if all(key in point for key in ['y', 'x', 'curve_number']):
        grade = point['y']
        is_send = float(point['x']) < 0
        curve_number = point['curve_number']
        selected_route_type = fig.data[curve_number].name.split('(')[
            1].rstrip(')')

        details = metrics.get_route_details(
            conn=conn,
            grade=grade,
            clicked_type=selected_route_type,
            filtered_types=route_type,
            tick_type='send' if is_send else 'fall',
            tick_types=filters.get('tick_type'),
            user_id=user_id,
            grade_grain=grade_grain,
            year_start=start_date,
            year_end=end_date
        )

        with details_container:
            st.write(
                f"### {grade} {selected_route_type} {
                    'Sends' if is_send else 'Falls'}")

            display_df = pd.DataFrame(details)

            if not display_df.empty:
                display_df['date'] = pd.to_datetime(
                    display_df['date']).dt.strftime('%m-%d-%y')
                display_df = display_df.drop(columns=['route_type', 'pitches'])
                display_df['link'] = display_df.apply(
                    lambda x: f"{x['route_url']}#{x['route_name']}",
                    axis=1
                )
                st.dataframe(
                    display_df,
                    column_config={
                        "link": st.column_config.LinkColumn("Route Name", display_text=".*#(.*)", width=125),
                        "original_grade": "Grade",
                        "date": st.column_config.Column("Date", width=70),
                        "tick_type": st.column_config.Column("Style", width=90),
                    },
                    hide_index=True,
                    column_order=[
                        "link", "date", "tick_type", "original_grade"]
                )
            else:
                st.write("No routes found.")
    else:
        st.write("Please click on a bar in the chart to see details.")
