import os
import sys
import time

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import json
import os

def lambda_handler(event, context):
    from src.scraping import helper_functions
    print("Initialized helper functions")

    """Handle batch of SQS messages"""
    try:
        for record in event['Records']:
            try:
                message = json.loads(record['body'])
                page_number = message['page_number']
                ticks_url = message['ticks_url']
                user_id = message['user_id']

                print(f"Processing page {page_number} for user {user_id} using url: {ticks_url}")
                
                # Process single page
                helper_functions.process_page(
                    page_number=page_number,
                    ticks_url=ticks_url,
                    user_id=user_id,
                    retry_count=message.get('retry_count', 0)
                )
                
            except Exception as e:
                print(f"Error processing record: {str(e)}")
                raise
                
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        raise