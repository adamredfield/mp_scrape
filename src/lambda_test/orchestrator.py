import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import json
import boto3

sqs = boto3.client('sqs')
QUEUE_URL = os.environ['QUEUE_URL']
BATCH_SIZE = 1  # pages per batch

def lambda_handler(event, context):

    user_id = event.get('user_id', '200362278/doctor-choss')  # Default if not provided
    base_url = f'https://www.mountainproject.com/user/{user_id}'
    ticks_url = f'{base_url}/ticks?page='

    print(f"Starting scrape for user: {user_id}")
    print(f"Queue URL: {QUEUE_URL}")
    from src.scraping import helper_functions
    print("Initialized helper functions")

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
            
            # Send smaller batch to SQS
            sqs.send_message_batch(
                QueueUrl=QUEUE_URL,
                Entries=batch
            )
            print(f"Queued pages {i} to {min(i + BATCH_SIZE, total_pages)}")
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'total_pages': total_pages,
                'total_batches': (total_pages + BATCH_SIZE - 1) // BATCH_SIZE,
                'pages_per_batch': BATCH_SIZE
            })
        }
        
    except Exception as e:
        print(f"Error in orchestrator: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }