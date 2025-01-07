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
            color: #F5F5F5;
            font-size: 1.2rem;
        }
        
        .item-details {
            color: #F5F5F5;
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
            color: #F5F5F5;
        }
        </style>
    """

def get_navigation_style():
    return """
        <style>
        /* Reset default spacing */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
        }
        /* Navigation container */
        .st-emotion-cache-eczf16 {
            background-color: #121212 !important;  /* Spotify's dark background */
        }

        /* Navigation text */
        .st-emotion-cache-eczf16 [data-testid="stVerticalBlock"] {
            color: #F5F5F5 !important;  /* Spotify's inactive text color */
        }

        /* Navigation links */
        .st-emotion-cache-eczf16 a {
            color: #FFFFFF !important;  /* Spotify's active text color */
        }

        /* Active/hover state */
        .st-emotion-cache-eczf16 [data-testid="stVerticalBlock"]:hover {
            color: #FFFFFF !important;
            background-color: #282828 !important;  /* Spotify's hover color */
        }

        /* Selected page */
        .st-emotion-cache-eczf16 [aria-selected="true"] {
            color: #1DB954 !important;  /* Spotify's green */
            background-color: #282828 !important;
        }
        </style>
    """
