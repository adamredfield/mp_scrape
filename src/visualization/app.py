import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from dash import Dash, html
import plotly.express as px
from src.database.utils import create_connection
from src.analysis.analysis_queries import *
from src.visualization.components.filters import create_filters_section
from src.visualization.components.charts import create_charts_section, create_table_section
from src.visualization.callbacks import register_callbacks
import pandas as pd

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
        ).head(20),
        'type_data': pd.DataFrame(
            get_route_type_preferences(cursor),
            columns=['Type', 'Count', 'Avg_Rating', 'Percentage']
        ),
        'rated_data': pd.DataFrame(
            get_highest_rated_climbs(cursor),
            columns=['Route', 'Grade', 'Stars', 'Votes', 'Styles']
        ).head(20)
    }
    
    conn.close()
    return data

# Initialize Dash app
app = Dash(__name__)
server = app.server 

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
    html.H1('🧗‍♂️ Climbing Analytics Dashboard', style={'textAlign': 'center', 'padding': '20px'}),
    create_filters_section(),
    create_charts_section(data),
    create_table_section(data),
    html.Div([html.P('Data sourced from Mountain Project', style={'textAlign': 'center', 'padding': '20px'})])
], style={'padding': '20px', 'backgroundColor': 'white'})


register_callbacks(app)

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True) 