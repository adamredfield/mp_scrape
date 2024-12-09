import json
from src.scraping import helper_functions
from src.database.utils import create_connection
from src.database import queries
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from datetime import datetime
import re
import boto3
import sqlite3
import os

s3 = boto3.client('s3')
BUCKET_NAME = os.environ['S3_BUCKET_NAME']
DB_NAME = 'ticklist.db'
LOCAL_DB_PATH = f'/tmp/{DB_NAME}'


def get_db():
    # Download DB from S3 if it exists
    try:
        s3.download_file(BUCKET_NAME, DB_NAME, LOCAL_DB_PATH)
    except Exception as e:
        print(f"Could not download DB from S3: {str(e)}")
    return sqlite3.connect(LOCAL_DB_PATH)

def lambda_handler(event, context):
    try:
        # Get SQLite connection at start
        conn = get_db()
        cursor = conn.cursor()
        
        with sync_playwright() as playwright:
            browser, context = helper_functions.login_and_save_session(playwright)
            page = context.new_page()

            # SQS sends records in batches
            for record in event['Records']:
                try:
                    # Parse message
                    message = json.loads(record['body'])

                    page_number = message['page_number']
                    ticks_url = message['ticks_url']
                    
                    print(f'Processing page: {page_number}')
                    
                    # Get page content
                    tick_response = requests.get(ticks_url)
                    if tick_response.status_code != 200:
                        raise Exception(f"Failed to retrieve data: {tick_response.status_code}")

                    # Parse page
                    tick_soup = BeautifulSoup(tick_response.text, 'html.parser')
                    tick_table = tick_soup.find('table', class_='table route-table hidden-xs-down')
                    tick_rows = tick_table.find_all('tr', class_='route-row')

                    # Process rows (your existing logic here)
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
                                    'primary_photo_url': route_attributes.get('primary_photo_url'),
                                    'insert_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                }

                                comments_dict = [{'route_id': route_id, 'comment': comment, 'insert_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')} for comment in comments]

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
                                'user': helper_functions.user,
                                'route_id': current_route_data['route_id'],
                                'date': tick_date,
                                'type': tick_type,
                                'note': tick_note,
                                'insert_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            queries.insert_tick(cursor, conn, tick_data)
                            conn.commit()
                            current_route_data = None

                    print(f'Successfully processed page {page_number}')
                    # Upload DB to S3 after page is processed
                    conn.commit()  # Final commit before S3 upload
                    s3.upload_file(LOCAL_DB_PATH, BUCKET_NAME, DB_NAME)
                
                except Exception as e:
                    print(f"Error processing page {page_number}: {str(e)}")
                    # Optionally rollback on error
                    conn.rollback()
                    
    finally:
        if 'browser' in locals():
            browser.close()
        if 'conn' in locals():
            conn.close()
    
    return {
        'statusCode': 200,
        'body': json.dumps('Processing complete')
    }