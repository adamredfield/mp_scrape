import os
import sys
import streamlit as st
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.streamlit.streamlit_helper_functions import get_squared_image, image_to_base64
import src.analysis.mp_racked_metrics as metrics
from src.streamlit.filters import render_filters
from src.analysis.filters_ctes import available_years
import streamlit.components.v1 as components

user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')




st.markdown("""   
     <style>
        /* Filter spacing from top of page */
        div[data-testid="stExpander"] {
            margin-top: 0rem;
        }

        /* Card spacing from filter */
        div:has(> .style-card) {
            margin-top: 0rem !important;  /* Adjust this value as needed */
        }

        /* Tab spacing from card */
        [data-testid="stTabs"] {
            margin-top: -1rem !important;
        }

        /* Center tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 90px;
            justify-content: center !important;
        }
        
    .stExpander {
        border: none !important;
        padding: 0 !important;
        
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
tag_type = filters.get('tag_type')
selected_styles = filters.get('selected_tags')
route_types = filters.get('route_type')
st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
filter_col1, filter_col2, _ = st.columns([1, 1, 2])

classics_count = metrics.get_classics_count(conn, user_id, start_year, end_year, route_types=route_types, selected_styles=selected_styles, tag_type=tag_type)
date_text = (f"in {start_year}" 
            if start_year == end_year 
            else f"from {start_year} to {end_year}")


st.markdown(f"""
    <div class="style-card">
        <div style="display: flex; justify-content: center; gap: 2rem;">
            <div style="text-align: center;">
                <div class="style-title">{classics_count} Classic Routes Climbed 🏆</div>
                <div class="style-subtitle">{date_text}</div>
                <div style="color: #B3B3B3; font-size: 0.8rem; margin-top: 0.5rem;">
                    Routes with 3.5 stars and 15 votes
                </div>
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

top_rated_routes = metrics.get_highest_rated_climbs(
    conn,
    selected_styles=selected_styles,
    route_types=route_types,
    year_start=start_year,
    year_end=end_year,
    tag_type=tag_type,
    user_id=user_id
).values.tolist()

st.markdown("""
    <style>

        
        /* Style the expander content container */
        .streamlit-expanderContent {
            border: none !important;
            background-color: transparent !important;
        }
        
        /* Dark background for each expander */
        div[data-testid="stExpander"] {
            background: rgba(0, 0, 0, 0.2) !important;å
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
        }

        /* Keeps filters near top of page*/
        .block-container {
            padding-top: 2rem !important;
        }
        
        /* Style card positioning */
        .style-card {
            background: transparent;
            border: 1px solid #1ed760;
            border-radius: 10px;
            padding: 1.5rem;
            margin: -4rem 0 2rem 0;  /* Increased negative top margin */
            text-align: center;
            position: relative;  /* Add position relative */
            z-index: 1;  /* Ensure card stays above other elements
        }
        /* Tab content spacing */
        .stTabs [data-baseweb="tab-list"] {
            margin-bottom: 1rem !important;  /* Uniform spacing after tab list */
        }
        
        /* Tabs positioning */
        [data-testid="stTabs"] {
            margin-top: 0 !important;
            margin-bottom: 0.5rem !important;
        }
        
    </style>
""", unsafe_allow_html=True)

tag_data = metrics.top_tags(
    conn, 
    tag_type, 
    user_id=user_id,
    year_start=start_year,
    year_end=end_year
)
tag_df = pd.DataFrame(tag_data, columns=['Type', 'Tag', 'Count'])

tab1, tab2 = st.tabs(["🏔️ Top Routes", "🏷️ Style Analysis"])

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

with tab1:
    local_css("src/streamlit/styles.css")

    if 'loaded_images' not in st.session_state:
        st.session_state.loaded_images = {}
    
    print("Session state at start:", st.session_state)

    @st.cache_data
    def process_image(photo_url, route_name):
        """Cache the image processing"""
        if photo_url:
            img = image_to_base64(get_squared_image(photo_url))
            return img
        return None

    @st.fragment
    def load_and_display_image(route_id, photo_url, route_name):
        """Fragment for handling image loading and display"""

        container = st.empty()

        if route_id not in st.session_state.loaded_images:
            if container.button("Load Image", key=f"load_{route_id}_{route_name.replace(' ', '_')}"):
                img = process_image(photo_url, route_name)
                if img:
                    st.session_state.loaded_images[route_id] = img
                    container.markdown(
                        f"""
                        <div style="width: 100%;">
                            <img src="{img}" 
                                style="width: 100%; 
                                        object-fit: cover; 
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
                <div style="width: 100%;">
                    <img src="{st.session_state.loaded_images[route_id]}" 
                        style="width: 100%; 
                                object-fit: cover; 
                                margin: 0; 
                                padding: 0;
                                border-radius: 4px;"
                        alt="{route_name}">
                </div>
                """,
                unsafe_allow_html=True
            )

    js_code = """
    <script>
    setTimeout(() => {
        try {
            // First, clean up any existing styles
            const allExpanders = window.parent.document.querySelectorAll('div.stExpander');
            allExpanders.forEach(exp => {
                exp.classList.remove('classic-route', 'regular-route');
            });
            
            // Then apply new styles
            const expanders = Array.from(window.parent.document.querySelectorAll('div.stExpander'));
            console.log('Found expanders:', expanders.length);
    """

    for i, (route_name, main_area, specific_location, grade, stars, route_id, styles, photo_url, route_url) in enumerate(top_rated_routes):
        i +=1


        if stars >= 3.5:  # if it's a classic route
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
            
        # Create the expander title using pure markdown
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
        
        print("-------------------")
    js_code += """
            } catch (err) {
                console.error('Main error:', err);
            }
    }, 1000);  // Single timeout of 1 second
    </script>
    """
    components.html(js_code, height=0, width=0)
    
with tab2:
    st.markdown("""
    <style>
        .tag-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            margin-bottom: 0.3rem;
        }
        
        .tag-name {
            color: #EEEEEE;
            font-size: 1rem;
            min-width: 120px;
        }
        
        .bar-container {
                flex-grow: 1;
                margin: 0;  /* Added margin on both sides */
                padding: 0;
        }
        
        .frequency-bar {
            background: #1ed760;
            height: 4px;
            border-radius: 2px;
        }
        
        .count {
            color: #B3B3B3;
            font-size: 0.9rem;
            min-width: 80px;
            text-align: right;
        }
    </style>
""", unsafe_allow_html=True)
    
    counts = tag_df['Count'].fillna(0)
    max_count = counts.max() if len(counts) > 0 else 1

    for i, (_, tag, count) in enumerate(zip(tag_df['Type'], tag_df['Tag'], counts), 1):
        percentage = (count / max_count) * 100 if max_count > 0 else 0
        
        st.markdown(f"""
            <div class="tag-item">
                <div class="tag-name">{i}. {tag}</div>
                <div class="bar-container">
                    <div class="frequency-bar" style="width: {percentage}%;"></div>
                </div>
                <div class="count">{int(count)} routes</div>
            </div>
        """, unsafe_allow_html=True)