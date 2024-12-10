import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_proxy():
    """Test proxy using IPRoyal's exact format"""
    print("\nTesting proxy connection...")
    
    # Get credentials
    username = os.getenv('IPROYAL_USERNAME')
    password = os.getenv('IPROYAL_PASSWORD')
    
    # Print masked credentials for verification
    print(f"Username length: {len(username) if username else 'None'}")
    print(f"Password length: {len(password) if password else 'None'}")
    
    # Use their exact format
    url = 'https://ipv4.icanhazip.com'
    proxy = 'http://geo.iproyal.com:12321'
    proxy_auth = f'{username}:{password}'
    
    proxies = {
        'http': f'http://{proxy_auth}@geo.iproyal.com:12321',
        'https': f'http://{proxy_auth}@geo.iproyal.com:12321'
    }
    
    try:
        print("Making test request...")
        print(f"Using proxy URL: http://{username}:****@geo.iproyal.com:12321")
        response = requests.get(url, proxies=proxies)
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"Proxy test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_proxy() 