import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.database.utils import create_connection

connection = create_connection()
cursor = connection.cursor()

 # Write the SQL command to create the Students table
create_table_query = '''

CREATE TABLE IF NOT EXISTS Routes (
    id INTEGER PRIMARY KEY,
    route_name TEXT NOT NULL,
    route_url TEXT NOT NULL,
    yds_rating TEXT,
    avg_stars REAL,
    num_votes INTEGER,
    location TEXT,
    type TEXT,
    fa TEXT,
    description TEXT,
    protection TEXT,
    comments TEXT,
    UNIQUE(id)
);

CREATE TABLE IF NOT EXISTS Ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER,
    tick_date TEXT,
    tick_type TEXT,
    tick_comment TEXT,
    FOREIGN KEY (route_id) REFERENCES Routes(id),
    UNIQUE(route_id, tick_date)
);

CREATE TABLE IF NOT EXISTS RouteComments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER,
    comment TEXT,
    FOREIGN KEY (route_id) REFERENCES Routes(id),
    UNIQUE(route_id, comment)
);

CREATE TABLE IF NOT EXISTS RouteAnalysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER,
    tags TEXT,
    sentiment_analysis TEXT,
    FOREIGN KEY (route_id) REFERENCES Routes(id)
);
'''

cursor.executescript(create_table_query)
connection.commit()
connection.close()