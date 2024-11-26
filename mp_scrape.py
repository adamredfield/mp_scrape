import requests
from bs4 import BeautifulSoup
import re
import csv
from playwright.sync_api import sync_playwright
import helper_functions

with sync_playwright() as playwright:
    browser, context = helper_functions.login_and_save_session(playwright)
    # create page once. Each loop will use same page rather than new tab.
    page = context.new_page()

    # how many pages in user's ticks to paginate through
    total_pages = helper_functions.get_total_pages()
    
    # initialize ticklist
    ticklist = []

    #for page in range(1,total_pages + 1):
    for tick_page in range(1,2):
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
            # check if tick details row rather than a route row
            if tick_details:
                # Append the additional info to the previous row's data
                current_route_data['tick_details'] = tick_details.text.strip()
                # We only want to append a row when we have the tick details
                ticklist.append(current_route_data)
                current_route_data = None
                continue

            cells = row.find_all('td')
            route_name = ' '.join(cells[0].text.strip().replace('●', '').split())
            print(f'Retrieving data for {route_name}')
            route_link = row.find('a', href=True)['href']

            route_html_content = helper_functions.fetch_dynamic_page_content(page, route_link)
            route_soup = BeautifulSoup(route_html_content, 'html.parser')
            # Use route_soup to obtain specific route data
            route_attributes = helper_functions.get_route_attributes(route_soup)
            route_sections = helper_functions.get_route_sections(route_soup)
            route_type, fa = helper_functions.get_route_details(route_soup)
            comments = helper_functions.get_comments(route_soup)

            current_route_data = {
                'route_name': route_name,
                'route_url': route_link,
                'yds_rating': route_attributes.get('rating'),  
                'avg_stars': route_attributes.get('avg_stars'),
                'num_votes': route_attributes.get('num_ratings'),
                'location': route_attributes.get('formatted_location'),
                'type': route_type,
                'fa': fa,
                'description': route_sections.get('description'),
                'protection': route_sections.get('protection'),
                'comments': comments
            }

    browser.close()
        
output_file = 'ticks_data.csv'
with open(output_file, mode='w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=ticklist[0].keys())
    writer.writeheader()
    writer.writerows(ticklist) 

print(f"Ticks saved to {output_file}")