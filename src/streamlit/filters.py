import streamlit as st
import pandas as pd
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import src.analysis.mp_racked_metrics as metrics
from src.analysis.fa_queries import get_all_top_first_ascensionists

def commitment_grade_filter(df):
    """Commitment grade filter"""
    available_grades = sorted([g for g in df['commitment_grade'].unique() if pd.notna(g)])
    return st.multiselect(
        'Filter by Commitment Grade:',
        options=available_grades,
        key='commitment_grade_filter'
    )

def grade_type_filter(df=None):
    """Filter for different grade types (YDS, Hueco, Aid)"""
    return st.selectbox(
        "Grade Type",
        options=['All Grades', 'YDS', 'Hueco', 'Aid'],
        format_func=lambda x: {
            'All Grades': 'All Grades',
            'YDS': 'Rope Grades (YDS)',
            'Hueco': 'Boulder Grades (V Scale)',
            'Aid': 'Aid Grades (A/C)'
        }.get(x, x),
        key='grade_type_filter'
    )

def grade_grain_filter(df=None):
    """Grade filter"""
    return st.selectbox(
            "Grade Detail Level",
            options=['base', 'granular', 'original'],
            format_func=lambda x: x.title(),
            key='grade_grain_filter'
        )

def type_filter():
    """Route type filter"""
    return st.multiselect(
        'Filter by Route Type:',
        options=['Trad', 'Sport', 'Aid', 'Alpine'],
        key='route_type_filter'
    )

def length_filter(df):
    """Route length filter"""
    min_length = 500
    max_length = int(df['length'].max())
    return st.slider(
        'Minimum Route Length (ft):',
        min_value=min_length,
        max_value=max_length,
        value=min_length,
        step=100,
        key='length_filter'
    )

def date_filter(df):
    """Date range filter"""

    available_years = sorted(df['date'].dt.year.unique())

    date_filter_type = st.radio(
        "",
        options=["Single Year", "Custom Range"],
        horizontal=True,
        key="single_year_date_range_radio",
        label_visibility="collapsed" 
    )

    if date_filter_type == "Single Year":
        year = st.selectbox(
            'Year',
            options=sorted(available_years, reverse=True),
            index=sorted(available_years, reverse=True).index(2024)
        )
        return year, year
    else:
        col1, col2 = st.columns(2)
        with col1:
            year_start = st.selectbox(
                'From', 
                options=available_years,
                index=0
            )   
        with col2:
            valid_end_years = [y for y in available_years if y >= year_start]
            year_end = st.selectbox(
                'To', 
                options=valid_end_years,
                index=len(valid_end_years) - 1 
            )
        return year_start, year_end

def route_type_filter(df=None):
    """Filter for different climbing types"""
    return st.multiselect(
        "Climbing Type",
        options=['All', 'Boulder', 'Aid', 'Sport', 'Trad', 'Alpine'],
        default=['Sport', 'Trad', 'Alpine', 'Aid'],
        format_func=lambda x: {
            'All': 'All Types',
            'Boulder': 'Boulder',
            'Aid': 'Aid',
            'Sport': 'Sport',
            'Trad': 'Trad'
        }.get(x, x),
        key='climbing_type_filter'
    )

def generate_route_type_where_clause(route_types):
    if not route_types or 'All' in route_types:
        return ""
    
    type_conditions = []
    for route_type in route_types:
        type_conditions.append(f"r.route_type ILIKE '%{route_type}%'")
    
    return f"WHERE ({' OR '.join(type_conditions)})"

def route_tag_filter(df=None, conn=None, user_id=None, year_start=None, year_end=None):  
    tag_selections = {}
    tag_types = ['style', 'feature', 'descriptor', 'rock_type']

    total_selected = sum(len(st.session_state.get(f'filter_{tag_type}', [])) for tag_type in tag_types)
    label = f"Route Characteristics ({total_selected})" if total_selected > 0 else "Route Characteristics"

    st.markdown("""
        <style>
        .filter-pill {
            background-color: #2e2e2e;
            padding: 2px 8px;
            border-radius: 12px;
            margin: 2px;
            display: inline-block;
            font-size: 0.8em;
            border: 1px solid #3e3e3e;
        }
        .filter-type {
            color: #1DB954;
            font-weight: bold;
        }
        .filter-values {
            color: #ffffff;
        }
        .filter-container {
            line-height: 2;
            margin-top: 4px;
        }
        </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 3])
    with col1:
        with st.popover(label, use_container_width=True):
            if total_selected > 0:
                if st.button("Clear All Filters", type="secondary", use_container_width=True):
                    for tag_type in tag_types:
                        st.session_state[f'filter_{tag_type}'] = []
                    st.rerun()
                st.divider()

            tabs = st.tabs([
                'Styles',
                'Features',
                'Descriptors',
                'Rock Types'
            ])
            for tab, tag_type in zip(tabs, tag_types):
                with tab:
                    tag_data = metrics.top_tags(
                        conn, 
                        tag_type, 
                        user_id=user_id,
                        year_start=year_start,
                        year_end=year_end
                    )
                    tag_df = pd.DataFrame(tag_data, columns=['Type', 'Tag', 'Count']).head(10)
                    options = [f"{tag} ({count})" for tag, count in zip(tag_df['Tag'], tag_df['Count'])]

                    selected_tags = st.multiselect(
                        f"Select {tag_type.title()}",
                        options=options,
                        format_func=lambda x: x.split(' (')[0],
                        key=f'filter_{tag_type}'
                    )

                    if selected_tags:
                        # Store only the tag names without counts
                        tag_selections[tag_type] = [tag.split(' (')[0] for tag in selected_tags]
                        st.caption(f"Selected: {', '.join(tag.split(' (')[0] for tag in selected_tags)}")
    with col2:
        if total_selected > 0:
            pills = []
            for tag_type in tag_types:
                selected = st.session_state.get(f'filter_{tag_type}', [])
                if selected:
                    tag_names = [tag.split(' (')[0] for tag in selected]
                    pills.append(
                        f'<span class="filter-pill">'
                        f'<span class="filter-type">{tag_type.title()}</span>: '
                        f'<span class="filter-values">{", ".join(tag_names)}</span>'
                        f'</span>'
                    )
            
            st.markdown(" ".join(pills), unsafe_allow_html=True)
    
    return tag_selections

def tick_type_filter(df=None):
    """Filter for different tick types"""
    
    # Default send types
    default_sends = [
        'Lead / Pinkpoint',
        'Lead / Onsight',
        'Lead / Redpoint',
        'Lead / Flash',
        'Solo'
    ]
    
    # All available tick types
    all_tick_types = [
        'Lead / Pinkpoint',
        'Lead / Onsight',
        'Lead',
        'Follow',
        'Lead / Redpoint',
        'Lead / Flash',
        'Solo',
        'TR'
    ]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.caption("Default Send Types")
        selected_defaults = st.multiselect(
            "Default Sends",
            options=default_sends,
            default=default_sends,
            key='default_sends'
        )
    
    with col2:
        st.caption("Additional Send Types")
        additional_types = st.multiselect(
            "Additional Types",
            options=[t for t in all_tick_types if t not in default_sends],
            key='additional_sends'
        )
    
    selected_types = selected_defaults + additional_types
    return selected_types if selected_types else default_sends

def climbed_routes_filter():
    """Filter for climbed/unclimbed routes"""
    return st.radio(
        "Show Routes",
        options=['All Routes', 'Unclimbed', 'Climbed'],
        horizontal=True,
        key='climbed_routes_filter'
    )

def fa_filter(conn):
    """Filter for routes by first ascensionist"""
    fas = get_all_top_first_ascensionists(conn)
    return st.selectbox(
        "First Ascensionist",
        options=fas,
        key='fa_filter_key'
    )

def grade_filter(conn, route_types=None, user_id=None, year_start=None, year_end=None):
    """Filter for climbing grades with type-specific handling"""
    
    print("Starting grade_filter function")

    try:
        grade_data = metrics.get_available_grades(
            conn=conn,
            route_types=route_types
        )

        print(f"Grade data received: {grade_data[:5] if grade_data else 'No data'}")  # Debug
        
    except Exception as e:
        print(f"Error getting grade distribution: {str(e)}")  # Debug
        print(f"Arguments passed to get_grade_distribution:")  # Debug
        print(f"conn: {type(conn)}")
        print(f"route_types: {route_types}")
        print(f"year_start: {year_start}")
        print(f"year_end: {year_end}")
        print(f"user_id: {user_id}")
        return None, None
    
    if not grade_data:
        return None, None

    grade_types = {
        'YDS': [],
        'Boulder': [],
        'Aid': []
    }

    for item in grade_data:
        grade = item['grade']
        if grade.startswith('V'):
            grade_types['Boulder'].append(grade)
        elif grade.startswith(('A', 'C')):
            grade_types['Aid'].append(grade)
        elif grade.startswith('5.'):
            grade_types['YDS'].append(grade)

    print(f"Grade types populated: {grade_types}") 

    # Sort grades within each type
    for grade_type in grade_types:
        grade_types[grade_type] = sorted(list(set(grade_types[grade_type])), 
                                       key=metrics.grade_sort_key)
    print("Starting to create UI elements")  
    col1, col2 = st.columns([1, 3])
    with col1:
        with st.popover("Grade Filter", use_container_width=True):
            grade_system = st.radio(
                "Grade System",
                options=['YDS', 'Boulder', 'Aid'],
                horizontal=True
            )

            if grade_types[grade_system]:
                col1, col2 = st.columns(2)
                with col1:
                    min_grade = st.selectbox(
                        "Minimum",
                        options=grade_types[grade_system],
                        index=0,
                        key='min_grade'
                    )
                with col2:
                    max_grade_options = [g for g in grade_types[grade_system] 
                                       if metrics.grade_sort_key(g) >= metrics.grade_sort_key(min_grade)]
                    max_grade = st.selectbox(
                        "Maximum",
                        options=max_grade_options,
                        index=len(max_grade_options)-1,
                        key='max_grade'
                    )
            
                return grade_system, (min_grade, max_grade)
    
    return None, None

def render_filters(df=None, filters_to_include=None, filter_title="Filters", conn=None, user_id=None, default_years=None):
    """
    Render filter expander with specified filters
    
    Args:
        df: DataFrame containing the data
        filters_to_include: List of filter names to include
        Options: ['grade', 'type', 'length', 'date']
    """

    if 'filter_expander_state' not in st.session_state:
        st.session_state.filter_expander_state = False

    if filters_to_include is None:
        filters_to_include = ['grade', 'type', 'length', 'date']
    
    filter_functions = {
        'commitment_grade': commitment_grade_filter,
        'grade_grain': grade_grain_filter,
        'type': type_filter,
        'length': length_filter,
        'date': date_filter,
        'route_type': route_type_filter,
        'tick_type': tick_type_filter,
        'climbed_routes': climbed_routes_filter,
        'fa': fa_filter,
        'grade': grade_filter
    }

    st.markdown("""
        <style>
            /* Top filter styling */
            .top-filter {
                margin-top: -40px !important;
            }
            
            /* Route expanders styling */
            .route-expander {
                margin-top: -20px !important;
            }
        </style>
    """, unsafe_allow_html=True)
    results = {}
    with st.expander(filter_title, expanded=st.session_state.filter_expander_state):
        if 'date' not in filters_to_include and default_years:
            results['year_start'], results['year_end'] = default_years
        if 'date' in filters_to_include:
            year_start, year_end = filter_functions['date'](df)
            results['year_start'] = year_start
            results['year_end'] = year_end
        if 'route_tag' in filters_to_include:
            tag_selections = route_tag_filter(
                df=df,
                conn=conn,
                user_id=user_id,
                year_start=results.get('year_start'),
                year_end=results.get('year_end')
            )
            results['tag_selections'] = tag_selections
        if 'climbed_routes' in filters_to_include:
            results['climbed_filter'] = climbed_routes_filter()
        if 'fa' in filters_to_include:
            results['fa_filter'] = fa_filter(conn)
        if 'grade' in filters_to_include:
            results['grade_filter'] = grade_filter(conn, route_types=results.get('route_type'))
        for filter_name in filters_to_include:
            if filter_name not in ['date', 'route_tag', 'climbed_routes', 'fa', 'grade'] and filter_name in filter_functions:
                results[filter_name] = filter_functions[filter_name](df)       
    return results