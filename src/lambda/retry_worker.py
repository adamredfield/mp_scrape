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
    try:
        response = sqs.receive_message(
            QueueUrl=DLQ_URL,
            MaxNumberOfMessages=10,
            VisibilityTimeout=900
        )
        
        if 'Messages' not in response:
            print("No failed messages to process")
            return
            
        for message in response['Messages']:
            try:
                original_body = json.loads(message['Body'])
                retry_count = original_body.get('retry_count', 0) + 1
                
                # Always delete the message we just received
                sqs.delete_message(
                    QueueUrl=DLQ_URL,
                    ReceiptHandle=message['ReceiptHandle']
                )
                
                if retry_count <= 3:
                    try:
                        helper_functions.process_page(
                            page_number=original_body['page_number'],
                            ticks_url=original_body['ticks_url'],
                            user_id=original_body['user_id'],
                            retry_count=retry_count
                        )
                        print(f"Successfully processed failed page {original_body['page_number']}")
                        
                    except Exception as e:
                        print(f"Processing failed, sending back to DLQ with retry count {retry_count}")
                        # Send new message with updated retry count
                        new_message = {
                            'MessageBody': json.dumps({
                                'page_number': original_body['page_number'],
                                'ticks_url': original_body['ticks_url'],
                                'user_id': original_body['user_id'],
                                'retry_count': retry_count,
                                'last_error_time': datetime.now(timezone.utc).isoformat()
                            })
                        }
                        
                        sqs.send_message(
                            QueueUrl=DLQ_URL,
                            MessageBody=new_message['MessageBody']
                        )
                        
                else:
                    print(f"Page {original_body['page_number']} exceeded max retries")
                    
            except Exception as e:
                print(f"Error in message processing loop: {str(e)}")
                continue
                
    except Exception as e:
        print(f"Error in retry worker: {str(e)}")
        raise