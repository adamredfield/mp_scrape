import os
import psycopg2
from pathlib import Path


def create_connection():
    """Create a PostgreSQL database connection"""
    try:
        connection = psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB', 'mp_scrape'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD'),
            host=os.getenv('POSTGRES_HOST'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            sslmode='require'
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

    