import os
import sys

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
                
                # Process single page
                helper_functions.process_page(
                    page_number=message['page_number'],
                    ticks_url=message['ticks_url'],
                    user_id='200362278/doctor-choss',
                    retry_count=message.get('retry_count', 0)
                )
                
            except Exception as e:
                print(f"Error processing record: {str(e)}")
                raise
                
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        raise