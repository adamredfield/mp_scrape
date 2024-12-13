import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.scraping import helper_functions

import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_proxy_connection():
    proxy_url = helper_functions.get_proxy_url()  # Use our existing function
    
    print("Testing proxy connection...")
    try:
        # Test with ipify
        response = requests.get(
            'https://api.ipify.org?format=json',
            proxies={
                'http': proxy_url,
                'https': proxy_url
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ IP Check Success! Connected via: {response.json()['ip']}")
            
            # If IP check works, try Mountain Project
            print("Testing Mountain Project connection...")
            mp_response = requests.get(
                'https://www.mountainproject.com',
                proxies={
                    'http': proxy_url,
                    'https': proxy_url
                },
                timeout=10
            )
            print(f"Mountain Project status: {mp_response.status_code}")
            if mp_response.status_code == 200:
                print("✅ Mountain Project connection successful!")
                return True
            
        else:
            print(f"❌ Failed with status code: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
    
    return False

if __name__ == "__main__":
    if test_proxy_connection():
        print("\n✅ Proxy connection working!")
    else:
        print("\n❌ Proxy connection failed")