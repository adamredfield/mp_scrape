import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from dash import html, dcc, dash_table
import plotly.express as px
from src.analysis.analysis_queries import *
from src.visualization.components.filters import create_grade_grouping_filter

def apply_chart_style(fig, width='50%', height='350px', vertical_align='top'):
    """Apply consistent styling to a chart"""
    return html.Div([
        dcc.Graph(figure=fig)
    ], style={
        'width': width,
        'display': 'inline-block',
        'verticalAlign': vertical_align,
        'height': height,
    })

def create_charts_section(data):
    tick_fig = px.pie(data['tick_data'], values='Count', names='Type', title='Tick Type Distribution')
    areas_fig = px.bar(data['areas_data'], x='Location', y='Visits', color='Avg_Rating', title='Top 10 Most Visited Areas')
    type_fig = px.bar(data['type_data'], x='Type', y='Count', color='Avg_Rating', title='Route Type Preferences')

    return html.Div([
        html.Div([
            apply_chart_style(tick_fig),
            html.Div([
                create_grade_grouping_filter(),
                dcc.Graph(id='grade-distribution', style={'height': '350px'})], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'})
        ], style={'marginBottom': '20px' }),
        html.Div([
            #apply_chart_style(None, id='areas-chart'),
            html.Div([dcc.Graph(id='areas-chart', style={'height': '350px'})], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'}),
            apply_chart_style(type_fig)
        ])
    ])

def create_table_section(data):
    return html.Div([
        html.H2('Highest Rated Climbs', style={'textAlign': 'center', 'padding': '20px'}),
        dash_table.DataTable(
            id='highest-rated-climbs-table',
            data=data['rated_data'].to_dict('records'),
            columns=[{'name': i, 'id': i} for i in data['rated_data'].columns],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px', 'whiteSpace': 'normal', 'height': 'auto'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}]
        )
    ])