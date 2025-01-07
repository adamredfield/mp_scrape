import plotly.graph_objects as go
import streamlit as st

def create_bar_chart(
    x_data, 
    y_data, 
    title, 
    orientation='v'
):
    CHART_HEIGHT = 250
    BAR_WIDTH = 0.1
    BAR_GAP = 0.2
    MARGIN = dict(l=30, r=20, t=30, b=40)
    
    fig = go.Figure(data=[
        go.Bar(
            x=y_data if orientation == 'h' else x_data,
            y=x_data if orientation == 'h' else y_data,
            orientation=orientation,
            marker_color='#1ed760',
            width=BAR_WIDTH
        )
    ])
    
    axis_settings = dict(
        color='#F5F5F5',
        showgrid=True,
        gridcolor='#333333',
        tickfont=dict(size=10)
    )
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=14)
        ),
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='#F5F5F5'),
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

def create_gradient_bar_chart(df, x_col, y_col, title):
    """
    Creates a horizontal bar chart with color gradients for each group.
    Specifically designed for stacked route length visualization.
    
    Args:
        df: DataFrame containing the data
        x_col: Column name for x-axis values (e.g., 'length')
        y_col: Column name for y-axis groups (e.g., 'main_area')
        title: Chart title
    """
    def generate_color_gradient(n):
        base_color = '#1ed760'  # Spotify green
        colors = []
        for i in range(n):
            factor = 0.5 + (i * 0.5 / n)
            hex_color = f'#{int(int(base_color[1:3], 16) * factor):02x}'
            hex_color += f'{int(int(base_color[3:5], 16) * factor):02x}'
            hex_color += f'{int(int(base_color[5:7], 16) * factor):02x}'
            colors.append(hex_color)
        return colors

    fig = go.Figure()
    
    for area in df[y_col].unique():
        area_data = df[df[y_col] == area]
        colors = generate_color_gradient(len(area_data))
        
        for (_, row), color in zip(area_data.iterrows(), colors):
            fig.add_trace(go.Bar(
                y=[row[y_col]],
                x=[row[x_col]],
                orientation='h',
                name='',
                showlegend=False,
                marker_color=color,
                hovertemplate=(
                    f"<b>{row['route_name']}</b><br>" +
                    f"Grade: {row['grade']}<br>" +
                    f"Length: {row[x_col]:,} ft<br>" +
                    "<extra></extra>"
                )
            ))

    fig.update_layout(
        paper_bgcolor='black',
        plot_bgcolor='black',
        title={
            'text': title,
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'color': '#F5F5F5', 'size': 20}
        },
        xaxis_title="Total Length (Feet)",
        margin=dict(l=20, r=20, t=50, b=20),
        height=400,
        xaxis=dict(
            color='#F5F5F5',
            gridcolor='#333333',
            showgrid=True
        ),
        yaxis=dict(
            color='#F5F5F5',
            gridcolor='#333333',
            showgrid=False,
            categoryorder='total ascending'
        ),
        font=dict(
            color='#F5F5F5'
        ),
        barmode='stack',
        dragmode=False,
        hovermode='closest'
    )
    
    return fig