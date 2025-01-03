import streamlit as st
import pandas as pd
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import src.analysis.mp_racked_metrics as metrics

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

def route_tag_filter(df=None, conn=None, user_id=None, year_start=None, year_end=None):  
    # Combined filter for characteristic type and its corresponding tags 
    st.write("Route Characteristics") 

    tag_type = st.radio(
        "",
        options=[
            'style', 'feature', 'descriptor', 'rock_type'
        ],
        format_func=lambda x: {
            'style': 'Styles',
            'feature': 'Features',
            'descriptor': 'Route Descriptors',
            'rock_type': 'Rock Types'
        }.get(x, x.title()),
        key='tag_type_filter',
        label_visibility="collapsed",
        horizontal=True  # Make it horizontal
    )

    tag_data = metrics.top_tags(
        conn, 
        tag_type, 
        user_id=user_id,
        year_start=year_start,
        year_end=year_end
    )
    tag_df = pd.DataFrame(tag_data, columns=['Type', 'Tag', 'Count']).head(10)
    
    # Select tags using multiselect
    selected_tags = st.multiselect(
        f"Filter by {tag_type.replace('_', ' ').title()}",
        options=tag_df['Tag'].tolist(),
        key='style_filter'
    )
    
    return tag_type, selected_tags

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

def render_filters(df=None, filters_to_include=None, filter_title="Filters", conn=None, user_id=None):
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
        'tick_type': tick_type_filter
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
        if 'date' in filters_to_include:
            year_start, year_end = filter_functions['date'](df)
            results['year_start'] = year_start
            results['year_end'] = year_end
        if 'route_tag' in filters_to_include:
            tag_type, selected_tags = route_tag_filter(
                df=df,
                conn=conn,
                user_id=user_id,
                year_start=results.get('year_start'),
                year_end=results.get('year_end')
            )
            results['tag_type'] = tag_type
            results['selected_tags'] = selected_tags
        for filter_name in filters_to_include:
            if filter_name not in ['date', 'route_tag'] and filter_name in filter_functions:
                results[filter_name] = filter_functions[filter_name](df)       
    return results