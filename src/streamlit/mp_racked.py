import streamlit as st
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(
    page_title="Your 2024 Climbing Racked",
    page_icon="🧗‍♂️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)
from src.streamlit.streamlit_helper_functions import get_user_id, get_device_dimensions, is_mobile, is_iphone_dimensions
from src.streamlit.styles import get_navigation_style

st.markdown("""
    <style>
    /* Hide JS eval iframes but keep messages visible */
    [class*="st-key-mobile_check"],
    [class*="st-key-device_dims"] {
        position: absolute !important;
        z-index: -1 !important;  /* Push iframes behind other content */
    }
""", unsafe_allow_html=True)

st.markdown('<div style="padding-top: 1rem;"></div>', unsafe_allow_html=True)

dims_container = st.empty()
error_container = st.empty()
button_container = st.empty()
info_container = st.empty()

dims = get_device_dimensions('initial') or {}
is_mobile_device = is_mobile()
is_iphone_dims = is_iphone_dimensions()

if not (is_mobile_device or is_iphone_dims):
    dimensions_text = "Unable to detect screen dimensions"
    if dims:
        width = dims.get('screenWidth', 'unknown')
        height = dims.get('screenHeight', 'unknown')
        dimensions_text = f"Current screen dimensions: {width}x{height}"
    with error_container:
        st.error(f"""
            This app requires either:
            1. A mobile device, or
            2. A browser window set to mobile dimensions
            
            Current screen dimensions: {dims.get('screenWidth')}x{dims.get('screenHeight')}
            Device pixel ratio: {dims.get('devicePixelRatio')}
            
            Common iPhone dimensions:
            - iPhone 12/13/14 Pro: 390x844
            - iPhone 15 Pro: 393x852
            - iPhone Pro Max: 428x926
            - iPhone 15 Pro Max: 430x932
        """)
    with button_container:
        if st.button("Reload page"):
            streamlit_js_eval(js_expressions="parent.window.location.reload()")
    
    with info_container:
        st.info("""
            To view on desktop:
            1. Right-click and select 'Inspect'
            2. Click the device toggle button (📱) or press Ctrl+Shift+M
            3. Select an iPhone from the device dropdown
            4. Click the refresh button above
        """)
        st.stop()

st.markdown(get_navigation_style(), unsafe_allow_html=True)

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if st.session_state['authenticated']:
    with st.sidebar:
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

conn = st.connection('postgresql', type='sql')

if not st.session_state['authenticated']:
    def empty_page():
        pass
    pg = st.navigation([st.Page(empty_page, title="Mountain Project Racked")], position="hidden")
    pg.run()

    user_id = get_user_id(conn)
    if user_id:
        st.session_state['user_id'] = user_id
        st.session_state['conn'] = conn
        st.session_state['authenticated'] = True
        st.rerun()

    st.stop()


pg = st.navigation({
    "Base Camp": [ 
        st.Page("pages/landing_page.py", 
                title= "Base Camp", 
                icon="⛺", 
                default=True)],
    "Performance Dashboard": [
        st.Page("pages/thousand_meter_view.py", 
                title= "Thousand Meter View", 
                icon="🦅"),
        st.Page("pages/grade_pyramid.py", 
                title="Grade Pyramid of Giza", 
                icon="📊"),
        st.Page("pages/wall_rat_stats.py", 
                title="Wall Rat Stats", 
                icon="🐀")
    ],
    "Personal Analytics": [ 
        st.Page("pages/going_the_distance.py", 
                title="Going the Distance", 
                icon="🏃"),
        st.Page("pages/dialing_it_in.py", 
            title="Dialing It In", 
            icon="🎯"),
        st.Page("pages/style_for_miles.py", 
            title="Style for Miles", 
            icon="🕺")
    ],
    "Route Explorer": [ 
        st.Page("pages/classics_chaser.py", 
                title="Classics Collector", 
                icon="⭐"),
        st.Page("pages/route_finder.py", 
                title="Advanced Route Finder", 
                icon="🔍"),        
        st.Page("pages/fa_legacy.py", 
                title="FA Legacy", 
                icon="⚡"),
        ]
    })

try:
    pg.run()
except Exception as e:
    st.error(f"Something went wrong: {str(e)}", icon=":material/error:")
