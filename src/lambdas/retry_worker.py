import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import json
import traceback
from datetime import datetime

def lambda_handler(event, context):
    print(f"Starting retry worker with event: {json.dumps(event, default=str)}")
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

                if 'error_context' in message:
                    print("Previous failure error context:")
                    print(json.dumps(message['error_context'], indent=2))

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
                # Add new error context for this retry attempt
                error_context = {
                    "original_message": message,
                    "error_type": str(type(e).__name__),
                    "error_message": str(e),
                    "stack_trace": traceback.format_exc(),
                    "lambda_request_id": context.aws_request_id,
                    "timestamp": datetime.now().isoformat(),
                    "retry_count": retry_count,
                    "function_name": context.function_name,
                    "memory_limit": context.memory_limit_in_mb,
                    "remaining_time_ms": context.get_remaining_time_in_millis()
                }
                print(f"Retry failure error context:")
                print(json.dumps(error_context, indent=2))
                raise
                
    except Exception as e:
        print(f"Error processing record: {str(e)}")
        print(f"Stack trace: {traceback.format_exc()}")
        raise  # Let Lambda handle the retry
