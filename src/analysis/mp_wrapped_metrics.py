import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.database.utils import create_connection
from src.analysis.analysis_utils import get_grade_group
from operator import itemgetter

conn = create_connection()
cursor = conn.cursor()

estimated_lengths_cte = f"""
        WITH estimated_lengths AS (
            SELECT  id,
                    CASE WHEN route_type ILIKE '%trad%' AND length_ft IS NULL AND pitches IS NULL -- trad single-pitch
                        THEN (SELECT avg(length_ft) FROM Routes r WHERE route_type ILIKE '%trad%'AND length_ft IS NOT NULL and pitches IS NULL AND length_ft < 230) -- avg single-pitch trad pitch length
                        WHEN route_type ILIKE '%trad%' AND length_ft IS NULL AND pitches IS NOT NULL -- trad multipitch
                        THEN (SELECT avg(length_ft/ pitches) FROM Routes r WHERE route_type ILIKE '%trad%' AND length_ft IS NOT NULL and pitches IS NOT NULL) * pitches
                        WHEN route_type ILIKE '%sport%' AND length_ft IS NULL AND pitches IS NOT NULL -- sport multipitch
                        THEN (SELECT avg(length_ft) FROM Routes r WHERE route_type ILIKE '%sport%'AND length_ft IS NOT NULL and pitches IS NULL AND length_ft < 230) -- avg single-pitch sport pitch length
                        WHEN route_type ILIKE '%sport%' AND length_ft IS NULL AND pitches IS NOT NULL -- sport multipitch
                        THEN (SELECT avg(length_ft/ pitches) FROM Routes r WHERE route_type ILIKE '%trad%' AND length_ft IS NOT NULL and pitches IS NOT NULL) * pitches
                        WHEN route_type ILIKE '%boulder%' AND length_ft IS NULL
                        THEN (SELECT avg(length_ft) FROM Routes r WHERE route_type ILIKE '%boulder%' AND length_ft IS NOT NULL) -- boulder
                        ELSE length_ft
                    END AS estimated_length
                FROM routes
            WHERE estimated_length IS NOT NULL
        )
        """


def total_routes(cursor):
    query = "SELECT COUNT(DISTINCT route_id) FROM Ticks WHERE date::text ILIKE '%2024%'"
    return cursor.execute(query).fetchone()[0]

def most_climbed_route(cursor):
    query = f"""
        {estimated_lengths_cte}
        SELECT DISTINCT concat(r.route_name, ' ~ ' ,
            r.specific_location,
            ' - ', 
            TRIM(NULLIF(CONCAT_WS(' ', r.yds_rating, r.hueco_rating, r.aid_rating,r.danger_rating, r.commitment_grade), '')), 
            ' - ',
            CAST(el.estimated_length AS INT),' ft') routes, 
        STRING_AGG(t.note, ' | ') notes,
        min(t.date) first_climbed,
        COUNT(*) times_climbed
        FROM Ticks t
        JOIN Routes r ON t.route_id = r.id
        LEFT JOIN estimated_lengths el on el.id = t.route_id 
        WHERE t.date ILIKE '%2024%'
        GROUP BY r.route_name
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """
    cursor.execute(query)
    columns = [description[0] for description in cursor.description]
    result = cursor.fetchone()
        
    # Get the route string and split it
    route_parts = result[0].split(' ~ ')
    if len(route_parts) == 2:
        route_name, rest = route_parts
        # Get everything after the last '>'
        location_parts = rest.split('>')
        clean_location = location_parts[-1].strip() if '>' in rest else rest
        # Reconstruct the route string
        clean_route = f"{route_name} ~ {clean_location}"
        return (clean_route,) + result[1:]

def top_rated_routes(cursor):
    query = """
        SELECT r.route_name, r.avg_stars
        FROM Routes r
        JOIN ticks t ON t.route_id = r.id
        WHERE t.date ILIKE '%2024%'
        ORDER BY r.avg_stars DESC
        LIMIT 5
    """
    return cursor.execute(query).fetchall()

def days_climbed(cursor):
    query = """
        SELECT COUNT(DISTINCT date)
        FROM Ticks
        WHERE date::text ILIKE '%2024%'
    """
    return cursor.execute(query).fetchone()[0]

def top_climbing_style(cursor):
    query = """
        SELECT rat.tag_value, count(*)
        from RouteAnalysis ra
        JOIN RouteAnalysisTags rat on rat.analysis_id = ra.id
        JOIN RouteAnalysisTagsReasoning ratr on ratr.analysis_id = rat.analysis_id AND rat.tag_type = ratr.tag_type
        JOIN ticks t on t.route_id = ra.route_id 
        WHERE rat.tag_type = 'style' AND t.date ILIKE '%2024%'
        GROUP BY rat.tag_value 
        ORDER BY count(*) desc
        LIMIT 1;
    """
    return cursor.execute(query).fetchone()[0]

def biggest_climbing_day(cursor):
    query = f"""
        {estimated_lengths_cte}
        SELECT  t.date,
                STRING_AGG(
                    concat(r.route_name, ' ~ ', 
                          TRIM(SUBSTRING(r.specific_location FROM POSITION('>' IN r.specific_location) + 1)), 
                          ' - ', 
                          TRIM(NULLIF(CONCAT_WS(' ', r.yds_rating, r.hueco_rating, r.aid_rating, r.danger_rating, r.commitment_grade), '')), 
                          ' - ',
                          CAST(el.estimated_length AS INT),' ft'
                    ), ' | '
                ) routes,
                CAST(ROUND(SUM(COALESCE(r.length_ft, el.estimated_length)),0) AS INTEGER) total_length,
                STRING_AGG(DISTINCT CONCAT(r.main_area, ', ', r.region), ' & ') areas
        FROM Ticks t 
        JOIN routes r on r.id = t.route_id 
        LEFT JOIN estimated_lengths el on el.id = t.route_id 
        WHERE t.date ILIKE '%2024%' AND r.route_name NOT ILIKE 'The Nose'
        GROUP BY t.date
        ORDER BY total_length desc
    LIMIT 1;
    """

    cursor.execute(query)
    columns = [description[0] for description in cursor.description]

    result = cursor.fetchone()
    
    return result

def top_grade(cursor, level):
    query = """
        SELECT
        	CASE
	        	WHEN r.route_type ILIKE '%Boulder%' THEN r.hueco_rating 
	        	WHEN r.route_type ILIKE '%Aid%' THEN r.aid_rating 
	        	ELSE r.yds_rating END AS primary_rating,
	        	count(*)
        FROM routes r
        join ticks t on t.route_id = r.id
        WHERE date::text ILIKE '%2024%'
        GROUP BY primary_rating 
        ORDER BY count(*) desc;
    """

    cursor.execute(query)
    results = cursor.fetchall()

    grouped_grades = {}

    for grade, count in results:
        grouped_grade = get_grade_group(grade, level)
        if grouped_grade in grouped_grades:
            grouped_grades[grouped_grade] += count
        else:
            grouped_grades[grouped_grade] = count
    
    return max(grouped_grades.items(), key=itemgetter(1))[0]  

def get_grade_distribution(cursor, level):
    query = """
        SELECT
            CASE
                WHEN r.route_type ILIK '%Boulder%' THEN r.hueco_rating 
                WHEN r.route_type LIKE '%Aid%' THEN r.aid_rating 
                ELSE r.yds_rating END AS primary_rating,
                count(*) as count
        FROM routes r
        join ticks t on t.route_id = r.id
        WHERE date::text ILIKE '%2024%'
        GROUP BY primary_rating 
        ORDER BY count desc;
    """

    cursor.execute(query)
    results = cursor.fetchall()

    grouped_grades = {}
    total_climbs = sum(count for _, count in results)

    for grade, count in results:
        grouped_grade = get_grade_group(grade, level)
        if grouped_grade in grouped_grades:
            grouped_grades[grouped_grade] += count
        else:
            grouped_grades[grouped_grade] = count
    
    # Convert to list of tuples with percentages
    distribution = [(grade, count, (count/total_climbs)*100) 
                   for grade, count in grouped_grades.items()]
    
    return sorted(distribution, key=lambda x: x[1], reverse=True)

def states_climbed(cursor):
    query = """
        SELECT region, count(distinct date) days_out, count(*) routes
        FROM Routes r
        JOIN ticks t on t.route_id = r.id
        WHERE date::text ILIKE '%2024%'
        GROUP BY region
        ORDER BY days_out desc;
    """
    cursor.execute(query)
    columns = [description[0] for description in cursor.description]

    result = cursor.fetchall()
    
    return result


def sub_areas_climbed(cursor):
    query = """
        SELECT sub_area , count(distinct date) days_out, count(*) routes
        FROM Routes r
        JOIN ticks t on t.route_id = r.id
        WHERE date::text ILIKE '%2024%'
        GROUP BY sub_area 
        ORDER BY days_out desc;
    """
    cursor.execute(query)
    columns = [description[0] for description in cursor.description]

    result = cursor.fetchall()
    
    return result

def regions_climbed(cursor):
    query = """
        SELECT count(distinct region)
        FROM Routes r
        JOIN ticks t on t.route_id = r.id
        WHERE date::text ILIKE '%2024%'
    """
    return cursor.execute(query).fetchone()[0]

def regions_sub_areas(cursor):
    query = """
        SELECT count(distinct sub_area)
        FROM Routes r
        JOIN ticks t on t.route_id = r.id
        WHERE date::text ILIKE '%2024%'
    """
    return cursor.execute(query).fetchone()[0]

def top_tags(cursor, tag_type):
    
    query = f"""
        WITH deduped_ticks AS(
            SELECT *,
            ROW_NUMBER() OVER (PARTITION BY route_id ORDER BY date DESC) as rn
            FROM Ticks
            WHERE date::text ILIKE '%2024%'
        )
        SELECT tav.mapped_type, tav.mapped_tag tag_value, count(*) as count
        FROM TagAnalysisView tav 
        JOIN deduped_ticks dt on dt.route_id = tav.route_id AND dt.rn = 1
        WHERE tav.mapped_type = '{tag_type}'
        GROUP BY tav.mapped_type, tav.mapped_tag
        ORDER BY count DESC;
    """
    cursor.execute(query)
    results = cursor.fetchall()
    return results