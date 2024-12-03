import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from src.scraping import helper_functions
from src.database.utils import create_connection
from src.database import queries
import re
from datetime import datetime

connection = create_connection()
cursor = connection.cursor()

with sync_playwright() as playwright:
    browser, context = helper_functions.login_and_save_session(playwright)
    # create page once. Each loop will use same page rather than new tab.
    page = context.new_page()

    # how many pages in user's ticks to paginate through
    total_pages = helper_functions.get_total_pages()

    for tick_page in range(1,total_pages + 1):
        print(f'Scraping page: {tick_page}')
        ticks_url_page = f'{helper_functions.ticks_url}{tick_page}'
        print(ticks_url_page)

        tick_response = requests.get(ticks_url_page)
        if tick_response.status_code != 200:
            print(f"Failed to retrieve data: {tick_response.status_code}")

        tick_soup = BeautifulSoup(tick_response.text, 'html.parser')
        tick_table = tick_soup.find('table', class_='table route-table hidden-xs-down')
        tick_rows = tick_table.find_all('tr', class_='route-row')

        # Table has two type of rows. One type holds route data and the other has tick details
        for row in tick_rows:
            tick_details = row.find('td', class_='text-warm small pt-0')
            
            if not tick_details:
                cells = row.find_all('td')
                route_name = ' '.join(cells[0].text.strip().replace('●', '').split())
                print(f'Retrieving data for {route_name}')
                route_link = row.find('a', href=True)['href']
                route_id = route_link.split('/route/')[1].split('/')[0]
                route_exists = queries.check_route_exists(cursor, route_id)
                if route_exists:
                    print(f"Route {route_name} already exists in the database.")
                    current_route_data = {
                    'route_id': route_id,
                    'route_name': route_name
                }
                else:
                    route_html_content = helper_functions.fetch_dynamic_page_content(page, route_link)
                    route_soup = BeautifulSoup(route_html_content, 'html.parser')
                    # Use route_soup to obtain specific route data
                    route_attributes = helper_functions.get_route_attributes(route_soup)
                    route_location = helper_functions.parse_location(route_attributes.get('formatted_location'))
                    route_sections = helper_functions.get_route_sections(route_soup)
                    route_details = helper_functions.get_route_details(route_soup)
                    comments = helper_functions.get_comments(route_soup)

                    current_route_data = {
                        'route_id': route_id,
                        'route_name': route_name,
                        'route_url': route_link,
                        'yds_rating': route_attributes.get('yds_rating'),  
                        'hueco_rating': route_attributes.get('hueco_rating'),
                        'aid_rating': route_attributes.get('aid_rating'),
                        'danger_rating': route_attributes.get('danger_rating'),
                        'avg_stars': route_attributes.get('avg_stars'),
                        'num_votes': route_attributes.get('num_ratings'),
                        'region': route_location.get('region'),
                        'main_area': route_location.get('main_area'),
                        'sub_area': route_location.get('sub_area'),
                        'specific_location': route_location.get('specific_location'),
                        'route_type': route_details.get('route_type'),
                        'length_ft': route_details.get('length_ft'),
                        'pitches': route_details.get('pitches'),
                        'commitment_grade': route_details.get('commitment_grade'),
                        'fa': route_details.get('fa'),
                        'description': route_sections.get('description'),
                        'protection': route_sections.get('protection'),
                        'insert_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }

                    comments_dict = [{'route_id': route_id, 'comment': comment, 'insert_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')} for comment in comments]

                    queries.insert_route(cursor, connection, current_route_data)
                    queries.insert_comments(cursor, connection, comments_dict)

                    current_route_data = {
                        'route_id': route_id,
                        'route_name': route_name
                    }
            
            # Check if tick details row rather than a route row. 
            if tick_details and current_route_data:
                # Append the additional info to the previous row's data
                tick_details_text = tick_details.text.strip()

                date_pattern = r'[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}'
                date_match = re.search(date_pattern, tick_details_text)
                tick_date = date_match.group() if date_match else None

                tick_type = None
                tick_note = None

                valid_tick_types = [
                    'Solo', 'TR', 'Follow', 'Lead',
                    'Lead / Onsight', 'Lead / Flash',
                    'Lead / Redpoint', 'Lead / Pinkpoint',
                    'Lead / Fell/Hung'
                ]

                if ' · ' in tick_details_text:
                    post_date_text = tick_details_text.split(' · ')[1]  # Get everything after the bullet, following date
                    if '.' in post_date_text:
                        parts = post_date_text.split('.', 1)
                        if "pitches" in parts[0].lower():
                            next_parts = parts[1].split('.', 1)
                            potential_type = next_parts[0].strip()
                            if potential_type in valid_tick_types:
                                tick_type = potential_type
                                tick_note = next_parts[1].strip() if len(next_parts) > 1 else None
                            else:
                                tick_note = parts[1].strip()
                        else:
                            potential_type = parts[0].strip()
                            if potential_type in valid_tick_types:
                                tick_type = potential_type
                                tick_note = parts[1].strip() if len(parts) > 1 else None
                            else:
                                tick_note = parts[1].strip()
                    else:
                        tick_note = post_date_text.strip()
                        
                tick_data = {
                    'user': helper_functions.user,
                    'route_id': current_route_data['route_id'],
                    'date': tick_date,
                    'type': tick_type,
                    'note': tick_note,
                    'insert_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                queries.insert_tick(cursor, connection, tick_data)
                current_route_data = None

    browser.close()
    connection.close()
    
    