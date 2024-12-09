import os
import sys
from dotenv import load_dotenv
import boto3
import sqlite3
import shutil

# Load environment variables
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)
load_dotenv(os.path.join(project_root, '.env'))

def sync_db():
    try:
        s3 = boto3.client('s3')
        BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
        LOCAL_DB_PATH = os.path.join(project_root, 'src', 'data', 'ticklist.db')
        TEMP_DB_PATH = os.path.join(project_root, 'src', 'data', 'ticklist_temp.db')
        
        print(f"\nDownloading to temporary file: {TEMP_DB_PATH}")
        s3.download_file(BUCKET_NAME, 'ticklist.db', TEMP_DB_PATH)
        
        # Verify the temp database
        temp_conn = sqlite3.connect(TEMP_DB_PATH)
        cursor = temp_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM routes")
        route_count = cursor.fetchone()[0]
        print(f"Verified temp database - contains {route_count} routes")
        temp_conn.close()
        
        # Close any existing connections
        print("Closing existing connections...")
        try:
            os.remove(LOCAL_DB_PATH + "-journal")  # Remove journal if exists
            os.remove(LOCAL_DB_PATH + "-wal")      # Remove WAL if exists
        except OSError:
            pass
            
        # Replace the old database
        print("Replacing old database...")
        shutil.move(TEMP_DB_PATH, LOCAL_DB_PATH)
        
        print(f"Successfully updated database at {LOCAL_DB_PATH}")
        
    except Exception as e:
        print(f"Error syncing DB: {str(e)}")
        if os.path.exists(TEMP_DB_PATH):
            os.remove(TEMP_DB_PATH)

if __name__ == "__main__":
    sync_db() 