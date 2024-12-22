import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from src.lambdas.orchestrator import lambda_handler
from dotenv import load_dotenv
load_dotenv()



def test_orchestrator():
    # test event
    test_event = {
        "user_id": "200832950/stevie-morris"
    }
    
    test_context = None
    
    try:
        print("Testing orchestrator with Stevie Morris user_id...")
        response = lambda_handler(test_event, test_context)
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"Test failed: {str(e)}")

if __name__ == "__main__":
    test_orchestrator() 