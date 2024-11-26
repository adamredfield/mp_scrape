import json
import requests
from bs4 import BeautifulSoup
import re

# login creds -- can only see full comments if logged in while viewing route pages
username = "mpscrape2024@gmail.com"
password = "mpscrape"
mp_home_url = "https://www.mountainproject.com"

base_url = 'https://www.mountainproject.com/user/'
user = '200362278/doctor-choss'
constructed_url = f'{base_url}{user}'
ticks_url = f'{constructed_url}/ticks?page='

def login_and_save_session(playwright):
    browser = playwright.chromium.launch(headless=False)  # Use headless=True for production
    context = browser.new_context()
    page = context.new_page()

    # Go to the homepage to login
    page.goto(mp_home_url)
    page.click("a.sign-in")
    page.wait_for_selector("#login-modal", timeout=5000)

    page.fill("input[type='email'][name='email']", username)
    page.fill("input[type='password'][name='pass']", password)
    page.click("#login-modal button[type='submit']")

    # save cookies and storage_state to keep session open for scraping
    cookies = context.cookies()
    with open("cookies.json", "w") as cookie_file:
        json.dump(cookies, cookie_file)

    storage_state = context.storage_state()
    with open("storage.json", "w") as storage_file:
        json.dump(storage_state, storage_file)  # Convert dictionary to JSON string

    print("Login successful, session saved!")

    return browser, context

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
    # desc_rows is where type and FA data is held
    desc_rows = description_details_tbl.find_all('tr') 
    for row in desc_rows:
        cells = row.find_all('td')
        
        label = cells[0].text.strip()
        value = cells[1].text.strip()

        # Check for Type and FA labels
        if label == 'Type:':
            route_type = value
        elif label == 'FA:':
            fa = value
    return route_type, fa

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

def get_route_attributes(route_soup):

    route_attributes = {}

    rate_yds_element = route_soup.find('span', class_='rateYDS')
    if rate_yds_element:
        route_attributes['rating'] = rate_yds_element.text.strip().split()[0]
    stars_avg_text_element = route_soup.find('span', id=re.compile('^starsWithAvgText-'))
    avg_rating_text = stars_avg_text_element.text.strip().replace('\n', ' ')
    avg_rating_parts = avg_rating_text.split('from')
    route_attributes['avg_stars'] = avg_rating_parts[0].replace('Avg:', '').strip()
    route_attributes['num_ratings'] = avg_rating_parts[1].replace('votes', '').strip() 
    route_attributes['formatted_location'] = ' > '.join(link.text.strip() for link in route_soup.select('.mb-half.small.text-warm a'))

    return route_attributes
