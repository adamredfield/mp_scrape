import os
from contextlib import contextmanager

@contextmanager
def create_connection():
    """Create a PostgreSQL database connection with retries and exponential backoff"""
    import psycopg2
    import random
    import time
    import socket
    print("Initialized DB dependencies")

    max_attempts = 5
    base_delay = 1

    last_exception = None
    for attempt in range(max_attempts):
        try:
            # Test network first
            host = os.getenv('POSTGRES_HOST')
            try:
                socket.getaddrinfo(host, 5432)
                print(f"DNS resolution successful for {host}")
            except socket.gaierror as e:
                print(f"DNS resolution failed: {e}")
                raise

            print(f"Attempt {attempt + 1}: Connecting to {host}")
            connection = psycopg2.connect(
                dbname=os.getenv('POSTGRES_DB', 'mp_scrape'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD'),
                host=host,
                port=os.getenv('POSTGRES_PORT', '5432'),
                sslmode='require',
                connect_timeout=10  # Shorter timeout
            )
            print("Connected successfully")
            break
        except (psycopg2.OperationalError, socket.gaierror) as e:
            last_exception = e
            print(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
            else:
                print(f"All {max_attempts} attempts failed. Last error: {last_exception}")
                raise last_exception
    try:
        yield connection
    finally:
        if 'connection' in locals() and connection:
            connection.close()
            print("Connection closed")

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

    