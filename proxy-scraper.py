import random
import requests
import re

def get_us_proxy():
    """Get a random US proxy from spys.me"""
    try:
        response = requests.get("https://spys.me/proxy.txt")
        content = response.text.split('\n')
        
        us_proxies = []
        regex = r"[0-9]+(?:\.[0-9]+){3}:[0-9]+"
        
        # Collect US proxies
        for line in content:
            if any(indicator in line for indicator in ['US-A', 'US-H']):  # US Anonymous/High anonymity
                matches = re.finditer(regex, line)
                for match in matches:
                    us_proxies.append(match.group())
        
        if not us_proxies:
            raise Exception("No US proxies found")

        print(f"Found {len(us_proxies)} US proxies")
            
        # Pick a random proxy
        proxy = random.choice(us_proxies)
        print(f"Selected proxy: {proxy}")
        return proxy
        
    except Exception as e:
        print(f"Error getting proxy: {e}")
        return None

if __name__ == "__main__":
    proxy = get_us_proxy()
    print(proxy)
