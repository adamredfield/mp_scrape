import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.analysis.analysis_utils import get_grade_group
from operator import itemgetter

def route_type_filter(route_types):
    if route_types:
        type_conditions = []
        for route_type in route_types:
            type_conditions.append(f"r.route_type LIKE '%{route_type}%'")
        type_filter = f"AND ({' OR '.join(type_conditions)})"
    else:
        type_filter = ''
    return type_filter

def year_filter(year=None):
    """Generate SQL WHERE clause for year filtering
    Args:
        year: Optional year to filter by. If None, no filter is applied
    """
    return f"AND t.date LIKE '%{year}%'" if year else ''


def get_tick_type_distribution(cursor, route_types=None):
    """Get distribution of tick types (Lead, TR, etc.)"""
    query = f"""
    SELECT 
        type,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Ticks WHERE type IS NOT NULL), 2) as percentage
    FROM Ticks t
    JOIN Routes r ON t.route_id = r.id
    WHERE type IS NOT NULL
    {route_type_filter(route_types)}
    GROUP BY type
    ORDER BY count DESC;
    """
    cursor.execute(query)
    return cursor.fetchall()

def get_grade_distribution(cursor, route_types=None, level='base', year=None):
    """Get distribution of sends by grade with configurable grouping and route"""

    grade_column = """
    CASE 
        WHEN r.route_type LIKE '%Boulder%' THEN r.hueco_rating 
        WHEN r.route_type LIKE '%Aid%' THEN r.aid_rating 
    ELSE r.yds_rating END"""

    query = f"""
    SELECT 
        {grade_column} AS grade,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (
            SELECT COUNT(*)
            FROM Ticks t
            JOIN Routes r2 ON t.route_id = r2.id
            WHERE r2.route_type IS NOT NULL
            AND (
                (r2.route_type NOT LIKE '%Aid%' AND t.type != 'Lead / Fell/Hung')  -- Filter out fell/hung for non-aid
                OR (r2.route_type LIKE '%Aid%')                                     -- Keep all ticks for aid
            )
            {route_type_filter(route_types)}
            {year_filter(year)}
        ), 2) as percentage
    FROM Routes r
    JOIN Ticks t ON r.id = t.route_id
    WHERE {grade_column} IS NOT NULL
    AND (
        (r.route_type NOT LIKE '%Aid%' AND t.type != 'Lead / Fell/Hung') -- only include fell / hung for aid routes
        OR (r.route_type LIKE '%Aid%')
    )
    {route_type_filter(route_types)}
    {year_filter(year)}
    GROUP BY grade
    ORDER BY COUNT(*) DESC;
    """

    cursor.execute(query)
    results = cursor.fetchall()

    grouped_grades = {}

    for grade, count, percentage in results:
        grouped_grade = get_grade_group(grade, level)
        if grouped_grade in grouped_grades:
            grouped_grades[grouped_grade] += count
        else:
            grouped_grades[grouped_grade] = count

    total_count = sum(grouped_grades.values())

    filtered_results = [{'Grade':grade, 'Count':count, 'Percentage':round(count * 100.0 / total_count, 2)}
        for grade, count in grouped_grades.items()]
    
    filtered_results.sort(key = itemgetter('Count'), reverse = True)
    
    return filtered_results

def get_most_climbed_areas(cursor, route_types=None):

    if route_types:
        type_conditions = []
        for route_type in route_types:
            type_conditions.append(f"r.route_type LIKE '%{route_type}%'")
        type_filter = f"WHERE ({' OR '.join(type_conditions)})"
    else:
        type_filter = ''
    """Get most frequently climbed areas"""
    query = f"""
    SELECT 
        r.sub_area ,
        COUNT(*) as visit_count,
        AVG(r.avg_stars) as avg_rating
    FROM Routes r
    JOIN Ticks t ON r.id = t.route_id
    {type_filter}
    GROUP BY r.sub_area
    ORDER BY visit_count DESC
    LIMIT 20;
    """
    cursor.execute(query)
    return cursor.fetchall()

def get_highest_rated_climbs(cursor, selected_styles=None, route_types=None, year=None, tag_type=None):
    """Get highest rated climbs
    Args:
        cursor: Database cursor
        selected_styles: Optional list of styles to filter by
        route_types: Optional list of route types to filter by
        year: Optional year to filter by
        tag_type: Type of tag to filter by (default: 'style')
    """
    style_filter = ""
    if selected_styles:
        style_conditions = [
            f"(',' || GROUP_CONCAT(tav.mapped_tag, ',') || ',') LIKE '%,{style},%'"
            for style in selected_styles
        ]
        style_filter = f"HAVING {' AND '.join(style_conditions)}"

    query = f"""
    WITH deduped_ticks AS(
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY route_id ORDER BY date DESC) as rn
    FROM Ticks
    )
    SELECT 
        DISTINCT concat(r.route_name, ' ~ ', r.main_area, ' > ', r.specific_location,' - ', 
        TRIM(NULLIF(CONCAT_WS(' ', r.yds_rating, r.hueco_rating, r.aid_rating,r.danger_rating, r.commitment_grade), ''))) routes,
        TRIM(NULLIF(CONCAT_WS(' ', 
            r.yds_rating,
            r.hueco_rating,
            r.aid_rating,
            r.danger_rating,
            r.commitment_grade), '')) as grade,
        r.avg_stars,
        r.num_votes,
        GROUP_CONCAT(tav.mapped_tag, ', ') as tags
    FROM Routes r
    LEFT JOIN TagAnalysisView tav on r.id = tav.route_id 
        AND tav.mapped_type = '{tag_type}'
    JOIN deduped_ticks t ON r.id = t.route_id AND rn = 1
    WHERE r.num_votes >= 10
    {route_type_filter(route_types)}
    {year_filter(year)}
    GROUP BY r.route_name, r.yds_rating, r.avg_stars, r.num_votes
    {style_filter}
    ORDER BY r.avg_stars DESC, num_votes DESC
    LIMIT 20
    """
    cursor.execute(query)
    return cursor.fetchall()

def get_route_type_preferences(cursor):
    """Analyze preferences for different route types"""
    query = '''
    SELECT 
        r.route_type,
        COUNT(*) as count,
        AVG(r.avg_stars) as avg_rating,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Ticks), 2) as percentage
    FROM Routes r
    JOIN Ticks t ON r.id = t.route_id
    WHERE r.route_type IS NOT NULL
    AND r.route_type IN ('Trad', 'Boulder', 'Sport', 'Aid')
    GROUP BY r.route_type
    ORDER BY count DESC
    '''
    cursor.execute(query)
    return cursor.fetchall()        

def get_distinct_styles(cursor):
    """Get all distinct active styles from TagMapping"""
    query = '''
    SELECT DISTINCT coalesce(clean_tag, raw_tag) as style
    FROM TagMapping
    WHERE is_active = 1
    AND COALESCE(mapped_tag_type, original_tag_type) = 'style'
    ORDER BY style;
    '''
    cursor.execute(query)
    return [row[0] for row in cursor.fetchall()]      

def get_bigwall_routes(cursor):
    """Get all bigwall routes"""
    query = '''
    SELECT  
        t.date,
        group_concat(concat(r.route_name, ' - ', TRIM(NULLIF(CONCAT_WS(' ', r.yds_rating, r.hueco_rating, r.aid_rating,r.danger_rating, r.commitment_grade), ''))), ' | ') routes,
        CAST(round(sum(coalesce(r.length_ft, el.estimated_length)),0) AS INTEGER) total_length,
        group_concat(DISTINCT r.main_area || ' | ') areas
    FROM Ticks t 
    JOIN routes r on r.id = t.route_id 
    LEFT JOIN estimated_lengths el on el.id = t.route_id 
    WHERE t.date LIKE '%2024%' AND r.route_name NOT LIKE 'The Nose'
    GROUP BY t.date
    ORDER BY total_length desc
    LIMIT 1;
    '''
    cursor.execute(query)
    return cursor.fetchall()

def get_length_climbed(cursor, area_type = "main_area", year=None):
    query = f"""
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
    SELECT 
        substr(t.date, -4) as year,
        r.{area_type} location,
        sum(coalesce(r.length_ft, el.estimated_length)) length_climbed
    FROM routes r
    JOIN Ticks t ON r.id = t.route_id
    LEFT JOIN estimated_lengths el on el.id = r.id
    WHERE t.date IS NOT NULL AND CAST(year AS INTEGER) >= 1999
    {year_filter(year)}
    GROUP BY year, r.{area_type}
    ORDER BY year DESC, length_climbed DESC;
    """
    cursor.execute(query)
    return cursor.fetchall()