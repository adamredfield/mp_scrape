import os
import sys
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_float import *
import streamlit.components.v1 as components

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.streamlit.streamlit_helper_functions import get_squared_image, image_to_base64
import src.analysis.mp_racked_metrics as metrics
from src.streamlit.filters import render_filters
from src.analysis.filters_ctes import available_years
from src.streamlit.styles import get_spotify_style

st.markdown("""
    <style>
        /* Add bottom padding to tab panels to prevent cutoff */
        .stTabs [data-baseweb="tab-panel"] {
            padding-top: 0 !important;
            padding-bottom: 10rem !important;
        }
        .st-emotion-cache-ule1sg {
            margin-top: -.25rem !important;
        }
    </style>
""", unsafe_allow_html=True)


@st.cache_data
def process_image(photo_url, route_name):
    """Cache the image processing"""
    if photo_url:
        squared_img = get_squared_image(photo_url)
        img = image_to_base64(squared_img)
        return img
    return None

@st.fragment
def load_and_display_image(route_id, photo_url, route_name):
    container = st.empty()

    if route_id not in st.session_state.loaded_images:
        if container.button("Load Image", key=f"load_{route_id}_{route_name.replace(' ', '_')}"):
            img = process_image(photo_url, route_name)
            if img:
                st.session_state.loaded_images[route_id] = img
            container.markdown(
                f"""
                <div style="width: 300px; height: 300px; background: black;">
                    <img src="{img}" 
                        style="width: 100%;
                                height: 100%;
                                object-fit: contain; 
                                margin: 0; 
                                padding: 0;
                                border-radius: 4px;"
                        alt="{route_name}">
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        container.markdown(
            f"""
            <div style="width: 100%; aspect-ratio: 1;">
                <img src="{st.session_state.loaded_images[route_id]}" 
                    style="width: 100%; 
                            height: 100%;
                            object-fit: cover; 
                            margin: 0; 
                            padding: 0;
                            border-radius: 4px;"
                    alt="{route_name}">
            </div>
            """,
            unsafe_allow_html=True
        )
def display_routes(routes_data, highlight_route_ids=None):
    js_code = """
        <script>
        setTimeout(() => {
            try {
                const allExpanders = window.parent.document.querySelectorAll('div[data-testid="stExpander"]');
                allExpanders.forEach(exp => {
                    exp.style.backgroundColor = 'rgb(14, 17, 23)';
                });
                // Then apply new styles
                const expanders = Array.from(allExpanders);
                console.log('Found expanders:', expanders.length);
        """

    for i, (route_name, main_area, specific_location, grade, stars, route_id, styles, photo_url, route_url) in enumerate(classic_climbs):
        i +=1

        if highlight_route_ids and route_id in highlight_route_ids:
            js_code += f"""
                try {{
                    const element = expanders[{i}];
                    if (element) {{
                        element.classList.add("classic-route");
                        console.log("Added classic-route to index {i}, ID: {route_id}");
                    }}
                }} catch (err) {{
                    console.error("Error with classic route at index {i}, ID: {route_id}", err);
                }}
            """
        else:
            js_code += f"""
                try {{
                    const element = expanders[{i}];
                    if (element) {{
                        element.classList.add("regular-route");
                        console.log("Added regular-route to index {i}, ID: {route_id}");
                    }}
                }} catch (err) {{
                    console.error("Error with regular route at index {i}, ID: {route_id}", err);
                }}
            """

        if specific_location:
            location_parts = specific_location.split(' > ')
            if len(location_parts) >= 2:
                shortened_location = ' > '.join(location_parts[-2:])
            else:
                shortened_location = location_parts[0]
        else:
            shortened_location = ''
            
        expander_title = rf"""**{route_name}** - {main_area} :green[{grade}]""".strip()

        with st.expander(expander_title, expanded=False):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if photo_url:
                    load_and_display_image(route_id, photo_url, route_name)
        
            
            with col2:
                st.markdown("### Route Details")
                st.markdown(f"""
                    - **Location:** {shortened_location}
                    - **Type:** {styles}
                    
                    [:green[View on Mountain Project ↗]]({route_url})
                """)
        
    js_code += """
            } catch (err) {
                console.error('Main error:', err);
            }
    }, 1000);  // Single timeout of 1 second
    </script>
    """
    components.html(js_code, height=0, width=0)

st.markdown(get_spotify_style(), unsafe_allow_html=True)

user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')

st.markdown("""   
     <style>
        /* Center tabs */
        .stTabs [data-baseweb="tab-list"] {
            justify-content: center !important;
        }
        .stTabs.st-emotion-cache-0.e10uku090 {
            margin-top: -1rem !important; 
            position: relative;
            z-index: 2;
        }       
    </style>
""", unsafe_allow_html=True)      

years_df = available_years(conn, user_id)

if 'filter_expander_state' not in st.session_state:
    st.session_state.filter_expander_state = False 

filters = render_filters(
    df=years_df,
    filters_to_include=['date', 'route_tag', 'route_type'],
    filter_title="Choose your filters",
    conn=conn,
    user_id=user_id 
)

start_year = filters.get('year_start')
end_year = filters.get('year_end')
tag_selections = filters.get('tag_selections', {})
route_types = filters.get('route_type')

classic_climbs = metrics.get_classic_climbs(
    conn,
    tag_selections=tag_selections,
    route_types=route_types,
    year_start=start_year,
    year_end=end_year,
    user_id=user_id
).values.tolist()

st.markdown("""
    <style>
        /* Style card positioning */
        .style-card {
            border: 1px solid #1ed760;
            border-radius: 10px;
            padding: 1.5rem;
            margin: 1.5rem 0 2rem 0;  /* Increased negative top margin */
            text-align: center;
            position: relative;  /* Add position relative */
            z-index: 1;  /* Ensure card stays above other elements
        }  
    </style>
""", unsafe_allow_html=True)


tab1, tab2 = st.tabs(["🏔️ Top Routes", "📚 Fifty Classics"])

with tab1:


    classics_count = metrics.get_classics_count(conn, user_id, start_year, end_year, route_types=route_types, tag_selections=tag_selections)
    date_text = (f"in {start_year}" 
                if start_year == end_year 
                else f"from {start_year} to {end_year}")

    st.markdown(f"""
        <div class="style-card">
            <div style="display: flex; justify-content: center; gap: 2rem;">
                <div style="text-align: center;">
                    <div class="style-title">{classics_count} Classic Routes Climbed 🏆</div>
                    <div class="style-subtitle">{date_text}</div>
                    <div style="color: #F5F5F5; font-size: 0.8rem; margin-top: 0.5rem;">
                        Routes with 3.5 stars and 15 votes<br>
                    </div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    def local_css(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    local_css("src/streamlit/styles.css")

    if 'loaded_images' not in st.session_state:
        st.session_state.loaded_images = {}

    display_routes(classic_climbs)


with tab2:
    def create_radial_gauge(value, max_value=50):

        percentage = (value / max_value) * 100
        
        fig = go.Figure(go.Indicator(
            mode="gauge", 
            value=value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "50 Classic Climbs of North America", 'font': {'color': 'white', 'size': 18}},
            gauge={
                'axis': {
                    'range': [None, 50], 
                    'tickwidth': 1, 
                    'tickcolor': "#1ed760",
                    'tickfont': {'color': '#F5F5F5'}
                },
                'bar': {'color': "#1ed760"},
                'bgcolor': "rgba(0,0,0,0)",
                'borderwidth': 2,
                'bordercolor': "#1ed760",
                'steps': [
                    {'range': [0, value], 'color': '#1ed760'},
                    {'range': [value, 50], 'color': 'rgba(30, 215, 96, 0.2)'}
                ]
            }
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "#FFFFFF", 'family': "Arial"},
            height=150, 
            margin=dict(l=30, r=30, t=50, b=20)
        )
        
        fig.add_annotation(
            text=f"{value}/50 • {int(percentage)}%",
            xref="paper",
            yref="paper",
            x=0.5,
            y=-0,
            showarrow=False,
            font=dict(size=18, color='white'),
            yshift=0
        )
        
        return fig
    
    fifty_classics = metrics.get_fifty_classics_details(conn, user_id)
    total_climbed = fifty_classics['climbed'].sum()
    total_classics = 50

    st.markdown("""
        <style> 
            .js-plotly-plot {
                margin-top: 0rem !important;
                margin-bottom: 0rem !important;
            }
            
            /* Ensure no extra padding at top of container */
            .block-container {
                padding-top: 0 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    fig = create_radial_gauge(total_climbed)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Display routes
    for _, route in fifty_classics.iterrows():
        expander_title = (
            f"{'✅ ' if route['climbed'] else ''}"
            f"**{route['route_name']}** - {route['main_area']} "
            f":green[{route['grade']}]"
        )
        
        with st.expander(expander_title, expanded=False):
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if route['primary_photo_url']:
                    load_and_display_image(route['id'], route['primary_photo_url'], route['route_name'])
            
            with col2:
                st.markdown("### Route Details")
                st.markdown(f"""
                    - **Location:** {route['specific_location']}
                    - **Type:** {route['route_type']}
                    - **Length:** {int(route['length_ft']) if pd.notna(route['length_ft']) else 'N/A'} ft
                    - **Pitches:** {int(route['pitches']) if pd.notna(route['pitches']) else 'N/A'}
                    - **Rating:** {'⭐' * int(route['avg_stars']) if pd.notna(route['avg_stars']) else 'N/A'}
                    - **Style:** {route['styles'] if pd.notna(route['styles']) else 'N/A'}  
                    - **Features:** {route['features'] if pd.notna(route['features']) else 'N/A'}  
                    - **Rock Type:** {route['rock_type'] if pd.notna(route['rock_type']) else 'N/A'}
                    
                    [:green[View on Mountain Project ↗]]({route['route_url']})
                """)
                
                if route['climbed']:
                    st.markdown(f"""
                        ---
                        **Climbed on:** {route['tick_date'].strftime('%B %d, %Y')}  
                        **Style:** {route['tick_style']}
                        
                        **Notes:** {route['tick_notes'] if pd.notna(route['tick_notes']) else 'No notes'}
                    """)