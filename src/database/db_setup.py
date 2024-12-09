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
    primary_photo_url TEXT,
    insert_date TIMESTAMP WITH TIME ZONE,
    UNIQUE(id)
);

CREATE TABLE IF NOT EXISTS Ticks (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    route_id INTEGER,
    date TIMESTAMP,
    type TEXT,
    note TEXT,
    insert_date TIMESTAMP,
    FOREIGN KEY (route_id) REFERENCES Routes(id),
    UNIQUE(route_id, date)
);

CREATE TABLE IF NOT EXISTS RouteComments (
    id SERIAL PRIMARY KEY,
    route_id INTEGER,
    comment TEXT,
    insert_date TIMESTAMP,
    FOREIGN KEY (route_id) REFERENCES Routes(id),
    UNIQUE(route_id, comment)
);

CREATE TABLE IF NOT EXISTS RouteAnalysis (
    id SERIAL PRIMARY KEY,
    route_id INTEGER,
    insert_date TIMESTAMP,
    FOREIGN KEY (route_id) REFERENCES Routes(id)
);

CREATE TABLE IF NOT EXISTS RouteAnalysisTags (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER,
    tag_type TEXT,
    tag_value TEXT,
    insert_date TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES RouteAnalysis(id)
);

CREATE TABLE IF NOT EXISTS RouteAnalysisTagsReasoning (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER,
    tag_type TEXT,
    reasoning TEXT,
    insert_date TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES RouteAnalysis(id)
);

CREATE TABLE IF NOT EXISTS TagMapping (
    id SERIAL PRIMARY KEY,
    raw_tag TEXT,          
    clean_tag TEXT,         
    original_tag_type TEXT,
    mapped_tag_type TEXT,
    is_active BOOLEAN,
    insert_date TIMESTAMP,
    UNIQUE(raw_tag, original_tag_type) 
);

CREATE OR REPLACE VIEW TagAnalysisView AS
SELECT DISTINCT 
    r.id route_id,
    r.route_name,
    COALESCE(tm.mapped_tag_type, tm.original_tag_type) as mapped_type, 
    COALESCE(tm.clean_tag, tm.raw_tag) as mapped_tag
FROM RouteAnalysisTags rat 
LEFT JOIN TagMapping tm on tm.raw_tag = rat.tag_value 
JOIN RouteAnalysis ra on rat.analysis_id = ra.id
JOIN Routes r on r.id = ra.route_id 
WHERE tm.is_active = true;
'''

for query in create_table_query.split(';'):
    if query.strip():
        cursor.execute(query)
connection.commit()
connection.close()