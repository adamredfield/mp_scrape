import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.scraping import helper_functions
from playwright.sync_api import sync_playwright

def test_login_and_session():
    with sync_playwright() as playwright:
        try:
            browser, context = helper_functions.login_and_save_session(playwright)
            print("Login successful!")
            
            # Test creating a new page
            page = context.new_page()
            print("New page created successfully")
            
            # Try to fetch a simple page
            page.goto('https://www.mountainproject.com')
            print("Navigation successful")
            
        except Exception as e:
            print(f"Test failed: {str(e)}")
        finally:
            if 'context' in locals():
                context.close()
            if 'browser' in locals():
                browser.close()

if __name__ == "__main__":
    test_login_and_session() 