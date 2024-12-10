import os
import psycopg2
from pathlib import Path
import time
import random


def create_connection():
    """Create a PostgreSQL database connection with retries and exponential backoff"""
    max_attempts = 5
    base_delay = 1  # Start with 1 second delay

    for attempt in range(max_attempts):
        try:
            print(f"Attempt {attempt + 1}: Connecting to {os.getenv('POSTGRES_HOST')}")
            connection = psycopg2.connect(
                dbname=os.getenv('POSTGRES_DB', 'mp_scrape'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD'),
                host=os.getenv('POSTGRES_HOST'),
                port=os.getenv('POSTGRES_PORT', '5432'),
                sslmode='require',
                connect_timeout=10
            )
            print("Connected successfully")
            return connection
        except psycopg2.OperationalError as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_attempts - 1:
                # Exponential backoff with jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
            else:
                print("Max attempts reached. Could not connect to the database.")
                raise

def add_new_tags_to_mapping(cursor):
    """Add any new tags from Tags table to TagMapping with default values"""
    
    # Insert new tags with themselves as clean_tag
    cursor.execute('''
        INSERT INTO TagMapping (raw_tag, original_tag_type, is_active, insert_date)
        SELECT DISTINCT 
            rat.tag_value,
            rat.tag_type,
            True,
            rat.insert_date
        FROM RouteAnalysisTags rat
        LEFT JOIN TagMapping m ON rat.tag_value = m.raw_tag
        WHERE m.raw_tag IS NULL
        ON CONFLICT (raw_tag, original_tag_type) DO NOTHING;
    ''')

    