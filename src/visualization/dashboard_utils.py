from src.database.utils import create_connection
from src.analysis.analysis_queries import get_distinct_styles
from dash import html, dcc

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
        id='route-type-selector',
        options=[type for type in route_types],
        value=['Trad', 'Sport'],
        multi=True,
            placeholder="Select route type(s)",
            style={'marginBottom': '15px', 'width': width}
        )
    ], style={'padding': '20px'})
