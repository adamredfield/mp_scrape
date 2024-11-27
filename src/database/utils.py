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