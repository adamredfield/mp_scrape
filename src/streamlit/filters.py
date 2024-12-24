import streamlit as st
import pandas as pd

def get_filter_style():
    return """
        <style>
            .streamlit-expanderHeader {
                font-size: 0.9em !important;
                color: white !important;
                background-color: transparent !important;
                border: none !important;
                padding: 4px 12px !important;
                position: fixed !important;
                top: 0.5rem !important;
                left: 4rem !important;
                z-index: 999 !important;
            }
            
            .streamlit-expanderHeader svg {
                font-size: 3em !important;
                vertical-align: middle !important;
            }
            
            .streamlit-expander {
                border: none !important;
                background-color: transparent !important;
            }
            
            .block-container {
                padding-top: 3rem !important;
            }
        </style>
    """

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
        "Date Range",
        options=["Single Year", "Custom Range"],
        horizontal=True
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
    return st.selectbox(
        "Climbing Type",
        options=['All', 'Boulder', 'Aid', 'Sport', 'Trad'],
        format_func=lambda x: {
            'All': 'All Types',
            'Boulder': 'Boulder',
            'Aid': 'Aid',
            'Sport': 'Sport',
            'Trad': 'Trad'
        }.get(x, x),
        key='climbing_type_filter'
    )

def render_filters(df=None, filters_to_include=None, filter_title="Filters"):
    """
    Render filter expander with specified filters
    
    Args:
        df: DataFrame containing the data
        filters_to_include: List of filter names to include
                          Options: ['grade', 'type', 'length', 'date']
    """
    st.markdown(get_filter_style(), unsafe_allow_html=True)
    
    if filters_to_include is None:
        filters_to_include = ['grade', 'type', 'length', 'date']
    
    filter_functions = {
        'commitment_grade': commitment_grade_filter,
        'grade_grain': grade_grain_filter,
        'type': type_filter,
        'length': length_filter,
        'date': date_filter,
        'route_type': route_type_filter
    }
    
    results = {}
    with st.expander(filter_title):
        for filter_name in filters_to_include:
            if filter_name in filter_functions:
                result = filter_functions[filter_name](df)
                if filter_name == 'date':
                    results['year_start'], results['year_end'] = result
                else:
                    results[filter_name] = result
    
    return results