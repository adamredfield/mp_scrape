import os
import sys
from datetime import datetime, timezone

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.scraping import helper_functions
import json
import boto3

sqs = boto3.client('sqs')
DLQ_URL = os.environ['DLQ_URL']
MAIN_QUEUE_URL = os.environ['QUEUE_URL']

def lambda_handler(event, context):
    """Handle batch of SQS messages from DLQ"""
    try:
        for record in event['Records']:
            try:
                message = json.loads(record['body'])
                retry_count = message.get('retry_count', 0) + 1
                
                if retry_count <= 3:
                    helper_functions.process_page(
                        page_number=message['page_number'],
                        ticks_url=message['ticks_url'],
                        user_id=message['user_id'],
                        retry_count=retry_count
                    )
                    print(f"Successfully processed failed page {message['page_number']}")
                else:
                    print(f"Page {message['page_number']} exceeded max retries")
                    
            except Exception as e:
                print(f"Error processing record: {str(e)}")
                raise  # Let Lambda handle the retry
                
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        raise

