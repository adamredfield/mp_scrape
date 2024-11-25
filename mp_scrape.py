import requests
from bs4 import BeautifulSoup
import re
import csv

base_url = 'https://www.mountainproject.com/user/'
user = '200362278/doctor-choss'
constructed_url = f'{base_url}{user}'
ticks_url = f'{constructed_url}/ticks?page='

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

ticks = []

for page in range(1,total_pages + 1):
    print(f'Scraping page: {page}')
    ticks_url_page = f'{ticks_url}{page}'
    print(ticks_url_page)

    tick_response = requests.get(ticks_url_page)
    if tick_response.status_code != 200:
        print(f"Failed to retrieve data: {tick_response.status_code}")

    tick_soup = BeautifulSoup(tick_response.text, 'html.parser')

    tick_table = tick_soup.find('table', class_='table route-table hidden-xs-down')

    rows = tick_table.find_all('tr', class_='route-row')

    # Table has two type of rows. One type holds route data and the other has tick details
    for row in rows:
        tick_details = row.find('td', class_='text-warm small pt-0')
        # check if tick details row rather than a route row
        if tick_details:
            # Append the additional info to the previous row's data
            current_route_data['tick_details'] = tick_details.text.strip()
            # We only want to append a row when we have the tick details
            ticks.append(current_route_data)
            current_route_data = None
            continue

        cells = row.find_all('td')
        route_name = ' '.join(cells[0].text.strip().replace('●', '').split())
        print(f'Retrieving data for {route_name}')
        route_link = row.find('a', href=True)['href']
        route_response = requests.get(route_link)
        route_soup = BeautifulSoup(route_response.text, 'html.parser')
        rate_yds_element = route_soup.find('span', class_='rateYDS')
        if rate_yds_element:
            rating = rate_yds_element.text.strip().split()[0]
        stars_avg_text_element = route_soup.find('span', id=re.compile('^starsWithAvgText-'))
        avg_rating_text = stars_avg_text_element.text.strip().replace('\n', ' ')
        avg_rating_parts = avg_rating_text.split('from')
        avg_stars = avg_rating_parts[0].replace('Avg:', '').strip()
        num_ratings = avg_rating_parts[1].replace('votes', '').strip() 
        formatted_location = ' > '.join(link.text.strip() for link in route_soup.select('.mb-half.small.text-warm a'))
        description_details_tbl = route_soup.find('table', class_='description-details')
        
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
        
        # desc_rows is where type and FA data is held
        desc_rows = description_details_tbl.find_all('tr') 
        for row in desc_rows:
            cells = row.find_all('td')
            
            label = cells[0].text.strip()
            value = cells[1].text.strip()

            # Check for Type and FA labels
            if label == 'Type:':
                type = value
            elif label == 'FA:':
                fa = value
        
        current_route_data = {
            'route_name': route_name,
            'route_url': route_link,
            'yds_rating': rating,  
            'avg_stars': avg_stars,
            'num_votes': num_ratings,
            'location': formatted_location,
            'type': type,
            'fa': fa,
            'description': route_sections.get('description'),
            'protection': route_sections.get('protection')
        }
        
output_file = 'ticks_data.csv'
with open(output_file, mode='w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=ticks[0].keys())
    writer.writeheader()
    writer.writerows(ticks) 

print(f"Ticks saved to {output_file}")