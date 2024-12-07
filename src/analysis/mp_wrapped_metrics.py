import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.database.utils import create_connection

conn = create_connection()
cursor = conn.cursor()

def total_routes():
    query = "SELECT COUNT(DISTINCT route_id) FROM Ticks WHERE date LIKE '%2024%'"
    return cursor.execute(query).fetchone()[0]

def most_climbed_route():
    query = """
        SELECT r.route_name, group_concat(t.note) notes, min(t.date) first_climbed, COUNT(*) times_climbed
        FROM Ticks t
        JOIN Routes r ON t.route_id = r.id
        WHERE t.date LIKE '%2024%'
        GROUP BY r.route_name
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """
    return cursor.execute(query).fetchone()[0]

def top_rated_routes():
    query = """
        SELECT r.route_name, r.avg_stars
        FROM Routes r
        JOIN ticks t ON t.route_id = r.id
        WHERE t.date LIKE '%2024%'
        ORDER BY r.avg_stars DESC
        LIMIT 5
    """
    return cursor.execute(query).fetchall()

def days_climbed():
    query = """
        SELECT COUNT(DISTINCT date)
        FROM Ticks
        WHERE date LIKE '%2024%'
    """
    return cursor.execute(query).fetchone()[0]

def top_climbing_style():
    query = """
        SELECT rat.tag_value, count(*)
        from RouteAnalysis ra
        JOIN RouteAnalysisTags rat on rat.analysis_id = ra.id
        JOIN RouteAnalysisTagsReasoning ratr on ratr.analysis_id = rat.analysis_id AND rat.tag_type = ratr.tag_type
        JOIN ticks t on t.route_id = ra.route_id 
        WHERE rat.tag_type = 'style' AND t.date LIKE '%2024%'
        GROUP BY rat.tag_value 
        ORDER BY count(*) desc
        LIMIT 1;
    """
    return cursor.execute(query).fetchone()[0]

def biggest_climbing_day():
    query = """
        WITH estimated_lengths AS (
            SELECT  id,
                    CASE WHEN route_type LIKE '%trad%' AND length_ft IS NULL AND pitches IS NULL -- trad single-pitch
                        THEN (SELECT avg(length_ft) FROM Routes r WHERE route_type LIKE '%trad%'AND length_ft IS NOT NULL and pitches IS NULL AND length_ft < 230) -- avg single-pitch trad pitch length
                        WHEN route_type LIKE '%trad%' AND length_ft IS NULL AND pitches IS NOT NULL -- trad multipitch
                        THEN (SELECT avg(length_ft/ pitches) FROM Routes r WHERE route_type LIKE '%trad%' AND length_ft IS NOT NULL and pitches IS NOT NULL) * pitches
                        WHEN route_type LIKE '%sport%' AND length_ft IS NULL AND pitches IS NOT NULL -- sport multipitch
                        THEN (SELECT avg(length_ft) FROM Routes r WHERE route_type LIKE '%sport%'AND length_ft IS NOT NULL and pitches IS NULL AND length_ft < 230) -- avg single-pitch sport pitch length
                        WHEN route_type LIKE '%sport%' AND length_ft IS NULL AND pitches IS NOT NULL -- sport multipitch
                        THEN (SELECT avg(length_ft/ pitches) FROM Routes r WHERE route_type LIKE '%trad%' AND length_ft IS NOT NULL and pitches IS NOT NULL) * pitches
                        WHEN route_type LIKE '%boulder%' AND length_ft IS NULL
                        THEN (SELECT avg(length_ft) FROM Routes r WHERE route_type LIKE '%boulder%' AND length_ft IS NOT NULL) -- boulder
                    END AS estimated_length
                FROM routes
            WHERE estimated_length IS NOT NULL
        )
        SELECT  t.date,
                group_concat(r.route_name, ' | ') routes,
                round(sum(coalesce(r.length_ft, el.estimated_length)),0) total_length
        FROM Ticks t 
        JOIN routes r on r.id = t.route_id 
        LEFT JOIN estimated_lengths el on el.id = t.route_id 
        WHERE t.date LIKE '%2024%' AND r.route_name NOT LIKE 'The Nose'
        GROUP BY t.date
        ORDER BY total_length desc
    LIMIT 1;
    """
    return cursor.execute(query).fetchone()[0]


