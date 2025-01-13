from streamlit_cookies_controller import CookieController
import streamlit as st

cookie_controller = CookieController()

if not st.session_state.get('authenticated'):
    st.switch_page("mp_racked.py")

user_id = st.session_state.user_id
conn = st.connection('postgresql', type='sql')

user_name = user_id.split('/')[1]
user_name_formatted = user_name.replace('-', ' ').title()

st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 10rem !important;
        margin-top: 0rem !important;
    }
    
    /* Compact welcome section */
   div[data-testid="stMarkdownContainer"] h1.welcome-title {
        font-size: 2rem;
        line-height: 1.2;
        margin: 0 0 1rem 0;
        padding: 0;
    }
    
    .quick-start {
        line-height: 1.4;
        margin: 0 0 1rem 0;
    }
    
    /* Expander styling */
    div[data-testid="stExpander"] {
        background-color: #0E1117 !important;  /* Match the background color */
        border: 1px solid #1ed760 !important;
        border-radius: 10px !important;
        color: white !important;
        font-size: 2rem !important;
        margin-bottom: 1rem !important;
        
    }
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
    <div style="text-align: center;">
        <h1 style="
            color: white; 
            line-height: 1.2; 
            margin: 0 0 -1.5rem 0; 
            padding: 0;
        ">
            <div style="font-size: 2.5rem; color: #1ed760; margin-bottom: 0.1em;">
                {user_name_formatted}
            </div>
            <div style="font-size: 2.2rem; opacity: 0.95;">
                Welcome to your
            </div>
            <div style="font-size: 2rem;">
                Mountain Project Racked
            </div>
        </h1>
    </div>
    <div style="
        color: rgba(255, 255, 255, 0.85);
        font-size: .9rem;
        line-height: 2;
        margin: 0 0 1.5rem 0;
    ">
        1. Tap arrow in the top left corner to access the menu ⬅️<br>
        2. Explore your climbing stats across different pages 📖<br>
        3. Filter and analyze your climbing history
    </div>
""", unsafe_allow_html=True)


def render_feature_card(emoji, title, description, page_name):
    # Create unique key for the card
    card_key = f"card_{title.lower().replace(' ', '_')}"
    
    # Use columns to create proper layout
    col1, col2, col3 = st.columns([0.1, 0.8, 0.1])
    with col2:
        # Create the card content
        st.markdown(f"""
            <div class="card-wrapper">
                <div class="feature-card">
                    <div class="card-header">
                        <span class="emoji">{emoji}</span>
                        <h2>{title}</h2>
                    </div>
                    <p>{description}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Add the button in the same column
        if st.button("", key=card_key, use_container_width=True):
            cookie_controller.set('current_page', title)
            st.switch_page(f"pages/{page_name.lower().replace(' ', '_')}.py")

# Add CSS to style everything properly
st.markdown("""
    <style>
    .card-wrapper {
        position: relative;
        margin-bottom: -150px;  /* Adjust based on button height */
    }
    
    .feature-card {
        background: black;
        border: 1px solid #1ed760;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
        pointer-events: none;
    }
    
    .card-header {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    .emoji {
        font-size: 1.5rem;
    }
    
    .feature-card h2 {
        color: white;
        font-size: 1.3rem;
        margin: 0;
    }
    
    .feature-card p {
        color: #9e9e9e;
        font-size: 1rem;
        margin: 0;
    }
    
    /* Button styling */
    .stButton button {
        background-color: transparent !important;
        border: none !important;
        height: 150px !important;
        transition: all 0.2s;
        margin-top: -20px !important;  /* Increased negative margin to move button up */
        position: relative !important;
        z-index: 1 !important;  /* Ensure button stays on top */
    }
    
    .stButton button:hover {
        background-color: rgba(30, 215, 96, 0.1) !important;
    }
    
    .stButton button:active {
        transform: scale(0.98);
    }
    </style>
""", unsafe_allow_html=True)


with st.expander("📈 Overview", expanded=False):
    render_feature_card("🦅", "Thousand Meter View", 
                       "Get a bird's eye view of your climbing stats", "thousand_meter_view")
    render_feature_card("📊", "Grade Pyramid of Giza", 
                        "The monkeys are sending.<br>"
                        "Visualize your grade progression pyramid", "grade_pyramid")   
    render_feature_card("🐀", "Wall Rat Stats", 
                        "Go BIG or go home.<br>"
                        "Multipitch & Bigwall Tracker", "wall_rat_stats")   
# Personal Analytics Section
with st.expander("📊 Personal Analytics", expanded=False):
    render_feature_card("🏃", "Going the Distance", 
                       "See how far you've climbed", "going_the_distance")
    render_feature_card("🎯", "Dialing It In", 
                        "What did you climb.<br>"
                        "Again and again and again", "dialing_it_in")  
    render_feature_card("🧗", "Style for Miles", 
                       "Break down your climbing preferences<br>"
                       "Top Styles, Features, Descriptors & Rock Type<br>", "style_for_miles")

# Route Explorer Section
with st.expander("🔍 Route Explorer", expanded=False):
    render_feature_card("⭐", "Classics Collector", 
                       "View your ultra classics<br>"
                       "Track your progress on the 50 classics of NA<br>", "classics_chaser")
    render_feature_card("🔍", "Advanced Route Finder", 
                       "Find your next adventure<br>"
                       "Advanced filtering by FA, style, etc<br>", "route_finder")
    render_feature_card("⚡", "FA Legacy", 
                       "Explore your favorite first ascenionists<br>"
                       "Made by and for the history nerds<br>", "fa_legacy")



