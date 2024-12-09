import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)
from dash import html, dcc
from src.database.utils import create_connection
from src.analysis.analysis_queries import *
from src.visualization.dashboard_utils import get_style_filter, get_route_type_filter

def get_style_filter(width='50%'):
    """
    Creates a reusable style filter dropdown component
    Args:
        width (str): CSS width of the dropdown (default: '50%')
    Returns:
        html.Div component with the style filter
    """
    conn = create_connection()
    cursor = conn.cursor()
    style_options = get_distinct_styles(cursor)
    conn.close()

    return html.Div([
        html.Label('Filter by Style:', 
                 style={'fontWeight': 'bold', 'marginBottom': '10px'}),
        dcc.Dropdown(
            id='style-filter',
            options=[{'label': style, 'value': style} for style in style_options],
            multi=True,
            placeholder="Select climbing style(s)",
            style={'marginBottom': '15px', 'width': width}
        )
    ], style={'padding': '20px'}) 

def get_route_type_filter(width='50%'):

    route_types = ['Trad', 'Sport', 'Aid', 'Boulder']

    return html.Div([
        html.Label('Filter by Route Type:', 
                 style={'fontWeight': 'bold', 'marginBottom': '10px'}),
        dcc.Dropdown(
        id='route-type-filter',
        options=[type for type in route_types],
        value=['Trad', 'Sport'],
        multi=True,
            placeholder="Select route type(s)",
            style={'marginBottom': '15px', 'width': width}
        )
    ], style={'padding': '20px'})

def create_grade_grouping_filter():
    """Creates the grade grouping radio button filter"""
    return html.Div([
        html.Label('Grade Grouping Level:', 
                 style={'fontWeight': 'bold', 'marginBottom': '10px'}),
        dcc.RadioItems(
            id='grade-grouping-level',
            options=[
                {'label': 'Basic (5.10)', 'value': 'base'},
                {'label': 'Detailed (5.10-, 5.10+)', 'value': 'granular'},
                {'label': 'Original', 'value': 'original'}
            ],
            value='base',
            style={'display': 'flex', 'gap': '20px'}
        )
    ], style={'marginBottom': '10px'})

def create_filters_section():
    return html.Div([
        html.Div([
            get_route_type_filter(width='200px'),  # Fixed width instead of percentage
            get_style_filter(width='200px')
        ], style={
            'display': 'flex',
            'gap': '20px',
            'justifyContent': 'flex-start',
            'marginBottom': '20px'
        })
    ])