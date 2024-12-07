from dash.dependencies import Input, Output
import pandas as pd
from src.database.utils import create_connection
import src.analysis.analysis_queries as analysis_queries
from src.visualization.components.filters import create_filters_section
import plotly.express as px
import plotly.graph_objects as go


def register_callbacks(app, data):
    @app.callback(
        Output('grade-distribution', 'figure'), 
        [Input('route-type-filter', 'value'), Input('grade-grouping-level', 'value')]
    )
    def update_grade_distribution(selected_types, level):
        conn = create_connection()
        cursor = conn.cursor()

        results = analysis_queries.get_grade_distribution(cursor, selected_types, level)
        df = pd.DataFrame(results, columns=['Grade', 'Count', 'Percentage'])


        fig = px.bar(df,
                     x='Grade',
                     y='Percentage',
                     title=f'Grade Distribution ({", ".join(selected_types)})',
                     custom_data=['Count'])

        fig.update_traces(
            text=df['Count'],
            textposition='auto',
            hovertemplate="<br>".join([
                "Grade: %{x}",
                "Percentage: %{y:.1f}%",
                "Count: %{customdata[0]}"
            ])
        )

        fig.update_layout(xaxis_title="Grade",
                          yaxis_title="Percentage of Climbs (%)",
                          bargap=0.1,
                          margin=dict(t=30, l=50, r=20, b=50),
                          height=350,
                          title={'y': 0.95, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'})
        conn.close()
        return fig
    @app.callback(
        Output('areas-chart', 'figure'), 
        Input('route-type-filter', 'value')
    )
    def update_areas_chart(selected_types):
        conn = create_connection()
        cursor = conn.cursor()

        results = analysis_queries.get_most_climbed_areas(cursor, selected_types)
        areas_df = pd.DataFrame(results, columns=['Location', 'Visits', 'Avg_Rating'])

        fig = px.bar(areas_df, x='Location', y='Visits', color='Avg_Rating',
            title='Top 20 Most Visited Areas')
        
        conn.close()
        return fig
    @app.callback(
        Output('tick-distribution', 'figure'), 
        Input('route-type-filter', 'value')
    )
    def update_tick_type_distribution(selected_types):
        conn = create_connection()
        cursor = conn.cursor()

        results = analysis_queries.get_tick_type_distribution(cursor, selected_types)
        df = pd.DataFrame(results, columns=['Type', 'Count', 'Percentage'])
        
        fig = px.pie(df, 
                 values='Count', 
                 names='Type', 
                 title='Tick Type Distribution')
    
        fig.update_layout(
            margin=dict(t=30, l=50, r=20, b=50),
            height=350,
            title={'y': 0.95, 'x': 0.5, 'xanchor': 'center', 'yanchor': 'top'}
        )

        conn.close()
        return fig

    @app.callback(
        Output('highest-rated-climbs-table', 'data'),
        [Input('style-filter', 'value'), Input('route-type-filter', 'value')]
    )
    def update_rated_climbs_table(selected_styles, selected_types):
        conn = create_connection()
        cursor = conn.cursor()

        results = analysis_queries.get_highest_rated_climbs(cursor, selected_styles, selected_types)
        df = pd.DataFrame(results, columns=['Route', 'Grade', 'Stars', 'Votes', 'Styles'])

        conn.close()
        return df.to_dict('records')
    
    @app.callback(
        Output('length-climbed-chart', 'figure'),
        Input('_', 'children')
    )
    def update_length_climbed_chart(trigger):
        df = data['length_data']

        year_totals = df.groupby('Year')['Length'].sum().reset_index()
        max_length = year_totals['Length'].max()

        fig = px.bar(
            df,
            x='Length',
            y='Year',
            color='Location',
            title='Length Climbed by Year',
            barmode='stack',
            orientation='h',
            custom_data=['Location', 'Length']
        )

        fig.update_layout(
            xaxis_title="Distance Climbed (Feet)",
            yaxis_title="Year",
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis={'categoryorder': 'category ascending'},
            xaxis_range=[0, max_length * 1.1]
        )
        fig.update_traces(
            hovertemplate="<br>".join([
                "Area: %{customdata[0]}",
                "Year: %{y}",
                "Distance: %{x:,d} feet",
                "<extra></extra>"
            ])
        )

        fig.add_trace(
        go.Scatter(
            x=year_totals['Length'] * 1.01,
            y=year_totals['Year'].astype(str),
            text=[f"{int(x):,} ft" for x in year_totals['Length']],
            mode='text',
            textposition='middle right',
            showlegend=False
        )
    )
        return fig