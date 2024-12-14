import os
from contextlib import contextmanager

@contextmanager
def create_connection():
    """Create a PostgreSQL database connection - fail fast, no retries"""
    import psycopg2
    print("Initialized DB dependencies")

    try:
        host = os.getenv('POSTGRES_HOST')
        print(f"Attempting connection to {host}")
        connection = psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB', 'mp_scrape'),
            user=os.getenv('POSTGRES_USER', 'postgres'),
            password=os.getenv('POSTGRES_PASSWORD'),
            host=host,
            port=os.getenv('POSTGRES_PORT', '5432'),
            sslmode='require',
            connect_timeout=20
        )
        print("Connected successfully")
        yield connection
    except Exception as e:
        print(f"Connection failed: {e}")
        raise  # Fail fast, let Lambda handle retries
    finally:
        if 'connection' in locals() and connection and not connection.closed:
            connection.close()
            print("Connection closed")

def add_new_tags_to_mapping(cursor):
    """Add any new tags from Tags table to TagMapping with default values"""
    # Insert new tags with themselves as clean_tag
    cursor.execute('''
        INSERT INTO analysis.TagMapping (raw_tag, original_tag_type, is_active, insert_date)
        SELECT DISTINCT 
            rat.tag_value,
            rat.tag_type,
            True,
            rat.insert_date
        FROM analysis.RouteAnalysisTags rat
        LEFT JOIN analysis.TagMapping m ON rat.tag_value = m.raw_tag
        WHERE m.raw_tag IS NULL
        ON CONFLICT (raw_tag, original_tag_type) DO NOTHING;
    ''')

  