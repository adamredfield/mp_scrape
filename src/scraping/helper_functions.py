import json
import requests
import re
from src.database.utils import create_connection
from src.database import queries
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from datetime import datetime, timezone
import re
import os

mp_home_url = "https://www.mountainproject.com"

base_url = f'{mp_home_url}/user/'
user_id = '200362278/doctor-choss'
constructed_url = f'{base_url}{user_id}'
ticks_url = f'{constructed_url}/ticks?page='

def get_proxy_url():
    """Get IPRoyal proxy URL - returns a string"""
    username = os.getenv('IPROYAL_USERNAME')
    password = os.getenv('IPROYAL_PASSWORD')
    
    proxy_url = f'http://{username}:{password}@geo.iproyal.com:12321'
    print(f"Generated proxy URL: http://{username}:****@geo.iproyal.com:12321")
    
    return proxy_url

def login_and_save_session(playwright):
    """Initialize browser with proxy and login"""
    mp_username = os.getenv('MP_USERNAME')
    mp_password = os.getenv('MP_PASSWORD')
    proxy_username = os.getenv('IPROYAL_USERNAME')
    proxy_password = os.getenv('IPROYAL_PASSWORD')

    print("Starting browser launch sequence...")
    try:
        browser = playwright.chromium.launch(
            headless=True,
            proxy={
                'server': 'http://geo.iproyal.com:12321',
                'username': proxy_username,
                'password': proxy_password
            }
        )
        print("Browser launched successfully")

        context = browser.new_context()
        print("Context created successfully")
    
        page = context.new_page()
        page.set_default_navigation_timeout(60000)
        page.set_default_timeout(30000)
        page.goto(mp_home_url)
        page.wait_for_load_state('networkidle')
        print("Navigation complete")

        page.click("a.sign-in")
        page.wait_for_selector("#login-modal", timeout=5000)
        page.fill("input[type='email'][name='email']", mp_username)
        page.fill("input[type='password'][name='pass']", mp_password)
        page.click("#login-modal button[type='submit']")
        print("Login submitted")

        # Save cookies and storage_state to /tmp
        cookies = context.cookies()
        with open("/tmp/cookies.json", "w") as cookie_file:
            json.dump(cookies, cookie_file)

        storage_state = context.storage_state()
        with open("/tmp/storage.json", "w") as storage_file:
            json.dump(storage_state, storage_file)

        print("Login successful, session saved!")
        return browser, context
    
    except Exception as e:
        print(f"Browser/login failed: {str(e)}")
        if browser:
            browser.close()
        raise

def fetch_dynamic_page_content(page, route_link):
        page.goto(route_link)
        last_height = None

        # loads comments
        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")  # Scroll down
            page.wait_for_timeout(1000)
            new_height = page.evaluate("document.body.scrollHeight")  # Get new scroll height
            if new_height == last_height:  # Stop if no change in scroll height
                break
            last_height = new_height
            
        html_content = page.content()
        return html_content

def get_total_pages():
    proxy_url = get_proxy_url()
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
     # Get total number of rows to paginate through
    pagination_response = requests.get(ticks_url, proxies=proxies)
    if pagination_response.status_code != 200:
        print(f"Failed to retrieve data: {pagination_response.status_code}")

    pagination_soup = BeautifulSoup(pagination_response.text, 'html.parser')
    pagination_div = pagination_soup.find('div', class_='pagination')
    no_click_links = pagination_div.find_all('a', class_='no-click')

    # Loop through the links to find the one containing text (pagination data)
    for link in no_click_links:
        pagination_text = link.get_text(strip=True)

    total_pages = int(pagination_text.split()[-1])

    return total_pages

def get_comments(route_soup):
        comments = []

        comment_elements = route_soup.find_all('div', class_='comment-body')

        for comment in comment_elements:
            # Extract the full comment text from the <span> with id containing '-full'
            comment_text = comment.find('span', id=re.compile(r'.*-full')).get_text(strip=True)
            comments.append(comment_text)
        return comments

def get_route_details(route_soup):
    description_details_tbl = route_soup.find('table', class_='description-details')
    route_details = {
    'route_type': None,
    'length_ft': None,
    'pitches': None,
    'commitment_grade': None,
    'fa': None
}
    desc_rows = description_details_tbl.find_all('tr') 
    for row in desc_rows:
        cells = row.find_all('td')

        label = cells[0].text.strip()
        value = cells[1].text.strip()

        if label == 'Type:':
            parsed_type = parse_route_type(value)
            route_details.update(parsed_type)
        elif label == 'FA:':
            route_details['fa'] = value
    return route_details

def get_route_sections(route_soup):
    # sections we want to extract text for. Can add as more relevant sections are found
    sections = ['description', 'protection']
    route_sections = {}

    # Find the <h2> header matching the section name
    headers = route_soup.find_all('h2', class_='mt-2')
    for header in headers:
        header_text = header.get_text(strip=True).lower()
        for section in sections:
            if section.lower() in header_text:
                section_div = header.find_next_sibling('div', class_='fr-view')
                route_sections[section.lower()] = ' '.join(section_div.get_text(separator=' ').split())
                # break out of loop if match already found and processed
                break
    return route_sections

def get_grade(route_soup):
    grade_types = {
        'yds_rating': None,     # e.g., "5.11d"
        'hueco_rating': None,   # e.g., "V3"
        'aid_rating': None,     # e.g., "A2"
        'danger_rating': None   # e.g., "R"
    }
    danger_list = ['PG', 'PG13', 'R', 'X'] 

    rating_h2 = route_soup.find('h2', class_='inline-block mr-2')
    if rating_h2:
        # Get all YDS spans (could contain both YDS and Hueco)
        rating_spans = rating_h2.find_all('span', class_='rateYDS')
        for span in rating_spans:
            rating = span.text.split()[0]  # Get the rating without "YDS"
            if rating.startswith('5.'):
                grade_types['yds_rating'] = rating
            elif rating.startswith('V'):
                grade_types['hueco_rating'] = rating
        
        danger_text = rating_h2.get_text().strip()
        for word in danger_text.split():
            if (word.startswith('A') or word.startswith('C')) and len(word) > 1 and word[1].isdigit():
                grade_types['aid_rating'] = word
            elif word in danger_list:
                grade_types['danger_rating'] = word
        
    return grade_types
def get_route_attributes(route_soup):

    route_attributes = {}
    grade_types = get_grade(route_soup)
    route_attributes['yds_rating'] = grade_types['yds_rating']
    route_attributes['hueco_rating'] = grade_types['hueco_rating']
    route_attributes['aid_rating'] = grade_types['aid_rating']
    route_attributes['danger_rating'] = grade_types['danger_rating']
    stars_avg_text_element = route_soup.find('span', id=re.compile('^starsWithAvgText-'))
    avg_rating_text = stars_avg_text_element.text.strip().replace('\n', ' ')
    avg_rating_parts = avg_rating_text.split('from')
    route_attributes['avg_stars'] = avg_rating_parts[0].replace('Avg:', '').strip()
    route_attributes['num_ratings'] = int(avg_rating_parts[1].replace('votes', '').replace(',', '').strip() )
    route_attributes['formatted_location'] = ' > '.join(link.text.strip() for link in route_soup.select('.mb-half.small.text-warm a'))
    photo_link = route_soup.find('div', class_='carousel-item')
    route_attributes['primary_photo_url'] = (
        photo_link['style'].split('url("')[1].split('")')[0] if photo_link and 'style' in photo_link.attrs else None
    )

    return route_attributes

def parse_route_type(route_details_string):
    """
    Parse route type string into components:
    - route_type: Trad, Sport, Aid, etc.
    - route_length: in feet/meters
    - pitches: number of pitches
    - commitment_grade: Grade I, II, III, etc.
    """
    if not route_details_string:
        return {
            'route_type': None,
            'route_length': None,
            'pitches': None,
            'commitment_grade': None
        }

    parsed_details = {
        'route_type': None,
        'length_ft': None,
        'pitches': None,
        'commitment_grade': None
    }

    # Split the string by commas
    parts = [p.strip() for p in route_details_string.split(',')]
    valid_types = ['Trad', 'Sport', 'Aid', 'Boulder']
    found_types = []

    # Process parts until we hit a length, pitch, or grade indicator to get type(s)
    for part in parts:
        if not any(indicator in part.lower() for indicator in ['ft', 'pitch', 'grade']):
            if part in valid_types:
                found_types.append(part)
            continue

        # Match route length (e.g., "500 ft (152 m)")
        length_match = re.search(r'(\d+)\s*ft', part)
        if length_match:
            parsed_details['length_ft'] = int(length_match.group(1))  # Store in feet
            continue

        # Match pitches (e.g., "6 pitches" or "6 pitch")
        pitch_match = re.search(r'(\d+)\s*pitch', part)
        if pitch_match:
            parsed_details['pitches'] = int(pitch_match.group(1))
            continue

        # Match commitment grade (e.g., "Grade III")
        grade_match = re.search(r'Grade\s+(VI|IV|V|I{1,3})', part)
        if grade_match:
            parsed_details['commitment_grade'] = grade_match.group(1)
            continue
    
    parsed_details['route_type'] = ', '.join(found_types) if found_types else None

    return parsed_details

def parse_location(location_string):
    """
    Parse location string into components:
    - state
    - main_area (e.g., Joshua Tree NP, Yosemite NP)
    - sub_area (e.g., Yosemite Valley, Hidden Valley Area)
    - specific_location (everything else combined)
    """
    if not location_string:
        return {
            'state': None,
            'main_area': None,
            'sub_area': None,
            'specific_location': None
        }

    # Split by ' > ' and remove 'All Locations'
    parts = [p.strip() for p in location_string.split(' > ')]
    if parts[0] == 'All Locations':
        parts = parts[1:]

    location_data = {
        'region': None,
        'main_area': None,
        'sub_area': None,
        'specific_location': None
    }

    # Always get state (should be first part)
    if len(parts) > 0:
        location_data['region'] = parts[0]

    # Get main area (e.g., Joshua Tree NP, Yosemite NP)
    if len(parts) > 1:
        location_data['main_area'] = parts[1]

    # Get sub area (e.g., Yosemite Valley, Hidden Valley Area)
    if len(parts) > 2:
        location_data['sub_area'] = parts[2]

    # Combine remaining parts for specific location
    if len(parts) > 3:
        location_data['specific_location'] = ' > '.join(parts[3:])

    return location_data

def process_page(page_number, ticks_url, user_id, retry_count=0):
    """Process a single page"""
    proxy_url = get_proxy_url()  # Get string URL
    proxies = {                  # Create dict where needed
        'http': proxy_url,
        'https': proxy_url
    }
    
    print(f"Using proxies config:")
    print(f"HTTP: {proxies['http'].replace(os.getenv('IPROYAL_PASSWORD'), '****')}")
    print(f"HTTPS: {proxies['https'].replace(os.getenv('IPROYAL_PASSWORD'), '****')}")
    
    with create_connection() as conn:
        cursor = conn.cursor()
        
        with sync_playwright() as playwright:
            browser = None
            context = None
            try:
                browser, context = login_and_save_session(playwright)
                page = context.new_page()

                print(f'Processing page: {page_number}. (Retry #{retry_count})')
                
                tick_response = requests.get(ticks_url, proxies=proxies)
                if tick_response.status_code != 200:
                    raise Exception(f"Failed to retrieve data: {tick_response.status_code}")
                
                tick_soup = BeautifulSoup(tick_response.text, 'html.parser')
                tick_table = tick_soup.find('table', class_='table route-table hidden-xs-down')
                tick_rows = tick_table.find_all('tr', class_='route-row')

                for row in tick_rows:
                    try:
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
                                route_html_content = fetch_dynamic_page_content(page, route_link)
                                route_soup = BeautifulSoup(route_html_content, 'html.parser')

                                route_attributes = get_route_attributes(route_soup)
                                route_location = parse_location(route_attributes.get('formatted_location'))
                                route_sections = get_route_sections(route_soup)
                                route_details = get_route_details(route_soup)
                                comments = get_comments(route_soup)

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
                                    'primary_photo_url': route_attributes.get('primary_photo_url'),
                                    'insert_date': datetime.now(timezone.utc).isoformat()
                                }

                                comments_dict = [{'route_id': route_id, 'comment': comment, 'insert_date': datetime.now(timezone.utc).isoformat()} for comment in comments]

                                queries.insert_route(cursor, conn, current_route_data)
                                queries.insert_comments(cursor, conn, comments_dict)
                                conn.commit()

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
                                'user_id': user_id,
                                'route_id': current_route_data['route_id'],
                                'date': tick_date,
                                'type': tick_type,
                                'note': tick_note,
                                'insert_date': datetime.now(timezone.utc).isoformat()
                            }
                            queries.insert_tick(cursor, conn, tick_data)
                            conn.commit()
                            current_route_data = None

                    except Exception as e:
                        conn.rollback()
                        print(f"Error processing row: {str(e)}")
                        continue  
                
                print(f'Successfully processed page {page_number}')
                
            except Exception as e:
                print(f"Error processing page {page_number}: {str(e)}")
                conn.rollback()
                raise
                
            finally:
                if context:
                    context.close()
                if browser:
                    browser.close()