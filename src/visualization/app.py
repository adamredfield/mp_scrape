import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from dash import Dash, html, dcc, dash_table
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.database.utils import create_connection
from src.database.analysis_queries import *

def load_data():
    """Load all data from database"""
    conn = create_connection()
    cursor = conn.cursor()
    
    data = {
        'tick_data': pd.DataFrame(
            get_tick_type_distribution(cursor),
            columns=['Type', 'Count', 'Percentage']
        ),
        'grade_data': pd.DataFrame(
            get_grade_distribution(cursor),
            columns=['Grade', 'Percentage']
        ),
        'seasonal_data': pd.DataFrame(
            get_seasonal_patterns(cursor),
            columns=['Month', 'Climb_Count', 'Avg_Grade']
        ),
        'areas_data': pd.DataFrame(
            get_most_climbed_areas(cursor),
            columns=['Location', 'Visits', 'Avg_Rating']
        ).head(10),
        'type_data': pd.DataFrame(
            get_route_type_preferences(cursor),
            columns=['Type', 'Count', 'Avg_Rating', 'Percentage']
        ),
        'rated_data': pd.DataFrame(
            get_highest_rated_climbs(cursor),
            columns=['Route', 'Grade', 'Stars', 'Votes']
        ).head(10)
    }
    
    conn.close()
    return data

# Initialize Dash app
app = Dash(__name__)
server = app.server  # needed for production deployment

# Load data
data = load_data()

# Create figures
tick_fig = px.pie(data['tick_data'], 
                  values='Count', 
                  names='Type', 
                  title='Tick Type Distribution')

grade_fig = px.bar(data['grade_data'], 
                   x='Grade', 
                   y='Percentage',
                   title='Grade Distribution')

seasonal_fig = go.Figure()
seasonal_fig.add_trace(go.Bar(
    name='Climbs', 
    x=data['seasonal_data']['Month'], 
    y=data['seasonal_data']['Climb_Count']
))
seasonal_fig.add_trace(go.Scatter(
    name='Avg Grade',
    x=data['seasonal_data']['Month'],
    y=data['seasonal_data']['Avg_Grade'],
    yaxis='y2'
))
seasonal_fig.update_layout(
    title='Seasonal Climbing Patterns',
    yaxis2=dict(overlaying='y', side='right'),
    hovermode='x unified'
)

areas_fig = px.bar(data['areas_data'], 
                   x='Location', 
                   y='Visits',
                   color='Avg_Rating',
                   title='Top 10 Most Visited Areas')

type_fig = px.bar(data['type_data'],
                  x='Type',
                  y='Count',
                  color='Avg_Rating',
                  title='Route Type Preferences')

# App layout
app.layout = html.Div([
    # Header
    html.H1('🧗‍♂️ Climbing Analytics Dashboard', 
            style={'textAlign': 'center', 'padding': '20px'}),
    
    # First row of graphs
    html.Div([
        html.Div([
            dcc.Graph(figure=tick_fig)
        ], style={'width': '50%', 'display': 'inline-block'}),
        html.Div([
            dcc.Graph(figure=grade_fig)
        ], style={'width': '50%', 'display': 'inline-block'})
    ]),
    
    # Seasonal patterns (full width)
    html.Div([
        dcc.Graph(figure=seasonal_fig)
    ]),
    
    # Another row of graphs
    html.Div([
        html.Div([
            dcc.Graph(figure=areas_fig)
        ], style={'width': '50%', 'display': 'inline-block'}),
        html.Div([
            dcc.Graph(figure=type_fig)
        ], style={'width': '50%', 'display': 'inline-block'})
    ]),
    
    # Highest rated climbs table
    html.H2('Highest Rated Climbs', 
            style={'textAlign': 'center', 'padding': '20px'}),
    dash_table.DataTable(
        data=data['rated_data'].to_dict('records'),
        columns=[{'name': i, 'id': i} for i in data['rated_data'].columns],
        style_table={'overflowX': 'auto'},
        style_cell={
            'textAlign': 'left',
            'padding': '10px',
            'whiteSpace': 'normal',
            'height': 'auto',
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': 'rgb(248, 248, 248)'
            }
        ]
    ),
    
    # Footer
    html.Div([
        html.P('Data sourced from Mountain Project',
               style={'textAlign': 'center', 'padding': '20px'})
    ])
], style={'padding': '20px'})

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True) 