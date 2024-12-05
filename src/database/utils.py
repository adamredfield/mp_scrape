import os
import sqlite3
from pathlib import Path

def get_db_path():
    """Get the absolute path to the database file"""
    root_dir = Path(__file__).parent.parent.parent  # Go up to project root
    return os.path.join(root_dir, 'data', 'ticklist.db')

def create_connection():
    """Create a database connection"""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    return sqlite3.connect(db_path) 

def add_new_tags_to_mapping(cursor):
    """Add any new tags from Tags table to TagMapping with default values"""
    
    # Insert new tags with themselves as clean_tag
    cursor.execute('''
        INSERT OR IGNORE INTO TagMapping (raw_tag, original_tag_type, is_active, insert_date)
        SELECT DISTINCT 
            rat.tag_value ,
            rat.tag_type,
            True,
            rat.insert_date
        FROM RouteAnalysisTags rat
        LEFT JOIN TagMapping m ON rat.tag_value = m.raw_tag
        WHERE m.raw_tag IS NULL;
    ''')

    