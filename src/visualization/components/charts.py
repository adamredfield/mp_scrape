import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from dash import html, dcc, dash_table
import plotly.express as px
from src.analysis.analysis_queries import *
from src.visualization.components.filters import create_grade_grouping_filter

def apply_chart_style(id=None, fig=None, width='50%', height='350px', vertical_align='top'):
    """Apply consistent styling to a chart"""
    graph_style = {'height': height}
    container_style = {
        'width': width,
        'display': 'inline-block',
        'verticalAlign': vertical_align
    }
    if fig:      
        return html.Div([
            dcc.Graph(figure=fig, style=graph_style)
        ], style=container_style)
    else:
        return html.Div([
            dcc.Graph(id=id, style=graph_style)
        ], style=container_style)

def create_charts_section(data):
    type_fig = px.bar(data['type_data'], x='Type', y='Count', color='Avg_Rating', title='Route Type Preferences')

    return html.Div([
        html.Div([
            html.Div([dcc.Graph(id='tick-distribution', style={'height': '350px'})], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'}),
            # apply_chart_style(tick_fig),
            html.Div([
                create_grade_grouping_filter(),
                dcc.Graph(id='grade-distribution', style={'height': '350px'})], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'})
        ], style={'marginBottom': '20px' }),
        html.Div([
            apply_chart_style(id='areas-chart'),
            #html.Div([dcc.Graph(id='areas-chart', style={'height': '350px'})], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'}),
            apply_chart_style(id='type-chart', fig=type_fig),
            #html.Div([dcc.Graph(id='length-climbed-chart', style={'height': '350px'})], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'})
            apply_chart_style(id='length-climbed-chart')
        ],style={'marginBottom': '50px'})
    ])

def create_table_section(data, table_type='rated'):

    if table_type == 'rated':
        title = 'Highest Rated Climbs'
        table_id = 'highest-rated-climbs-table'
        table_data = data['rated_data']
    if table_type == 'bigwall':
        title = 'Big Wall Climbs'
        table_id = 'bigwall-climbs-table'
        table_data = data['bigwall_data']

    return html.Div([
        html.Div([
            html.H2(title, style={'textAlign': 'center', 'padding': '20px','marginTop': '20px','marginBottom': '10px'})
        ], style={'marginBottom': '10px'}),
        dash_table.DataTable(
            id=table_id,
            data=table_data.to_dict('records'),
            columns=[{'name': i, 'id': i} for i in table_data.columns],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px', 'whiteSpace': 'normal', 'height': 'auto'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}]
        )
    ])