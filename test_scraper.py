import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import os
from dotenv import load_dotenv
from src.scraping.helper_functions import get_proxy_url
import requests

load_dotenv()

def test_proxy():
    """Test proxy using exact Lambda configuration"""
    print("\nTesting proxy connection...")
    
    # Get proxy URL using actual Lambda function
    proxy_url = get_proxy_url()
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    print(f"Using proxies config:")
    print(f"HTTP: {proxies['http'].replace(os.getenv('IPROYAL_PASSWORD'), '****')}")
    print(f"HTTPS: {proxies['https'].replace(os.getenv('IPROYAL_PASSWORD'), '****')}")
    
    try:
        print("\nMaking test request...")
        response = requests.get('https://ipv4.icanhazip.com', proxies=proxies)
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"Proxy test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_proxy() 