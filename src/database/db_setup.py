import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.database.utils import create_connection

connection = create_connection()
cursor = connection.cursor()

create_routes_schema_query = 'CREATE SCHEMA IF NOT EXISTS routes;'
create_analysis_schema_query = 'CREATE SCHEMA IF NOT EXISTS analysis;'

create_table_query = '''
CREATE TABLE IF NOT EXISTS routes.Routes (
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

CREATE TABLE IF NOT EXISTS routes.Ticks (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    route_id INTEGER,
    date TIMESTAMP,
    type TEXT DEFAULT '' NOT NULL,
    note TEXT,
    note_hash TEXT DEFAULT md5('') NOT NULL,
    insert_date TIMESTAMP,
    FOREIGN KEY (route_id) REFERENCES routes.Routes(id),
    UNIQUE (user_id, route_id, "date", type, note_hash)
);

CREATE TABLE IF NOT EXISTS routes.RouteComments (
    id SERIAL PRIMARY KEY,
    route_id INTEGER,
    comment TEXT,
    comment_hash TEXT,
    insert_date TIMESTAMP,
    FOREIGN KEY (route_id) REFERENCES routes.Routes(id),
    UNIQUE(route_id, comment_hash)
);

CREATE TABLE IF NOT EXISTS analysis.RouteAnalysis (
    id SERIAL PRIMARY KEY,
    route_id INTEGER,
    insert_date TIMESTAMP,
    FOREIGN KEY (route_id) REFERENCES routes.Routes(id)
);

CREATE TABLE IF NOT EXISTS analysis.RouteAnalysisTags (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER,
    tag_type TEXT,
    tag_value TEXT,
    rank INTEGER,
    insert_date TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES analysis.RouteAnalysis(id)
);

CREATE TABLE IF NOT EXISTS analysis.RouteAnalysisTagsReasoning (
    id SERIAL PRIMARY KEY,
    analysis_id INTEGER,
    tag_type TEXT,
    reasoning TEXT,
    insert_date TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES analysis.RouteAnalysis(id)
);

CREATE TABLE IF NOT EXISTS analysis.TagMapping (
    id SERIAL PRIMARY KEY,
    raw_tag TEXT,          
    clean_tag TEXT,         
    original_tag_type TEXT,
    mapped_tag_type TEXT,
    is_active BOOLEAN,
    insert_date TIMESTAMP,
    UNIQUE(raw_tag, original_tag_type) 
);

CREATE or replace VIEW analysis.TagAnalysisView as
with ranked_tags AS(
	SELECT DISTINCT 
	    r.id route_id,
	    r.route_name,
	    COALESCE(tm.mapped_tag_type, tm.original_tag_type) as mapped_type, 
	    COALESCE(tm.clean_tag, tm.raw_tag) as mapped_tag,
	            ROW_NUMBER() OVER (
	            PARTITION BY r.id, COALESCE(tm.mapped_tag_type, tm.original_tag_type)
	            ORDER BY rat.rank
	        )::integer as new_rank
	FROM analysis.routeanalysistags_v2 rat
	LEFT JOIN analysis.TagMapping tm on tm.raw_tag = rat.tag_value and tm.original_tag_type = rat.tag_type
	JOIN analysis.RouteAnalysis_v2 ra on rat.analysis_id = ra.id
	JOIN routes.Routes r on r.id = ra.route_id
	where tm.is_active = true
	)
SELECT 
    route_id,
    route_name,
    mapped_type,
    mapped_tag,
    new_rank as rank
FROM ranked_tags
ORDER BY route_id, mapped_type, new_rank;

CREATE TABLE IF NOT EXISTS analysis.tagMapping (
    id SERIAL PRIMARY KEY,
    raw_tag TEXT NOT NULL,          
    clean_tag TEXT NOT NULL,         
    original_tag_type TEXT NOT NULL,
    mapped_tag_type TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    insert_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(raw_tag, original_tag_type))

CREATE VIEW analysis.TagAnalysisView AS
SELECT DISTINCT 
    r.id route_id,
    r.route_name,
    COALESCE(tm.mapped_tag_type, tm.original_tag_type) as mapped_type, 
    COALESCE(tm.clean_tag, tm.raw_tag) as mapped_tag
FROM analysis.RouteAnalysisTags rat 
LEFT JOIN analysis.TagMapping tm on tm.raw_tag = rat.tag_value 
JOIN analysis.RouteAnalysis ra on rat.analysis_id = ra.id
JOIN routes.Routes r on r.id = ra.route_id 
WHERE tm.is_active = true;
);
'''

for query in create_table_query.split(';'):
    if query.strip():
        cursor.execute(query)
connection.commit()
