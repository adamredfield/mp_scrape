import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import json

def lambda_handler(event, context):
    from src.scraping import helper_functions
    print("Initialized helper functions")

    try:
        for record in event['Records']:
            try:
                message = json.loads(record['body'])
                retry_count = message.get('retry_count', 0) + 1
                page_number = message['page_number']
                ticks_url = message['ticks_url']
                user_id = message['user_id']

                print(f"Processing page {page_number} for user {user_id} using url: {ticks_url}")
                
                if retry_count <= 3:
                    helper_functions.process_page(
                        page_number=page_number,
                        ticks_url = ticks_url,
                        user_id= user_id,
                        retry_count=retry_count
                    )
                    print(f"Successfully processed failed page {message['page_number']}")

            except Exception as e:
                print(f"Page {message['page_number']} exceeded max retries")
                raise
                
    except Exception as e:
        print(f"Error processing record: {str(e)}")
        raise  # Let Lambda handle the retry
