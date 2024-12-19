import streamlit as st

# Styling
STYLES = {
    'base': """
        footer {visibility: hidden;}
        .stApp { background: black; }
    """,
    
    'container': """
        .wrapped-container {
            position: relative;
            height: 100vh;
            width: 100vw;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: white;
            text-align: center;
            padding: 0;
            margin: 0;
            background: black;
            overflow: hidden;
        }
    """,
    
    'patterns': """
        .top-pattern {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 45vh;
            background: linear-gradient(to bottom right, #FF1CAE, #FF0080);
            clip-path: polygon(
                0 0, 10% 0, 10% 8%, 20% 8%, 20% 16%,
                30% 16%, 30% 24%, 40% 24%, 40% 32%,
                50% 32%, 50% 40%, 60% 40%, 60% 48%,
                70% 48%, 70% 56%, 80% 56%, 80% 64%,
                90% 64%, 90% 72%, 100% 72%, 100% 0
            );
    }
    
        .bottom-pattern {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 45vh;
            background: linear-gradient(to top left, #FF1CAE, #FF0080);
            clip-path: polygon(
                0 28%, 10% 28%, 10% 36%, 20% 36%, 20% 44%,
                30% 44%, 30% 52%, 40% 52%, 40% 60%,
                50% 60%, 50% 68%, 60% 68%, 60% 76%,
                70% 76%, 70% 84%, 80% 84%, 80% 92%,
                90% 92%, 90% 100%, 0 100%
            );
        }
    """,
    
    'text': """ 
        .big-text {
            font-family: 'Helvetica Neue', sans-serif;
            font-size: 4.5rem;
            font-weight: 900;
            line-height: 1.2;
            margin: 0;
            padding: 0;
            text-align: center;
            z-index: 10;
        }
    
        .subtitle-text {
            font-family: 'Helvetica Neue', sans-serif;
            font-size: 2rem;
            font-weight: 400;
            margin-top: 3rem;
            z-index: 10;
        }
    
        .route-list {
            font-family: 'Helvetica Neue', sans-serif;
            font-size: 1.5rem;
            font-weight: 400;
            margin-top: 1.5rem;
            z-index: 10;
        }
    """,
    
    'diamond_patterns': """
        .diamond-pattern {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 25vh;
            background: linear-gradient(to right, #4B0082, #00BFFF);
            clip-path: polygon(
                0 0, 100% 0,              /* Top edge */
                100% 25%, 80% 25%,        /* Right top step */
                60% 25%, 40% 25%,         /* Middle space */
                20% 25%, 0 25%            /* Left top step */
            );
        }
    
        .diamond-pattern-right {
            position: absolute;
            top: 0;
            right: 0;
            width: 20vw;
            height: 40vh;
            background: linear-gradient(to right, #4B0082, #00BFFF);
            clip-path: polygon(
                0 0,                      /* Top left */
                100% 0,                   /* Top right */
                100% 100%,                /* Bottom right */
                0 40%                     /* Bottom point */
            );
        }
        
        .diamond-pattern-left {
            position: absolute;
            top: 0;
            left: 0;
            width: 20vw;
            height: 40vh;
            background: linear-gradient(to right, #4B0082, #00BFFF);
            clip-path: polygon(
                0 0,                      /* Top left */
                100% 0,                   /* Top right */
                100% 40%,                 /* Bottom point */
                0 100%                    /* Bottom left */
            );
        }
        
        .diamond-bottom-right {
            position: absolute;
            bottom: 0;
            right: 0;
            width: 20vw;
            height: 40vh;
            background: linear-gradient(to right, #4B0082, #00BFFF);
            clip-path: polygon(
                0 60%,                    /* Top point */
                100% 0,                   /* Top right */
                100% 100%,                /* Bottom right */
                0 100%                    /* Bottom left */
            );
        }
        
        .diamond-bottom-left {
            position: absolute;
            bottom: 0;
            left: 0;
            width: 20vw;
            height: 40vh;
            background: linear-gradient(to right, #4B0082, #00BFFF);
            clip-path: polygon(
                0 0,                      /* Top left */
                100% 60%,                 /* Top point */
                100% 100%,                /* Bottom right */
                0 100%                    /* Bottom left */
            );
        }
    """,
    
    'routes': """
        .top-routes-container {
            background: #ffff00;
            color: black;
            padding: 2rem;
            min-height: 100vh;
            width: 100vw;
        }
    
        .route-title {
            font-family: 'Helvetica Neue', sans-serif;
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 2rem;
        }
        
        .route-row {
            display: flex;
            align-items: center;
            margin-bottom: 1.5rem;
            gap: 1rem;
        }
        
        .route-number {
            font-size: 2.5rem;
            font-weight: 700;
            min-width: 3rem;
        }
        
        .route-info {
            display: flex;
            flex-direction: column;
        }
        
        .route-name {
            font-size: 1.5rem;
            font-weight: 600;
            margin: 0;
        }
    
        .route-rating {
            font-size: 1.2rem;
            color: #333;
            margin: 0;
        }
    """,

    'misc': """
        .big-number {
            font-size: 3rem;
            font-weight: 700;
            color: black;
        }
        
        .area-container {
            background: transparent;
            padding: 0.5rem;
        }
        
        .area-name {
            font-size: 1.5rem;
            font-weight: 600;
            margin: 0;
            color: black;
        }
        
        .length-count {
            font-size: 1.2rem;
            color: #333;
            margin: 0;
        }
    """
    }

def get_all_styles():
    """Combine all styles into a single string"""
    return "<style>\n" + "\n".join(STYLES.values()) + "\n</style>"

def get_wrapped_styles():
    """Get styles for wrapped pages only"""
    return "<style>\n" + "\n".join([
        STYLES['base'],
        STYLES['container'],
        STYLES['patterns'],
        STYLES['text']
    ]) + "\n</style>"

def get_diamond_styles():
    """Get styles for diamond pages only"""
    return "<style>\n" + "\n".join([
        STYLES['base'],
        STYLES['container'],
        STYLES['diamond_patterns'],
        STYLES['text']
    ]) + "\n</style>"

def get_routes_styles():
    """Get styles for routes pages only"""
    return "<style>\n" + "\n".join([
        STYLES['base'],
        STYLES['routes'],
        STYLES['misc']
    ]) + "\n</style>"

def wrapped_template(main_text, subtitle=None, detail_text=None, main_font_size="4rem", subtitle_font_size="2rem", route_font_size="0.9rem"):
    return f"""
        <div class="wrapped-container">
            <div class="top-pattern"></div>
            <div class="bottom-pattern"></div>
            <div class="big-text" style="font-size: {main_font_size};">{main_text}</div>
            {f'<div class="subtitle-text" style="font-size: {subtitle_font_size};">{subtitle}</div>' if subtitle else ''}
            {f'<div class="route-container">{detail_text}</div>' if detail_text else ''}
        </div>
    """

def diamond_template(main_text, subtitle=None, detail_text=None):
    """Diamond pattern template for total routes page"""
    return f"""
        <div class="wrapped-container">
            <div class="diamond-pattern-left"></div>
            <div class="diamond-pattern-right"></div>
            <div class="diamond-bottom-left"></div>
            <div class="diamond-bottom-right"></div>
            <div class="big-text">{main_text}</div>
            {f'<div class="subtitle-text">{subtitle}</div>' if subtitle else ''}
            {f'<div class="route-list">{detail_text}</div>' if detail_text else ''}
        </div>
    """

def get_spotify_style():
    return """
        <style>
        .stApp {
            background-color: black !important;
        }
        
        .content-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .spotify-header {
            color: #1ed760;
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            text-align: center;
        }
        
        .list-item {
            margin: 0.25rem 0;
            text-align: left;
            padding-left: 40%;
        }
        
        .item-number {
            color: #1ed760;
            font-size: 1.2rem;
        }
        
        .item-name {
            color: white;
            font-size: 1.2rem;
        }
        
        .item-details {
            color: #b3b3b3;
            font-size: 0.9rem;
            margin-top: -0.2rem;
        }
        
        .total-section {
            margin-top: 2rem;
            text-align: center;
        }
        
        .total-label {
            color: #1ed760;
            font-size: 1.2rem;
            margin-bottom: 0.5rem;
        }
        
        .total-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: white;
        }
        </style>
    """