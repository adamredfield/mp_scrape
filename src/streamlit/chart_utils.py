import plotly.graph_objects as go
import streamlit as st

def create_bar_chart(
    x_data, 
    y_data, 
    title, 
    orientation='v'
):
    """
    Create a mobile-friendly bar chart with consistent formatting
    """
    # Mobile-optimized constants
    CHART_HEIGHT = 250
    BAR_WIDTH = 0.1
    BAR_GAP = 0.2
    MARGIN = dict(l=30, r=20, t=30, b=40)
    
    # Create figure with swapped coordinates for horizontal orientation
    fig = go.Figure(data=[
        go.Bar(
            x=y_data if orientation == 'h' else x_data,
            y=x_data if orientation == 'h' else y_data,
            orientation=orientation,
            marker_color='#1ed760',
            width=BAR_WIDTH
        )
    ])
    
    # Common axis settings
    axis_settings = dict(
        color='white',
        showgrid=True,
        gridcolor='#333333',
        tickfont=dict(size=10)
    )
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=14)
        ),
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white'),
        height=CHART_HEIGHT,
        margin=MARGIN,
        bargap=BAR_GAP,
        showlegend=False,
        xaxis=dict(
            **axis_settings,
            type='category' if orientation == 'v' else None,
            range=[0, max(y_data) * 1.1] if orientation == 'h' else None
        ),
        yaxis=dict(
            **axis_settings,
            type='category' if orientation == 'h' else None,
            range=[0, max(y_data) * 1.1] if orientation == 'v' else None
        )
    )
    
    # Display the chart with mobile-friendly settings
    return st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            'scrollZoom': False,
            'displayModeBar': False,
            'staticPlot': True,
            'responsive': True
        }
    )