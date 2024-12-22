import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from itertools import islice
from dotenv import load_dotenv
from src.database.utils import create_connection
from src.scraping.helper_functions import login_and_save_session, get_route_details

load_dotenv()

BATCH_SIZE = 10

def get_existing_routes(conn):
    """Get all route IDs and URLs from database"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, route_url 
        FROM routes.Routes 
    """)
    return cursor.fetchall()

def insert_route_types_batch(conn, route_data):
    """Insert batch of route types"""
    if not route_data:
        return
        
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO routes.route_types_temp (route_id, route_type)
        VALUES (%s, %s)
        ON CONFLICT (route_id) DO UPDATE 
        SET route_type = EXCLUDED.route_type,
            scraped_at = NOW()
    """, route_data)
    conn.commit()
    print(f"Committed batch of {len(route_data)} routes")

def process_routes_batch(routes_batch, page, total_routes, processed_count):
    """Process a batch of routes and return route_type data"""
    batch_data = []
    
    for route_id, route_url in routes_batch:
        try:
            processed_count += 1
            print(f"Processing route {route_id} ({processed_count}/{total_routes})")
            
            page.goto(route_url, timeout=90000)
            route_html = page.content()
            route_soup = BeautifulSoup(route_html, 'html.parser')
            
            route_details = get_route_details(route_soup)
            route_type = route_details['route_type'] if route_details else None
            
            batch_data.append((route_id, route_type))
            print(f"Processed route {route_id}: {route_type}")
            
        except Exception as e:
            print(f"Error processing route {route_id}: {str(e)}")
            batch_data.append((route_id, None))  # Add failed route with None type
            continue
            
    return batch_data, processed_count

def batch_iterator(iterable, batch_size):
    """Create an iterator that returns batches of the iterable"""
    iterator = iter(iterable)
    return iter(lambda: list(islice(iterator, batch_size)), [])

def main():

    with create_connection() as conn:
        
        # Get all routes
        routes = get_existing_routes(conn)
        total_routes = len(routes)
        print(f"Found {total_routes} routes to process")
        
        with sync_playwright() as playwright:
            browser, context = login_and_save_session(playwright)
            page = context.new_page()
            
            try:
                processed_count = 0
                for batch in batch_iterator(routes, BATCH_SIZE):
                    batch_data, processed_count = process_routes_batch(batch, page, total_routes, processed_count)
                    insert_route_types_batch(conn, batch_data)
                    print(f"Progress: {processed_count}/{total_routes} routes processed")
                    
                    
            finally:
                if context:
                    context.close()
                if browser:
                    browser.close()
                
        print("\nProcessing complete!")
        print(f"Total routes processed: {processed_count}")

if __name__ == "__main__":
    main()