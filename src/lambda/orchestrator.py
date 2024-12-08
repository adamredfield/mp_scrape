import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import json
import boto3
from src.scraping import helper_functions

sqs = boto3.client('sqs')
QUEUE_URL = os.environ['https://sqs.us-east-1.amazonaws.com/855154218477/mp-scraper-queue']
BATCH_SIZE = 2  # 2 pages per batch

def lambda_handler(event, context):
    try:
        # 1. Get total pages from Mountain Project
        total_pages = helper_functions.get_total_pages()
        print(f"Found {total_pages} pages to scrape")
        
        # 2. Break into smaller batches (2 pages each)
        for i in range(1, total_pages + 1, BATCH_SIZE): # page numbers start at 1
            batch = []
            for page_num in range(i, min(i + BATCH_SIZE, total_pages + 1)): # if total_pages is smaller than stop, use total_pages
                batch.append({
                    'Id': str(page_num),
                    'MessageBody': json.dumps({
                        'page_number': page_num,
                        'ticks_url': f'{helper_functions.ticks_url}{page_num}',
                        'user': helper_functions.user
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