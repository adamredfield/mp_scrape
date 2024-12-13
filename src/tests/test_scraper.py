import os
from dotenv import load_dotenv
load_dotenv()

from src.scraping import helper_functions

def test_scrape():
    # Test parameters
    user_id = "200362278/doctor-choss"  # or any other user
    base_url = f'https://www.mountainproject.com/user/{user_id}'
    ticks_url = f'{base_url}/ticks?page='
    
    try:
        # First test get_total_pages
        print("Testing get_total_pages...")
        total_pages = helper_functions.get_total_pages(ticks_url)
        print(f"Found {total_pages} pages to scrape")
        
        # Then test processing a single page
        print("\nTesting process_page...")
        helper_functions.process_page(
            page_number=1,
            ticks_url=ticks_url,
            user_id=user_id,
            retry_count=0
        )
        
    except Exception as e:
        print(f"Test failed: {str(e)}")

if __name__ == "__main__":
    test_scrape()