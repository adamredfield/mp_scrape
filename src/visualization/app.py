import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from dash import Dash, html, dcc, dash_table
from dash.dependencies import Input, Output 
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.database.utils import create_connection
from src.analysis.analysis_queries import *

def load_data():
    """Load all data from database"""
    conn = create_connection()
    cursor = conn.cursor()
    
    data = {
        'tick_data': pd.DataFrame(
            get_tick_type_distribution(cursor),
            columns=['Type', 'Count', 'Percentage']
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

# Layout
app.layout = html.Div([
    # Header
    html.H1('🧗‍♂️ Climbing Analytics Dashboard', 
            style={'textAlign': 'center', 'padding': '20px'}),
    
    # First row of graphs
    html.Div([
        # Left side - Tick Types
        html.Div([
            dcc.Graph(figure=tick_fig)
        ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        
        # Right side - Grade Distribution with Controls
        html.Div([
            html.Div([
                html.Label('Route Types:', 
                         style={'fontWeight': 'bold', 'marginBottom': '10px'}),
                dcc.Dropdown(
                    id='route-type-selector',
                    options=[
                        {'label': 'Trad', 'value': 'Trad'},
                        {'label': 'Sport', 'value': 'Sport'},
                        {'label': 'Aid', 'value': 'Aid'},
                        {'label': 'Boulder', 'value': 'Boulder'}
                    ],
                    value=['Trad', 'Sport'],
                    multi=True,
                    placeholder="Select route type(s)",
                    style={'marginBottom': '15px'}
                ),
                html.Label('Grade Grouping:', 
                         style={'fontWeight': 'bold', 'marginBottom': '10px'}),
                dcc.RadioItems(
                    id='grade-grouping-level',
                    options=[
                        {'label': 'Basic (5.10)', 'value': 'base'},
                        {'label': 'Detailed (5.10-, 5.10+)', 'value': 'granular'},
                        {'label': 'Original', 'value': 'original'}
                    ],
                    value='base',
                    style={'marginBottom': '15px'}
                )
            ], style={'padding': '10px', 'backgroundColor': '#f8f9fa', 'borderRadius': '5px'}),
            dcc.Graph(
                id='grade-distribution',
                style={'height': '350px'}
                )
        ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ], style={'marginBottom': '20px'}),
    
    # Second row of graphs
    html.Div([
        # Left side - Areas
        html.Div([
            dcc.Graph(figure=areas_fig)
        ], style={'width': '50%', 'display': 'inline-block'}),
        
        # Right side - Route Types
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
], style={'padding': '20px', 'backgroundColor': 'white'})

# Add callback for grade distribution
@app.callback(
    Output('grade-distribution', 'figure'),
    [Input('route-type-selector', 'value'),
     Input('grade-grouping-level', 'value')]
)
def update_grade_distribution(selected_types, level):
    conn = create_connection()
    cursor = conn.cursor()
    
    # Get data using our new parameterized query
    results = get_grade_distribution(cursor, selected_types, level)
    df = pd.DataFrame(results, columns=['Grade', 'Count', 'Percentage'])
    
    fig = px.bar(df,
                 x='Grade',
                 y='Percentage',
                 title=f'Grade Distribution ({", ".join(selected_types)})',
                 custom_data=['Count'])
    
    fig.update_traces(
        text=df['Count'],  # Show the count
        textposition='auto',  # Position text automatically
        hovertemplate="<br>".join([
            "Grade: %{x}",
            "Percentage: %{y:.1f}%",
            "Count: %{customdata[0]}"
        ])
    )
    
    fig.update_layout(
        xaxis_title="Grade",
        yaxis_title="Percentage of Climbs (%)",
        bargap=0.1,
        margin=dict(t=30, l=50, r=20, b=50),  # Adjusted margins
        height=350,
        title={
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )
    
    conn.close()
    return fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True) 