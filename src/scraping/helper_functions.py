import json
import requests
from bs4 import BeautifulSoup
import re

# login creds -- can only see full comments if logged in while viewing route pages
username = "mpscrape2024@gmail.com"
password = "mpscrape"
mp_home_url = "https://www.mountainproject.com"

base_url = f'{mp_home_url}/user/'
user_id = '200362278/doctor-choss'
constructed_url = f'{base_url}{user_id}'
ticks_url = f'{constructed_url}/ticks?page='

def login_and_save_session(playwright):
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

        context = browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        print("Context created successfully")

        page = context.new_page()
        page.goto(mp_home_url)
        page.wait_for_load_state('networkidle')
        print("Navigation complete")

        page.click("a.sign-in")
        page.wait_for_selector("#login-modal", timeout=5000)
        page.fill("input[type='email'][name='email']", username)
        page.fill("input[type='password'][name='pass']", password)
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
        print(f"Error in browser setup: {str(e)}")
        if 'browser' in locals():
            browser.close()
        raise

def fetch_dynamic_page_content(page, route_link):
        page.goto(route_link)
        last_height = None

        # loads comments
        while True:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")  # Scroll down
            page.wait_for_timeout(1000)  # Wait for 2 seconds
            new_height = page.evaluate("document.body.scrollHeight")  # Get new scroll height
            if new_height == last_height:  # Stop if no change in scroll height
                break
            last_height = new_height
            
        html_content = page.content()
        return html_content

def get_total_pages():
     # Get total number of rows to paginate through
    pagination_response = requests.get(ticks_url)
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

        # Find all comment bodies in the route_soup
        comment_elements = route_soup.find_all('div', class_='comment-body')

        # Loop through each comment and extract the text
        for comment in comment_elements:
            # Extract the full comment text from the <span> with id containing '-full'
            comment_text = comment.find('span', id=re.compile(r'.*-full')).get_text(strip=True)
            
            # Append the comment text to the list
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
    # desc_rows is where type and FA data is held
    desc_rows = description_details_tbl.find_all('tr') 
    for row in desc_rows:
        cells = row.find_all('td')

        label = cells[0].text.strip()
        value = cells[1].text.strip()

        # Check for Type and FA labels
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
    route_attributes['avg_stars'] = int(avg_rating_parts[0].replace('Avg:', '').strip())
    route_attributes['num_ratings'] = avg_rating_parts[1].replace('votes', '').strip() 
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