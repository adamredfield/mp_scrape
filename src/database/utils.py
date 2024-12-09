import os
import psycopg2
from pathlib import Path


def create_connection():
    """Create a PostgreSQL database connection"""
    try:
        connection = psycopg2.connect(
            dbname="mp_scrape",
            user="postgres",
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port="5432"
        )
        return connection
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
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

    