import os
import sys
import json
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.lambda_test.worker import lambda_handler


def test_worker():
    # Simulate SQS event with JSON-encoded body
    test_event = {
        'Records': [{
            'body': json.dumps({
                'page_number': 1,
                'ticks_url': 'https://www.mountainproject.com/user/201956982/choss-choss/ticks?page=',
                'user_id': '201956982/choss-choss'
            })
        }]
    }
    
    try:
        print("Testing worker with simulated SQS message...")
        lambda_handler(test_event, None)
        
    except Exception as e:
        print(f"Test failed: {str(e)}")

if __name__ == "__main__":

    test_worker()