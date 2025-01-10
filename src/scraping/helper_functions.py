from src.analysis.fa_parsing import parse_fa_data
from playwright.sync_api import sync_playwright
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from src.database import queries
import re
import requests
import json
import os
import sys
import unicodedata

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.database.utils import create_connection, add_new_tags_to_mapping
from src.analysis.ai_analysis_helper_functions import process_route, process_route_response, save_analysis_results

mp_home_url = "https://www.mountainproject.com"

def get_proxy_url():
    """Get IPRoyal proxy URL - returns a string"""
    username = os.getenv('IPROYAL_USERNAME')
    password = os.getenv('IPROYAL_PASSWORD')

    proxy_url = f'http://{username}:{password}@geo.iproyal.com:12321'
    print(f"Generated proxy URL: http://{username}:****@geo.iproyal.com:12321")

    return proxy_url


def login_and_save_session(playwright):
    browser = None
    context = None
    page = None

    mp_username = os.getenv('MP_USERNAME')
    mp_password = os.getenv('MP_PASSWORD')

    print("Starting browser launch sequence...")
    try:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--single-process',
                '--no-zygote'
            ]
        )
        print("Browser launched successfully")

        context = browser.new_context()
        page = context.new_page()
        print("Context created successfully")

        page.set_default_navigation_timeout(90000)
        page.set_default_timeout(90000)
        page.goto(mp_home_url)
        print("Navigation complete")
        page.wait_for_selector("a.sign-in", timeout=10000)
        print("Sign in button found")
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


def fetch_dynamic_page_content(page, route_link, max_retries=3):
    for attempt in range(max_retries):
        try:
            page.goto(route_link, timeout=90000)
            last_height = None

            # loads comments
            while True:
                # Scroll down
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1000)
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            html_content = page.content()
            return html_content
        except Exception as e:
            print(
                f"Error fetching {route_link} (Attempt {attempt +1}): {str(e)}")
            if "context or browser has been closed" in str(e):
                return "BROWSER_CLOSED"

            if attempt < max_retries - 1:
                continue
            else:
                print(
                    f"Failed to fetch {route_link} after {max_retries} attempts")
                raise


def get_total_pages(ticks_url):
    pagination_response = requests.get(ticks_url)
    if pagination_response.status_code != 200:
        print(f"Failed to retrieve data: {pagination_response.status_code}")
        raise Exception(
            f"Failed to get total pages: {pagination_response.status_code}")

    pagination_soup = BeautifulSoup(pagination_response.text, 'html.parser')
    pagination_div = pagination_soup.find('div', class_='pagination')
    if not pagination_div:
        return 1  # Return 1 if no pagination found

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
        # Extract the full comment text from the <span> with id containing
        # '-full'
        comment_text = comment.find(
            'span', id=re.compile(r'.*-full')).get_text(strip=True)
        comments.append(comment_text)
    return comments


def get_route_details(route_soup):
    description_details_tbl = route_soup.find(
        'table', class_='description-details')
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
    sections = ['description', 'protection']
    route_sections = {}

    # Find the <h2> header matching the section name
    headers = route_soup.find_all('h2', class_='mt-2')
    for header in headers:
        header_text = header.get_text(strip=True).lower()
        for section in sections:
            if section.lower() in header_text:
                section_div = header.find_next_sibling('div', class_='fr-view')
                route_sections[section.lower()] = ' '.join(
                    section_div.get_text(separator=' ').split())
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
        # Get all YDS spans (could contain both YDS, Hueco & Aid)
        rating_spans = rating_h2.find_all('span', class_='rateYDS')
        for span in rating_spans:
            rating = span.text.split()[0]
            if rating.startswith('5.'):
                grade_types['yds_rating'] = rating
            elif rating.startswith('V'):
                grade_types['hueco_rating'] = rating

        danger_text = rating_h2.get_text().strip()
        for word in danger_text.split():
            if (word.startswith('A') or word.startswith('C')
                    ) and len(word) > 1 and word[1].isdigit():
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
    stars_avg_text_element = route_soup.find(
        'span', id=re.compile('^starsWithAvgText-'))
    avg_rating_text = stars_avg_text_element.text.strip().replace('\n', ' ')
    avg_rating_parts = avg_rating_text.split('from')
    route_attributes['avg_stars'] = avg_rating_parts[0].replace(
        'Avg:', '').strip()
    route_attributes['num_ratings'] = int(
        avg_rating_parts[1].replace(
            'votes',
            '').replace(
            'vote',
            '').replace(
                ',',
            '').strip())
    route_attributes['formatted_location'] = ' > '.join(
        link.text.strip() for link in route_soup.select('.mb-half.small.text-warm a'))
    photo_link = route_soup.find('div', class_='carousel-item')
    route_attributes['primary_photo_url'] = (
        photo_link['style'].split('url("')[1].split('")')[
            0] if photo_link and 'style' in photo_link.attrs else None
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
    valid_types = [
        'Trad',
        'Sport',
        'Aid',
        'Boulder',
        'Alpine',
        'Mixed',
        'Ice',
        'Snow',
        'TR']
    found_types = []

    # Process parts until we hit a length, pitch, or grade indicator to get
    # type(s)
    for part in parts:
        if not any(indicator in part.lower()
                   for indicator in ['ft', 'pitch', 'grade']):
            for valid_type in valid_types:
                if valid_type in part:
                    found_types.append(valid_type)
            continue

        # Match route length (e.g., "500 ft (152 m)")
        length_match = re.search(r'(\d+)\s*ft', part)
        if length_match:
            parsed_details['length_ft'] = int(
                length_match.group(1))  # Store in feet
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

    parsed_details['route_type'] = ', '.join(
        found_types) if found_types else None

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


def check_routes_exist(cursor, route_ids):
    """Check multiple routes at once"""
    if not route_ids:
        return set()

    placeholders = ','.join(['%s'] * len(route_ids))
    cursor.execute(
        f"SELECT id FROM routes.Routes WHERE id IN ({placeholders})",
        tuple(route_ids)
    )
    return {row[0] for row in cursor.fetchall()}


def parse_route_data(route_soup, route_id, route_name, route_link):
    route_attributes = get_route_attributes(route_soup)
    route_location = parse_location(route_attributes.get('formatted_location'))
    route_sections = get_route_sections(route_soup)
    route_details = get_route_details(route_soup)

    current_route_data = {
        'route_id': route_id,
        'route_name': sanitize_text(route_name),
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
    return current_route_data


def parse_route_comments_data(route_soup, route_id):
    comments = get_comments(route_soup)
    comments_dict = [{'route_id': route_id, 'comment': comment, 'insert_date': datetime.now(
        timezone.utc).isoformat()} for comment in comments]
    return comments_dict


def parse_tick_details(tick_details, current_route_data, user_id):

    tick_details_text = tick_details.text.strip()

    date_pattern = r'[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}'
    date_match = re.search(date_pattern, tick_details_text)
    tick_date = date_match.group() if date_match else None

    tick_type = None
    tick_note = None
    pitch_count = None

    valid_tick_types = [
        'Solo', 'TR', 'Follow', 'Lead',
        'Lead / Onsight', 'Lead / Flash',
        'Lead / Redpoint', 'Lead / Pinkpoint',
        'Lead / Fell/Hung'
    ]

    if ' · ' in tick_details_text:
        # Get everything after the bullet, following date
        post_date_text = tick_details_text.split(' · ')[1]
        pitch_pattern = r'(\d+)\s*pitches?'
        pitch_match = re.search(pitch_pattern, post_date_text)
        if pitch_match:
            pitch_count = int(pitch_match.group(1))

        if '.' in post_date_text:
            parts = post_date_text.split('.', 1)
            if "pitches" in parts[0].lower():
                next_parts = parts[1].split('.', 1)
                potential_type = next_parts[0].strip()
                if potential_type in valid_tick_types:
                    tick_type = potential_type
                    tick_note = next_parts[1].strip() if len(
                        next_parts) > 1 else None
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
        'pitches_climbed': pitch_count,
        'insert_date': datetime.now(timezone.utc).isoformat()
    }
    return tick_data


def process_page(page_number, ticks_url, user_id, retry_count=0):
    """Process a single page"""

    tick_data = []
    route_data = []
    route_comments_data = []
    route_ids_to_check = {}
    tick_details_map = {}
    current_route_data = None
    ai_route_analysis_data = []

    browser = None
    context = None
    page = None

    try:
        with sync_playwright() as playwright:
            try:
                browser, context = login_and_save_session(playwright)
                page = context.new_page()

                print(
                    f'Processing page: {page_number} for user {user_id}. (Retry #{retry_count})')

                current_page_url = f"{ticks_url}{page_number}"
                page.goto(current_page_url, timeout=90000)
                tick_html = page.content()
                tick_soup = BeautifulSoup(tick_html, 'html.parser')
                tick_table = tick_soup.find(
                    'table', class_='table route-table hidden-xs-down')
                tick_rows = tick_table.find_all('tr', class_='route-row')
                print(f"Found {len(tick_rows) / 2} routes to process")

                for i in range(0, len(tick_rows),
                               2):  # Step by 2 since routes and ticks alternate
                    try:
                        route_row = tick_rows[i]
                        tick_row = tick_rows[i + 1] if i + \
                            1 < len(tick_rows) else None
                        cells = route_row.find_all('td')
                        route_name = ' '.join(
                            cells[0].text.strip().replace(
                                '●', '').split())
                        route_link = route_row.find('a', href=True)['href']
                        route_id = route_link.split('/route/')[1].split('/')[0]

                        tick_details = tick_row.find(
                            'td', class_='text-warm small pt-0') if tick_row else None

                        if route_id not in tick_details_map:
                            tick_details_map[route_id] = []

                        if tick_details:
                            tick_details_map[route_id].append(tick_details)

                        route_ids_to_check[route_id] = (route_name, route_link)

                    except IndexError as e:
                        print(f"Error processing row {i}: {str(e)}")
                        continue  # Skip this row and continue with next
                    except Exception as e:
                        print(f"Unexpected error processing row {i}: {str(e)}")
                        continue

                with create_connection() as conn:
                    cursor = conn.cursor()
                    existing_routes = queries.check_routes_exists(
                        cursor, route_ids_to_check.keys())

                    for route_id, (route_name,
                                   route_link) in route_ids_to_check.items():
                        print(f'Retrieving data for {route_name}')

                        current_route_data = {
                            'route_id': route_id,
                            'route_name': route_name
                        }
                        if int(route_id) in existing_routes:
                            print(
                                f"Route {route_name} with id {route_id} already exists in the database.")

                        if int(route_id) not in existing_routes:
                            route_html_content = fetch_dynamic_page_content(
                                page, route_link)

                            if route_html_content == "BROWSER_CLOSED":
                                print("Browser closed, recreating session...")
                                if context:
                                    try:
                                        context.close()
                                    except BaseException:
                                        pass
                                if browser:
                                    try:
                                        browser.close()
                                    except BaseException:
                                        pass
                                browser, context = login_and_save_session(
                                    playwright)
                                page = context.new_page()
                                print(
                                    "Session recreated, continuing with next route")
                                continue
                            if route_html_content is None:
                                print(
                                    f"Skipping route {route_name} due to fetch errors")
                                continue

                            route_soup = BeautifulSoup(
                                route_html_content, 'html.parser')
                            current_route_data = parse_route_data(
                                route_soup, route_id, route_name, route_link)
                            current_route_comments_data = parse_route_comments_data(
                                route_soup, route_id)

                            route_data.append(current_route_data)
                            route_comments_data.extend(
                                current_route_comments_data)
                            parse_fa_data(current_route_data['fa'])

                            combined_grade = ' '.join(filter(None, [
                                current_route_data.get('yds_rating') or '',
                                current_route_data.get('hueco_rating') or '',
                                current_route_data.get('aid_rating') or '',
                                current_route_data.get('danger_rating') or '',
                                current_route_data.get(
                                    'commitment_grade') or ''
                            ])).strip() or None

                            combined_location = ' > '.join(filter(None, [
                                current_route_data.get('region') or '',
                                current_route_data.get('main_area') or '',
                                current_route_data.get('sub_area') or '',
                                current_route_data.get(
                                    'specific_location') or ''
                            ])).strip() or None

                            route_for_analysis = {
                                'route_id': current_route_data['route_id'],
                                'route_name': current_route_data['route_name'],
                                'combined_grade': combined_grade,
                                'avg_stars': current_route_data['avg_stars'],
                                'num_votes': current_route_data['num_votes'],
                                'location': combined_location,
                                'route_type': current_route_data['route_type'],
                                'fa': current_route_data['fa'],
                                'description': current_route_data['description'],
                                'protection': current_route_data['protection'],
                                'comments': ' | '.join(c['comment'] for c in current_route_comments_data)
                            }
                            print(f"Running AI analysis")
                            ai_route_response = process_route(
                                route_for_analysis)
                            if ai_route_response:
                                ai_route_analysis_data.append(
                                    process_route_response(ai_route_response))

                        if route_id in tick_details_map:
                            print(
                                f"\nProcessing ticks for {route_name} ({route_id})")
                            print(
                                f"Number of ticks: {len(tick_details_map[route_id])}")
                            for tick_detail in tick_details_map[route_id]:
                                tick_data.append(
                                    parse_tick_details(
                                        tick_detail,
                                        current_route_data,
                                        user_id))

                    if route_data:
                        print(f"Attempting to insert {len(route_data)} routes")
                        queries.insert_routes_batch(cursor, route_data)
                    if route_comments_data:
                        print(
                            f"Attempting to insert {len(route_comments_data)} comments")
                        queries.insert_comments_batch(
                            cursor, route_comments_data)
                    if tick_data:
                        print(f"Attempting to insert {len(tick_data)} ticks")
                        cursor = conn.cursor()
                        queries.insert_ticks_batch(cursor, tick_data)
                    if ai_route_analysis_data:
                        print(f"Attempting to insert AI results")
                        for result in ai_route_analysis_data:
                            save_analysis_results(cursor, result)

                    add_new_tags_to_mapping(cursor)

                    conn.commit()  # commit all transactions together
                    print(f'Successfully processed page {page_number}')
            finally:
                if context:
                    context.close()
                if browser:
                    browser.close()

    except Exception as e:
        print(f"Error processing page {page_number}: {str(e)}")
        raise

import unicodedata

def sanitize_text(text):
    if not text:
        return text
        
    # Replace problematic characters
    replacements = {
        '…': '...',
        '\u2019': "'",  # Replace curly single quote with straight single quote
        '"': '"',
        '"': '"',
        '–': '-',
        '—': '-',
        '\u2028': ' ',  # Line separator
        '\u2029': ' '   # Paragraph separator
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
        
    # Normalize Unicode characters
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    
    return text.strip()

def sanitize_route_data(route_data):
    """Sanitize all text fields in route data"""
    text_fields = [
        'route_name',
        'description',
        'protection',
        'fa',
        'region',
        'main_area',
        'sub_area',
        'specific_location',
        'route_type',
        'commitment_grade'
    ]
    
    for field in text_fields:
        if field in route_data and route_data[field]:
            route_data[field] = sanitize_text(route_data[field])
    
    return route_data