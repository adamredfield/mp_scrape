import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import src.analysis.mp_racked_metrics as metrics
import streamlit as st
from src.streamlit.streamlit_helper_functions import image_to_base64, get_squared_image
from src.streamlit.styles import wrapped_template


def page_biggest_day(user_id, conn):
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