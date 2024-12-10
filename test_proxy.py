import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_proxy():
    username = os.getenv('IPROYAL_USERNAME')
    password = os.getenv('IPROYAL_PASSWORD')
    proxy_auth = f"{username}:{password}"
    proxy = 'geo.iproyal.com:12321'
    
    print(f"Proxy auth length: {len(proxy_auth) if proxy_auth else 'None'}")
    
    proxies = {
        'http': f'http://{proxy_auth}@{proxy}',
        'https': f'http://{proxy_auth}@{proxy}'
    }
    
    # Print the full URL (with password masked) for debugging
    debug_url = f'http://{username}:****@{proxy}'
    print(f"Using proxy URL: {debug_url}")
    
    try:
        # Add timeout and verify options
        response = requests.get('http://ipv4.icanhazip.com', 
                              proxies=proxies,
                              timeout=10,
                              verify=False)
        print(f"Success! Your IP is: {response.text.strip()}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_proxy() 