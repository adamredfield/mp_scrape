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
    hueco_rating TEXT,
    aid_rating TEXT,
    danger_rating TEXT,
    avg_stars REAL,
    num_votes INTEGER,
    region TEXT,
    main_area TEXT,
    sub_area TEXT,
    specific_location TEXT,
    route_type TEXT,
    length_ft INTEGER,
    pitches INTEGER,
    commitment_grade TEXT,
    fa TEXT,
    description TEXT,
    protection TEXT,
    insert_date TEXT,
    UNIQUE(id)
);

CREATE TABLE IF NOT EXISTS Ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    route_id INTEGER,
    date TEXT,
    type TEXT,
    note TEXT,
    FOREIGN KEY (route_id) REFERENCES Routes(id),
    insert_date TEXT,
    UNIQUE(route_id, date)
);

CREATE TABLE IF NOT EXISTS RouteComments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER,
    comment TEXT,
    FOREIGN KEY (route_id) REFERENCES Routes(id),
    insert_date TEXT,
    UNIQUE(route_id, comment)
);

CREATE TABLE IF NOT EXISTS RouteAnalysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER,
    insert_date TEXT,
    FOREIGN KEY (route_id) REFERENCES Routes(id)
);

CREATE TABLE IF NOT EXISTS RouteAnalysisTags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER,
    tag_type TEXT,
    tag_value TEXT,
    insert_date TEXT,
    FOREIGN KEY (analysis_id) REFERENCES RouteAnalysis(id)
);

CREATE TABLE IF NOT EXISTS RouteAnalysisTagsReasoning (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER,
    tag_type TEXT,
    reasoning TEXT,
    insert_date TEXT,
    FOREIGN KEY (analysis_id) REFERENCES RouteAnalysis(id)
);

CREATE TABLE TagMapping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_tag TEXT,          
    clean_tag TEXT,         
    original_tag_type TEXT,
    mapped_tag_type TEXT,
    is_active BOOLEAN,
    insert_date TEXT,
    UNIQUE(raw_tag, original_tag_type) 
);

CREATE VIEW TagAnalysisView AS
SELECT DISTINCT 
    r.id route_id,
    r.route_name,
    COALESCE(tm.mapped_tag_type, tm.original_tag_type) as mapped_type, 
    COALESCE(tm.clean_tag, tm.raw_tag) as mapped_tag
FROM RouteAnalysisTags rat 
LEFT JOIN TagMapping tm on tm.raw_tag = rat.tag_value 
JOIN RouteAnalysis ra on rat.analysis_id = ra.id
JOIN Routes r on r.id = ra.route_id 
WHERE tm.is_active = 1;
'''

cursor.executescript(create_table_query)
connection.commit()
connection.close()