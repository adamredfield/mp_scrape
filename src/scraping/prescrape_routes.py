import os
import sys
import time
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.database.utils import create_connection
from src.database import queries
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from src.scraping.helper_functions import login_and_save_session, fetch_dynamic_page_content, parse_route_data, parse_route_comments_data, get_total_pages

STATE_IDS = {
    '''"Alabama": "105905173",
    "Alaska": "105909311",
    "Arizona": "105708962",
    "Arkansas": "105901027",
    "California": "105708959",
    "Colorado": "105708956",
    "Connecticut": "105806977",
    "Delaware": "106861605",
    "Florida": "111721391",
    "Georgia": "105897947",
    "Hawaii": "106316122",
    "Idaho": "105708958",
    "Illinois": "105911816",
    "Indiana": "112389571",
    "Iowa": "106092653",
    "Kansas": "107235316",
    "Kentucky": "105868674",
    "Louisiana": "116720343",
    "Maine": "105948977",
    "Maryland": "106029417",
    "Massachusetts": "105908062",
    "Michigan": "106113246",
    "Minnesota": "105812481",
    "Mississippi": "108307056",
    "Missouri": "105899020",
    "Montana": "105907492",
    "Nebraska": "116096758",
    "Nevada": "105708961",
    "New Hampshire": "105872225",
    "New Jersey": "106374428",
    "New Mexico": "105708964",
    "New York": "105800424",
    "North Carolina": "105873282",
    "North Dakota": "106598130",
    "Ohio": "105994953",
    "Oklahoma": "105854466",
    "Oregon": "105708965",
    "Pennsylvania": "105913279",
    "Rhode Island": "106842810",
    "South Carolina": "107638915",
    "South Dakota": "105708963",
    "Tennessee": "105887760",
    "Texas": "105835804",
    "Utah": "105708957",
    "Vermont": "105891603",
    "Virginia": "105852400",
    "Washington": "105708966",
    "West Virginia": "105855459",
    "Wisconsin": "105708968",'''
    "Wyoming": "105708960"
}

states = list(STATE_IDS.keys())

def set_route_finder_filters(page, grade, state):
    """Set route finder filters for a specific grade range"""
    try:
        page.goto("https://www.mountainproject.com/route-finder")
        # Set route type to Rock
        #page.select_option('select[id="type"][name="type"]', "Rock")
        page.select_option('select[id="type"][name="type"]', "Boulder")
        
        # Set grade range
        #page.select_option('select[id="diffMinrock"][name="diffMinrock"]', grade)
        #page.select_option('select[id="diffMaxrock"][name="diffMaxrock"]', grade)
        page.select_option('select[id="diffMinboulder"][name="diffMinboulder"]', grade)
        page.select_option('select[id="diffMaxboulder"][name="diffMaxboulder"]', grade)
        
        # Check Trad, Sport, and Toprope
        #page.uncheck('input[id="check_is_top_rope"][name="is_top_rope"]')

        # Set stars filter to 3+ stars
        page.select_option('select[id="stars"][name="stars"]', "3.8")
        
        # Set pitches to Any
        page.evaluate(f'''
            document.getElementById("single-area-picker-name").innerHTML = "{state}";
            document.getElementById("initial-id-single").value = "{STATE_IDS[state]}";
        ''')
        
        # Click Find Routes
        page.click('input[type="submit"][class="btn btn-primary btn-sm"][value="Find Routes"]')
        
        # Wait for results to load
        no_routes = page.query_selector("td:has-text('- none -')")
        if no_routes:
            print(f"No routes found for {state} grade {grade}")
            return None
        
        return page.url
    
    except Exception as e:
        print(f"Error setting filters: {e}")
        return False


def scrape_high_rated_routes():
    """Main function to scrape all 3+ star routes"""

    """grades = [
        "5.0", "5.1", "5.2", "5.3", "5.4", "5.5", 
        "5.6", "5.7", "5.8", "5.9", "5.10a", "5.10b", "5.10c", "5.10d",
        "5.11a", "5.11b", "5.11c", "5.11d", "5.12a", "5.12b", "5.12c", "5.12d",
        "5.13a", "5.13b", "5.13c", "5.13d", "5.14a", "5.14b", "5.14c", "5.14d"
    ]
"""
    grades = [
        "20000", "20050", "20150", "20250", "20350", "20450", "20550", 
        "20650", "20750", "20850", "20950", "21050", "21150", "21250", "21350",
        "21450", "21550"
    ]

    with create_connection() as conn:  # Single database connection for entire session
        cursor = conn.cursor()
    
        with sync_playwright() as playwright:
            try:
                
                browser, context = login_and_save_session(playwright)
                page = context.new_page()
                
                for state in states:
                    print(f"\n{'='*50}")
                    print(f"Processing state: {state}")
                    print(f"{'='*50}")
                    
                    for grade in grades:
                        print(f"\nProcessing grade {grade} in {state}")

                        filtered_url = set_route_finder_filters(page, grade, state)
                        if not filtered_url:
                            print(f"Failed to set filters for {state}, grade {grade}")
                            continue

                        total_pages = get_total_pages(filtered_url)
                        print(f"Found {total_pages} pages of routes")
                        
                        # Process each page of results
                        for page_num in range(1, total_pages + 1):
                                try:
                                    print(f"Processing page {page_num}/{total_pages} for {state} grade {grade}")
                                    
                                    # Navigate to specific page if not on first page
                                    if page_num > 1:
                                        page.goto(f"{filtered_url}&page={page_num}")
                                        page.wait_for_selector(".table-responsive")
                                    
                                    route_ids_to_check = {}

                                    # Get route data from current page
                                    route_rows = page.query_selector_all(".table-responsive .route-table.hidden-xs-down .route-row")
                                    
                                    for row in route_rows:
                                        route_link = row.query_selector("a").get_attribute("href")
                                        route_name = row.query_selector("strong").text_content().strip()
                                        route_id = route_link.split('/route/')[1].split('/')[0]
                                        route_ids_to_check[route_id] = (route_name, route_link)
                                            
                                    # Check if route already exists before processing

                                    existing_routes = queries.check_routes_exists(cursor, route_ids_to_check.keys())

                                    for route_id, (route_name, route_link) in route_ids_to_check.items():
                                        print(f'Retrieving data for {route_name}')

                                        if int(route_id) in existing_routes:
                                            print(f"Route {route_name} with id {route_id} already exists in the database.")
                                            continue


                                        route_html_content = fetch_dynamic_page_content(page, route_link)
                                        if route_html_content == "BROWSER_CLOSED":
                                            print("Browser closed, recreating session...")
                                            if context:
                                                try:
                                                    context.close()
                                                except:
                                                    pass
                                            if browser:
                                                try:
                                                    browser.close()
                                                except:
                                                    pass
                                            browser, context = login_and_save_session(playwright)
                                            page = context.new_page()
                                            print("Session recreated, continuing with next route")
                                            continue
                                        if route_html_content is None:
                                            print(f"Skipping route {route_name} due to fetch errors")
                                            continue
                                        route_soup = BeautifulSoup(route_html_content, 'html.parser')
                                        
                                        current_route_data = parse_route_data(route_soup, route_id, route_name, route_link)
                                        current_route_comments_data = parse_route_comments_data(route_soup, route_id)
                                    

                                        queries.insert_routes_batch(cursor, [current_route_data])
                                        queries.insert_comments_batch(cursor, current_route_comments_data)
                                        conn.commit()
                                except Exception as e:
                                    print(f"Error processing page: {str(e)}")
                                    conn.rollback()
                                    if "context or browser has been closed" in str(e):
                                        if context:
                                            context.close()
                                        if browser:
                                            browser.close()
                                        context = None
                                        browser = None
                                        break
                                    
                                    continue
                                                        
            finally:
                if context:
                    context.close()
                if browser:
                    browser.close()

def scrape_fifty_classics():
    """Scrape data for the Fifty Classic Climbs"""


    with create_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT route_id FROM routes.fifty_classics")
        route_ids = [str(row[0]) for row in cursor.fetchall()]
    
        with sync_playwright() as playwright:
            try:
                browser, context = login_and_save_session(playwright)
                page = context.new_page()
                
                for route_id in route_ids:
                    # Construct and fetch route URL
                    route_link = f"https://www.mountainproject.com/route/{route_id}"
                    print(f"\nProcessing route: {route_link}")
                    
                    # Check if route already exists in routes table
                    existing_routes = queries.check_routes_exists(cursor, [route_id])
                    if int(route_id) in existing_routes:
                        print(f"Route with ID {route_id} already exists in database.")
                        continue
                    
                    route_html_content = fetch_dynamic_page_content(page, route_link)
                    
                    if route_html_content == "BROWSER_CLOSED":
                        print("Browser closed, recreating session...")
                        if context:
                            context.close()
                        if browser:
                            browser.close()
                        browser, context = login_and_save_session(playwright)
                        page = context.new_page()
                        continue
                        
                    if route_html_content is None:
                        print(f"Skipping route {route_id} due to fetch errors")
                        continue
                        
                    route_soup = BeautifulSoup(route_html_content, 'html.parser')
                    
                    # Get route name from the page
                    route_name = route_soup.select_one('h1').text.strip()
                    
                    # Parse and insert route data
                    current_route_data = parse_route_data(route_soup, route_id, route_name, route_link)
                    current_route_comments_data = parse_route_comments_data(route_soup, route_id)
                    
                    queries.insert_routes_batch(cursor, [current_route_data])
                    queries.insert_comments_batch(cursor, current_route_comments_data)
                    conn.commit()
                    
                    print(f"Successfully processed {route_name}")
                    
            except Exception as e:
                print(f"Error: {str(e)}")
                conn.rollback()
            finally:
                if context:
                    context.close()
                if browser:
                    browser.close()


if __name__ == "__main__":
    scrape_high_rated_routes()