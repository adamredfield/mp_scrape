import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import json
import boto3
from src.scraping import helper_functions

sqs = boto3.client('sqs')
NEW_SCRAPE_QUEUE_URL = os.environ['NEW_SCRAPE_QUEUE_URL']
BATCH_SIZE = 1  # pages per batch

def lambda_handler(event, context):
    try:
        if 'Records' in event:
            for record in event['Records']:
                try:
                    message = json.loads(record['body'])
                    user_id = message['user_id']

                    scrape_user(user_id)
                except Exception as e:
                    print(f"Error processing message: {str(e)}")
                    raise e
        else:
            return {
                    'statusCode': 400,
                    'body': json.dumps('Error: user_id is required')
                }
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

def scrape_user(user_id):
    base_url = f'https://www.mountainproject.com/user/{user_id}'
    ticks_url = f'{base_url}/ticks?page='

    print(f"Starting scrape for user: {user_id}")
    print(f"Queue URL: {NEW_SCRAPE_QUEUE_URL}")

    try:
        total_pages = helper_functions.get_total_pages(ticks_url)
        print(f"Found {total_pages} pages to scrape")
        
        for i in range(1, total_pages + 1, BATCH_SIZE): # page numbers start at 1
            batch = []
            for page_num in range(i, min(i + BATCH_SIZE, total_pages + 1)): # if total_pages is smaller than stop, use total_pages
                batch.append({
                    'Id': str(page_num),
                    'MessageBody': json.dumps({
                        'page_number': page_num,
                        'ticks_url': ticks_url,
                        'user_id': user_id
                    })
                })
            if batch:
                QUEUE_URL = os.environ['QUEUE_URL']

                sqs.send_message_batch(
                    QueueUrl=QUEUE_URL,
                    Entries=batch
            )
            print(f"Queued pages {i} to {min(i + BATCH_SIZE, total_pages)}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'user_id': user_id,
                'total_pages': total_pages,
                'total_batches': (total_pages + BATCH_SIZE - 1) // BATCH_SIZE,
                'pages_per_batch': BATCH_SIZE
            })
        }
        
    except Exception as e:
        print(f"Error in scrape_user: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
    