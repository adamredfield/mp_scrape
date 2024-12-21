import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.streamlit.streamlit_helper_functions import get_user_id
from styles import get_all_styles, wrapped_template, diamond_template, get_wrapped_styles, get_diamond_styles, get_routes_styles, get_spotify_style
import streamlit as st
import src.analysis.mp_racked_metrics as metrics
import pandas as pd
import plotly.graph_objects as go
from PIL import Image
import requests
from io import BytesIO
import base64
from src.database import queries
from src.streamlit.chart_utils import create_bar_chart
# Page config
st.set_page_config(
    page_title="Your 2024 Climbing Racked",
    page_icon="🧗‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

conn = st.connection('postgresql', type='sql')

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 0

def page_total_length(user_id):
    """First page showing total length climbed"""
    length_data = metrics.get_length_climbed(conn, year='2024', user_id=user_id)
    length_df = pd.DataFrame(length_data, columns=['Year', 'Location', 'Length'])
    total_length = length_df['Length'].sum()

    el_caps = total_length / 3000  # El Cap height in feet
    # Only show decimal if not a whole number
    el_caps_str = f"{el_caps:.1f}" if el_caps % 1 != 0 else f"{int(el_caps)}"
    
    formatted_length = f"{int(total_length):,}"
    
    main_text = f"You climbed<br>{formatted_length}<br>feet this year"
    subtitle = f"That's like climbing {el_caps_str} El Caps! 🏔️"
    st.markdown(wrapped_template(main_text, subtitle), unsafe_allow_html=True)

def page_biggest_day(user_id):
    """Biggest climbing day page"""
    try:
        biggest_day = metrics.biggest_climbing_day(conn, user_id=user_id)
        
        if not biggest_day:
            st.error("No climbing data found for 2024")
            return
            
        date = biggest_day[0]
        routes = biggest_day[1]
        total_length = int(biggest_day[2])
        areas = biggest_day[3].rstrip(" & ")
        route_urls = biggest_day[4].split(" | ")
        photo_urls = biggest_day[5].split(" | ")

        formatted_date = date.strftime('%b %d')
        day = date.day
        if day in [1, 21, 31]:
            suffix = 'st'
        elif day in [2, 22]:
            suffix = 'nd'
        elif day in [3, 23]:
            suffix = 'rd'
        else:
            suffix = 'th'
        
        # Adjust sizes based on number of routes
        route_list = routes.split(" | ")
        num_routes = len(route_list)
        
        # Dynamic sizing
        if num_routes <= 1:
            img_size = "150px"
            margin = "0.5rem"
            font_size = "0.9rem"
            detail_size = "0.8rem"
        elif num_routes <= 3:
            img_size = "100px"
            margin = "0.35rem"
            font_size = "0.85rem"
            detail_size = "0.75rem"
        elif num_routes <= 5:
            img_size = "75px"
            margin = "0.35rem"
            font_size = "0.85rem"
            detail_size = "0.75rem"
        else:
            img_size = "50px"
            margin = "0.25rem"
            font_size = "0.8rem"
            detail_size = "0.7rem"
        
        formatted_routes = []
        for route, url, photo in zip(route_list, route_urls, photo_urls):
            route_parts = route.split(" ~ ")
            route_name = route_parts[0]
            route_details = route_parts[1] if len(route_parts) > 1 else ""
            
            formatted_routes.append(
                f'<div style="display: flex; align-items: center; gap: 0.5rem; margin: {margin} 0;">'
                f'<div style="flex: 1;">'
                f'<a href="{url}" target="_blank" style="color: white; text-decoration: none; font-size: {font_size};">{route_name}</a>'
                f'<div style="color: #888; font-size: {detail_size}; line-height: 1.2;">{route_details}</div>'
                f'</div>'
                f'<img src="{image_to_base64(get_squared_image(photo))}" style="width: {img_size}; height: {img_size}; object-fit: cover;"></div>'
            )
        
        formatted_routes_html = "".join(formatted_routes)
        
        main_text = f"Your biggest climbing day<br>was {formatted_date}{suffix} with<br>{total_length:,d} feet of GNAR GNAR"
        st.markdown(
            wrapped_template(
                main_text=main_text,
                subtitle=f"You Climbed these rigs in {areas}",
                detail_text=formatted_routes_html,
                main_font_size="2.5rem",
                subtitle_font_size="1.5rem",
                route_font_size="0.9rem"
            ),
            unsafe_allow_html=True
        )
        
    except Exception as e:
        st.error(f"Error: {str(e)}")

def image_to_base64(pil_image):
    buffered = BytesIO()
    pil_image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_str}"

def page_total_routes(user_id):
    """Second page showing total routes"""
    total_routes = metrics.total_routes(conn, user_id=user_id)
    
    main_text = f"You climbed {total_routes:,} routes<br>this year"
    subtitle = "And one route again, and again, and again..."
    st.markdown(diamond_template(main_text, subtitle), unsafe_allow_html=True)

def page_most_climbed(user_id):
    """Page showing most repeated route"""
    route_data = metrics.most_climbed_route(conn, user_id=user_id)
    
    if route_data:
        route_name = route_data[0]
        notes = route_data[1]
        first_date = route_data[2]
        times_climbed = route_data[3]

        formatted_date = first_date.strftime('%b %d')
        day = first_date.day

        if day in [1, 21, 31]:
            suffix = 'st'
        elif day in [2, 22]:
            suffix = 'nd'
        elif day in [3, 23]:
            suffix = 'rd'
        else:
            suffix = 'th'

        note_list = notes.split(" | ") if notes else []
        note_list.reverse()
        
        formatted_notes = ""
        if note_list:
            formatted_notes = "Let's relive some memories:<br><br>"
            formatted_notes += "<br>".join([
                f'<div style="max-width: 1000px;">Ascent #{i+1}: "{note.strip()}"</div>'
                for i, note in enumerate(note_list)
                if note.strip()
            ])
        
        main_text = f"Your most climbed route was<br>{route_name}"
        subtitle = f"You climbed it {times_climbed} times"
        detail_text = f"starting on {formatted_date}{suffix}<br><br>{formatted_notes}"
        
        st.markdown(diamond_template(main_text, subtitle, detail_text), unsafe_allow_html=True)
def get_squared_image(url):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        
        # Get the largest dimension
        max_dim = max(img.width, img.height)
        
        # Create a square black background of the largest dimension
        square_img = Image.new('RGB', (max_dim, max_dim), (0, 0, 0))
        
        # Calculate position to paste (center)
        paste_x = (max_dim - img.width) // 2
        paste_y = (max_dim - img.height) // 2
        
        # Paste original onto square background
        square_img.paste(img, (paste_x, paste_y))
        return square_img
        
    except Exception as e:
        print(f"Error loading image from {url}: {e}")
        return None

def page_top_routes(user_id):
    """Page showing top rated routes and tags"""
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    filter_col1, filter_col2, _ = st.columns([1, 1, 2])
    
    with filter_col1:
        tag_type = st.selectbox(
            "Route Characteristics",
            options=['style', 'feature', 'descriptor', 'rock_type'],
            format_func=lambda x: x.replace('_', ' ').title(),
            key='tag_type_filter'
        )
    
    # Get tag data for filter options
    tag_data = metrics.top_tags(conn, tag_type, user_id=user_id)
    tag_df = pd.DataFrame(tag_data, columns=['Type', 'Tag', 'Count']).head(10)
    
    # Calculate max_count from the actual Count column
    max_count = tag_df['Count'].max() if not tag_df.empty else 1
    
    with filter_col2:
        selected_styles = st.multiselect(
            f"Filter by {tag_type.replace('_', ' ').title()}",
            options=tag_df['Tag'].tolist(),
            key='style_filter'
        )
        
    # Get filtered routes based on selected styles
    top_rated_routes = metrics.get_highest_rated_climbs(
        conn,
        selected_styles=selected_styles,
        route_types=None,  # route_types
        year='2024', # year
        tag_type=tag_type,
        user_id=user_id
    ).values.tolist()

    # Create a centered layout with two columns
    left_col, right_col = st.columns(2)
    
    st.markdown("""
        <style>
        .route-container {
            margin-bottom: 20px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Top Routes Column
    with left_col:
        st.markdown("<h2 class='spotify-header'>Your Top Routes</h2>", unsafe_allow_html=True)
        for i, (route, grade, stars, route_id, tags, photo_url, route_url) in enumerate(top_rated_routes[:10], 1):
            with st.container():
                cols = st.columns([1, 10])
                with cols[0]:
                    if photo_url:
                        img = get_squared_image(photo_url)
                        st.image(
                            img, # Fixed width for thumbnail
                            output_format="JPEG"  # Better for photos
                        )
            with cols[1]:
                st.markdown(
                    f"""
                    <div class='list-item'>
                        <div>
                            <span class='item-number'>{i}. </span>
                            <span class='item-name'>
                                <a href="{route_url}" target="_blank" style="color: inherit; text-decoration: none; border-bottom: 1px dotted #888;">
                                    {route}
                                </a>
                            </span>
                        </div>
                        <div class='item-details'>⭐ {stars:.1f} stars &bull; {grade}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    
    # Top Tags Column
    with right_col:
        st.markdown(f"<h2 class='spotify-header'>Top {tag_type.replace('_', ' ').title()}s</h2>", unsafe_allow_html=True)
        
        counts = tag_df['Count'].fillna(0)
        max_count = counts.max() if len(counts) > 0 else 1

        for i, (_, tag, count) in enumerate(zip(tag_df['Type'], tag_df['Tag'], counts), 1):
            # Calculate number of bars based on proportion of max count
            num_bars = min(10, round((count / max_count) * 10)) if max_count > 0 else 0
            frequency_bars = '|' * num_bars
            
            st.markdown(
                f"""
                <div class='list-item'>
                    <div>
                        <span class='item-number'>{i}. </span>
                        <span class='item-name'>{tag}</span>
                    </div>
                    <div class='item-details'>
                        <span style="color: #1ed760;">{frequency_bars}</span> {int(count)} routes
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

def page_areas_breakdown(user_id):
    """Page showing top states and areas"""
    states = metrics.states_climbed(conn, user_id=user_id)
    sub_areas = metrics.sub_areas_climbed(conn, user_id=user_id)
    total_states = metrics.regions_climbed(conn, user_id=user_id)
    total_areas = metrics.regions_sub_areas(conn, user_id=user_id)
    
    # Apply Spotify styling
    st.markdown(get_spotify_style(), unsafe_allow_html=True)
    
    # Create a centered layout with three columns for the top sections
    left_spacer, col1, middle_spacer, col2, right_spacer = st.columns([0.5, 2, 0.5, 2, 1.5])
    
    # States column
    with col1:
        st.markdown("<h2 class='spotify-header'>Top States</h2>", unsafe_allow_html=True)
        for i, (state, days, routes) in enumerate(states[:5], 1):
            st.markdown(
                f"""
                <div class='list-item'>
                    <div>
                        <span class='item-number'>{i}. </span>
                        <span class='item-name'>{state}</span>
                    </div>
                    <div class='item-details'>{days} days • {routes} routes</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        st.markdown(
            f"""
            <div class='total-section'>
                <div class='total-label'>Total States</div>
                <div class='total-value'>{total_states}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Areas column
    with col2:
        st.markdown("<h2 class='spotify-header'>Top Areas</h2>", unsafe_allow_html=True)
        for i, (area, days, routes) in enumerate(sub_areas[:5], 1):
            st.markdown(
                f"""
                <div class='list-item'>
                    <div>
                        <span class='item-number'>{i}. </span>
                        <span class='item-name'>{area}</span>
                    </div>
                    <div class='item-details'>{days} days • {routes} routes</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        st.markdown(
            f"""
            <div class='total-section'>
                <div class='total-label'>Total Areas</div>
                <div class='total-value'>{total_areas}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    
    # Add spacing before the chart section
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    
    # Add filter for the length chart
    filter_col1, filter_col2, _ = st.columns([1, 1, 2])
    
    with filter_col1:
        area_type = st.selectbox(
            "Group Length By",
            options=['region', 'main_area'],
            format_func=lambda x: x.replace('_', ' ').title(),
            key='length_filter_type'
        )
    
    # Get length data based on selected filter
    length_data = metrics.get_length_climbed(conn, area_type=area_type, year='2024', user_id=user_id)
    length_df = pd.DataFrame(length_data, columns=['Year', 'Location', 'Length'])
    
    # Create horizontal bar chart
    fig = go.Figure(data=[
        go.Bar(
            y=length_df['Location'],
            x=length_df['Length'],
            orientation='h',
            marker_color='#1ed760',  # Spotify green
        )
    ])
    
    # Update layout with dark theme
    fig.update_layout(
        paper_bgcolor='black',
        plot_bgcolor='black',
        title={
            'text': f'Length Climbed by {area_type.replace("_", " ").title()}',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'color': 'white', 'size': 20}
        },
        xaxis_title="Distance Climbed (Feet)",
        yaxis_title=area_type.replace("_", " ").title(),
        margin=dict(l=20, r=20, t=50, b=20),
        height=400,
        xaxis=dict(
            color='white',
            gridcolor='#333333',
            showgrid=True
        ),
        yaxis=dict(
            color='white',
            gridcolor='#333333',
            showgrid=False,
            categoryorder='total ascending'  # Sort by length climbed
        ),
        font=dict(
            color='white'
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

def page_grade_distribution(user_id):
    """Page showing grade distribution and most common grade"""
    # Add filter above the chart
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])
    
    with filter_col1:
        grade_level = st.selectbox(
            "Grade Detail Level",
            options=['base', 'granular', 'original'],
            format_func=lambda x: x.title(),
            key='grade_level_filter'
        )
    
    # Get the data based on selected grade level
    grade_dist = metrics.get_grade_distribution(conn, route_types=None, level=grade_level, year='2024', user_id=user_id)
    top_grade = metrics.top_grade(conn,level=grade_level, user_id=user_id)
    
    # Apply Spotify styling
    st.markdown(get_spotify_style(), unsafe_allow_html=True)
    
    # Create a centered layout
    left_spacer, content, right_spacer = st.columns([0.5, 2, 0.5])
    
    with content:
        st.markdown("<h2 class='spotify-header'>Your Grades</h2>", unsafe_allow_html=True)
        
        # Display top grade
        st.markdown(
            f"""
            <div class='total-section'>
                <div class='total-label'>Most Common Grade</div>
                <div class='total-value'>{top_grade}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Create DataFrame for plotting
        df = pd.DataFrame(grade_dist)
        
        # Create bar chart using Graph Objects with dark theme
        fig = go.Figure(data=[
            go.Bar(
                x=df['Grade'],
                y=df['Percentage'],
                marker_color='#1ed760'  # Spotify green
            )
        ])
        
        # Update layout with dark theme
        fig.update_layout(
            paper_bgcolor='black',
            plot_bgcolor='black',
            title={
                'text': 'Grade Distribution',
                'y': 0.9,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'color': 'white', 'size': 20}
            },
            xaxis_title="Grade",
            yaxis_title="Percentage of Climbs (%)",
            bargap=0.1,
            margin=dict(t=50, l=50, r=20, b=50),
            height=400,
            xaxis=dict(
                type='category',
                categoryorder='array',
                categoryarray=df['Grade'],
                color='white',
                gridcolor='#333333'
            ),
            yaxis=dict(
                color='white',
                gridcolor='#333333'
            ),
            font=dict(
                color='white'
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)

def page_bigwall_routes(user_id):
    """Page showing bigwall routes climbed"""
    try:
        df = metrics.get_bigwall_routes(conn, user_id=user_id)
        
        if df.empty:
            st.error("No big wall routes found for 2024")
            return
            
        # Apply Spotify styling
        st.markdown(get_spotify_style(), unsafe_allow_html=True)
        

        # Create header and filter section
        st.markdown("<h2 class='spotify-header'>Wall Rat Stats</h2>", unsafe_allow_html=True)
        st.markdown("""
            <style>
            .route-container {
                margin: 0 !important;
                padding: 0 !important;
            }
            .stImage {
                margin: 0 !important;
                padding: 0 !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        filter_col1, filter_col2, _ = st.columns([1, 1, 2])
        with filter_col1:
            available_grades = sorted([g for g in df['commitment_grade'].unique() if pd.notna(g)])
            selected_grades = st.multiselect(
                'Filter by Commitment Grade:',
                options=available_grades,
                key='commitment_grade_filter'
            )
            
        with filter_col2:
            min_length = 500
            max_length = int(df['length'].max())
            length_filter = st.slider(
                'Minimum Route Length (ft):',
                min_value=min_length,
                max_value=max_length,
                value=min_length,
                step=100,
                key='length_filter'
            )

        filtered_df = df
        if selected_grades:
            filtered_df = filtered_df[filtered_df['commitment_grade'].isin(selected_grades)]
        filtered_df = filtered_df[filtered_df['length'] >= length_filter]
        # Minimal spacing
        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

        # Stats right after filters
        stats_col1, stats_col2, spacer = st.columns([0.5, 1.5, 3])
        with stats_col1:
            st.markdown(
                f"""
                <div class='total-section' style='margin-left: -20px;'>  
                    <div class='total-label'>Total Big Walls</div>
                    <div class='total-value'>{len(filtered_df)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with stats_col2:
            st.markdown(
                f"""
                <div class='total-section' style='margin-left: -40px;'>
                    <div class='total-label'>Total Length</div>
                    <div class='total-value'>{filtered_df['length'].sum():,} ft</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Minimal spacing before routes list
        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        
        # Display routes
        for i, (_, route) in enumerate(filtered_df.iterrows(), 1):
                    with st.container():
                        # More compact columns - adjust the ratio as needed
                        cols = st.columns([0.4, 3])
                        
                        # Photo column
                        with cols[0]:
                            if pd.notna(route.primary_photo_url):
                                img = get_squared_image(route.primary_photo_url)
                                if img:
                                    st.image(img, output_format="JPEG")
                        
                        # Details column - moved closer to image
                        with cols[1]:
                            st.markdown(
                                f"""
                                <div class='list-item' style='margin-left: 65px; padding: 0; display: flex; flex-direction: column; justify-content: center; min-height: 60px; transform: translateY(45px);'>  
                                    <div style='margin-bottom: 4px;'>
                                        <span class='item-number' style='vertical-align: middle;'>{i}. </span>
                                        <span class='item-name' style='vertical-align: middle;'>{route.route_name}</span>
                                    </div>
                                    <div class='item-details' style='margin: 0; line-height: 1.4;'>
                                        {route.grade} {route.commitment_grade or ''} • {route.length:,} ft • {route.area}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                    
        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

        # Create color gradients - multiple shades of Spotify green
        def generate_color_gradient(n):
            base_color = '#1ed760'  # Spotify green
            # Create n different shades by adjusting lightness
            colors = []
            for i in range(n):
                # Adjust the multiplier to control color difference
                factor = 0.5 + (i * 0.5 / n)  # This will give variations from 50% to 100% brightness
                hex_color = f'#{int(int(base_color[1:3], 16) * factor):02x}'
                hex_color += f'{int(int(base_color[3:5], 16) * factor):02x}'
                hex_color += f'{int(int(base_color[5:7], 16) * factor):02x}'
                colors.append(hex_color)
            return colors

        # Create horizontal bar chart with stacked routes
        fig = go.Figure()

        # Group by area but keep individual routes
        for area in filtered_df['main_area'].unique():
            area_routes = filtered_df[filtered_df['main_area'] == area]
            colors = generate_color_gradient(len(area_routes))
            
            for route, color in zip(area_routes.itertuples(), colors):
                fig.add_trace(go.Bar(
                    y=[area],                    # Area name
                    x=[route.length],            # Route length
                    orientation='h',
                    name='',                     # No legend entries
                    showlegend=False,
                    marker_color=color,          # Different shade for each route
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>" +
                        "Grade: %{customdata[1]}<br>" +
                        "Length: %{x:,} ft<br>" +
                        "<extra></extra>"
                    ),
                    customdata=[[route.route_name, route.grade]]
                ))

        # Update layout with dark theme
        fig.update_layout(
            paper_bgcolor='black',
            plot_bgcolor='black',
            title={
                'text': 'Big Wall Lengths by Area',
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top',
                'font': {'color': 'white', 'size': 20}
            },
            xaxis_title="Total Length (Feet)",
            margin=dict(l=20, r=20, t=50, b=20),
            height=400,
            xaxis=dict(
                color='white',
                gridcolor='#333333',
                showgrid=True
            ),
            yaxis=dict(
                color='white',
                gridcolor='#333333',
                showgrid=False,
                categoryorder='total ascending'
            ),
            font=dict(
                color='white'
            ),
            barmode='stack'
        )

        st.plotly_chart(fig, use_container_width=True)
            
    except Exception as e:
        st.error(f"Error: {str(e)}")

def page_first_ascents(user_id):

    # Initialize session states
    if 'fa_view_type' not in st.session_state:
        st.session_state.fa_view_type = "All FAs"
    if 'selected_fa' not in st.session_state:
        st.session_state.selected_fa = None

    # Get data for selectors
    top_fas = metrics.get_top_first_ascensionists(conn, user_id=user_id)
    partnerships = metrics.get_collaborative_ascensionists(conn, "All FAs", user_id)

    st.markdown("""
        <style>
            /* Base styles */
            .block-container {
                padding-top: 1rem;
                padding-bottom: 0rem;
                max-width: 100%;
            }
            
            .stDataFrame {
                margin-bottom: 5rem !important;  /* Extra space after dataframe */
            }
            
            /* Mobile-friendly header */
            .spotify-header {
                font-size: 1.5rem;
                text-align: center;
                margin: 0;
                padding: 0;
                line-height: 1.2;
            }
            
            /* Radio button container */
            div.stRadio > div {
                flex-direction: column;
                gap: 0.2rem;
                padding: 0;
                margin: 0;
                position: relative;  
            }
            
            /* Selectbox positioning */
            div.stSelectbox {
                position: absolute !important;  
                left: 130px !important;        
                top: -93px !important;          
                width: 225px !important;       
            }
            
            /* Hide selectbox label */
            div.stSelectbox label {
                display: none;
            }

            /* Spacing between charts */
            .element-container:has(.js-plotly-plot) {
                margin-bottom: 1rem !important;  /* Increased space between charts */
            }
            
            /* Remove margin from last chart */
            .element-container:has(.js-plotly-plot):last-of-type {
                margin-bottom: 0 !important;
            }
            
            /* Adjust chart title spacing */
            .js-plotly-plot .plotly .gtitle {
                margin-top: 0.5rem !important;
            }   
            .list-item {
                padding: 0.5rem 0;
                display: flex;
                justify-content: space-between; 
                align-items: center;
                max-width: 65%; 
                margin: 0 auto; 
                gap: 1rem; 
            }
            .item-name {
                color: white;
            }
        
            .item-details {
                color: white;
                          margin-right: 2rem;  /* Add right margin to move text left */
            }
            .list-item:hover {
                opacity: 0.8;  /* Subtle hover effect */
            }
        
        /* Style for the routes list */
        .stExpander {
            border: none !important;
            background-color: transparent !important;
        }
        
        .route-item {
            padding: 0.2rem 1rem;
            color: #888;
                font-size: 0.9em;
            }
         </style>
            
    """, unsafe_allow_html=True)

    # Header
    st.markdown("<h2 class='spotify-header'>Your Top FAs</h2>", unsafe_allow_html=True)

    # Create a container for controls
    controls = st.container()

    # Create columns with a very narrow middle column
    left, middle, right = controls.columns([1, 0.1, 1])

    # Radio buttons in left column
    with left:
        view_type = st.radio(
            "",
            ["All FAs", "Individual FA", "FA Team"],
            horizontal=False,
            key="view_type_radio",
            label_visibility="collapsed"
        )

    # Empty middle column for spacing
    with middle:
        st.write("")

    # Selector in right column
    with right:
        if view_type == "Individual FA":
            selected_value = st.selectbox(
                "",
                options=[fa[0] for fa in top_fas],
                key="fa_individual",
                label_visibility="collapsed"
            )
            if 'selected_fa' not in st.session_state or selected_value != st.session_state.selected_fa:
                st.session_state.selected_fa = selected_value
                st.rerun()
        elif view_type == "FA Team":
            selected_value = st.selectbox(
                "",
                options=[p[0] for p in partnerships],
                key="fa_partnership",
                label_visibility="collapsed"
            )
            if 'selected_fa' not in st.session_state or selected_value != st.session_state.selected_fa:
                st.session_state.selected_fa = selected_value
                st.rerun()
        else:
            st.session_state.selected_fa = "All FAs"
   
        # Get data based on selection
        current_selection = st.session_state.selected_fa or "All FAs"
    
    # Fetch data for visualizations
    decades = metrics.get_first_ascensionist_by_decade(conn, current_selection, user_id)
    areas = metrics.get_first_ascensionist_areas(conn, current_selection, user_id)
    grades = metrics.get_first_ascensionist_grades(conn, current_selection, user_id)

    # Only get partners for individual FA view
    if view_type == "Individual FA":
        partners = metrics.get_collaborative_ascensionists(conn, current_selection, user_id)
        
    if view_type == "All FAs":
        # Decades chart
        create_bar_chart(
            title="FAs by Decade", 
            x_data=[decade[0] for decade in decades], 
            y_data=[decade[1] for decade in decades],
            orientation='v',
        )

        # Most prolific First Ascensionists
        st.markdown("<h3 style='text-align: center;'>Most Prolific FAs</h3>", unsafe_allow_html=True)
        for fa, count in top_fas:
            st.markdown(
                f"""
                <div class='list-item'>
                    <span class='item-name'>{fa}</span>
                    <span class='item-details'>{count} routes</span>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        # Layout for Individual FA and Partnership views
        
        # Decades chart
        create_bar_chart(
            title="FAs by Decade", 
            x_data=[decade[0] for decade in decades], 
            y_data=[decade[1] for decade in decades],
            orientation='v',
        )
        
        # Top Areas
        create_bar_chart(
            title="Areas Developed by FA", 
            x_data=[area[0] for area in areas], 
            y_data=[area[1] for area in areas],
            orientation='h',
        )
        
        # Grade Distribution
        create_bar_chart(
            title="FAs by Grade", 
            x_data=[grade[0] for grade in grades], 
            y_data=[grade[1] for grade in grades],
            orientation='v',
        )
        
        # Show Frequent Partners only for Individual FA view
        if view_type == "Individual FA":
            st.markdown("<h3 style='text-align: center;'>Frequent Partners</h3>", unsafe_allow_html=True)
            st.markdown("<div class='list-container'>", unsafe_allow_html=True)
            partners = metrics.get_collaborative_ascensionists(conn, current_selection, user_id)
            for partner, count in partners:
                st.markdown(
                    f"""
                    <div class='list-item'>
                        <span class='item-name'>{partner}</span>
                        <span class='item-details'>{count} routes</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            st.markdown("</div>", unsafe_allow_html=True)

def main():
    
    user_id = get_user_id(conn)
    if not user_id:
        return

    if 'page' not in st.session_state:
        st.session_state.page = 0

    # Page mapping
    pages = {
        8: lambda: page_total_length(user_id),
        1: lambda: page_biggest_day(user_id),
        2: lambda: page_total_routes(user_id),
        3: lambda: page_most_climbed(user_id),
        4: lambda: page_top_routes(user_id),
        5: lambda: page_areas_breakdown(user_id),
        6: lambda: page_grade_distribution(user_id),
        7: lambda: page_bigwall_routes(user_id),
        0: lambda: page_first_ascents(user_id)
    }

    # Apply styles based on current page
    current_page = st.session_state.page
    if current_page in [0, 1]:  # Total length and biggest day pages
        st.markdown(get_wrapped_styles(), unsafe_allow_html=True)
    elif current_page in [2, 3]:  # Total routes and most climbed pages
        st.markdown(get_diamond_styles(), unsafe_allow_html=True)
    elif current_page in [4, 5, 6]:  # Top routes, areas, and grades pages
        st.markdown(get_routes_styles(), unsafe_allow_html=True)
    else:
        st.markdown(get_all_styles(), unsafe_allow_html=True)

    # Display current page
    if current_page in pages:
        pages[current_page]()
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 18, 1])
    
    with col1:
        if st.session_state.page > 0:
            if st.button("← Prev"):
                st.session_state.page -= 1
                st.rerun()
    
    with col3:
        if st.session_state.page < len(pages) - 1:
            if st.button("Next →"):
                st.session_state.page += 1
                st.rerun()

if __name__ == "__main__":
    main() 

