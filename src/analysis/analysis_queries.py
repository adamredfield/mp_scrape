import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.analysis.analysis_utils import get_grade_group

def get_tick_type_distribution(cursor):
    """Get distribution of tick types (Lead, TR, etc.)"""
    query = '''
    SELECT 
        type,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Ticks WHERE type IS NOT NULL), 2) as percentage
    FROM Ticks
    WHERE type IS NOT NULL
    GROUP BY type
    ORDER BY count DESC;
    '''
    cursor.execute(query)
    return cursor.fetchall()

def get_grade_distribution(cursor, route_types=None, level='base'):
    """Get distribution of sends by grade with configurable grouping and route"""

    grade_column = "CASE "
    grade_column += "WHEN r.route_type LIKE '%Boulder%' THEN r.hueco_rating "
    grade_column += "WHEN r.route_type LIKE '%Aid%' THEN r.aid_rating "
    grade_column += "ELSE r.yds_rating END"

    # Build type filter using LIKE for comma-separated values
    if route_types:
        type_conditions = []
        for route_type in route_types:
            type_conditions.append(f"r.route_type LIKE '%{route_type}%'")
        type_filter = f"AND ({' OR '.join(type_conditions)})"
    else:
        type_filter = ''

    query = f'''
    SELECT 
        {grade_column} as grade,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (
            SELECT COUNT(*)
            FROM Ticks t2
            JOIN Routes r2 ON t2.route_id = r2.id
            WHERE r2.route_type IS NOT NULL
            AND (
                (r2.route_type NOT LIKE '%Aid%' AND t2.type != 'Lead / Fell/Hung')  -- Filter out fell/hung for non-aid
                OR (r2.route_type LIKE '%Aid%')                                  -- Keep all ticks for aid
            )
            {type_filter}
        ), 2) as percentage
    FROM Routes r
    JOIN Ticks t ON r.id = t.route_id
    WHERE {grade_column} IS NOT NULL
    AND (
        (r.route_type NOT LIKE '%Aid%' AND t.type != 'Lead / Fell/Hung') -- only include fell / hung for aid routes
        OR (r.route_type LIKE '%Aid%')
    )
    {type_filter}
    GROUP BY grade
    ORDER BY COUNT(*) DESC;
    '''
    params = route_types * 2 if route_types else []
    cursor.execute(query, params)
    results = cursor.fetchall()

    grouped_grades = {}

    for grade, count, percentage in results:
        grouped_grade = get_grade_group(grade, level)
        if grouped_grade in grouped_grades:
            grouped_grades[grouped_grade] += count
        else:
            grouped_grades[grouped_grade] = count

    total_count = sum(grouped_grades.values())
    return [(grade, count, round(count * 100.0 / total_count, 2)) 
        for grade, count in grouped_grades.items()]

def get_most_climbed_areas(cursor):
    """Get most frequently climbed areas"""
    query = '''
    SELECT 
        r.sub_area ,
        COUNT(*) as visit_count,
        AVG(r.avg_stars) as avg_rating
    FROM Routes r
    JOIN Ticks t ON r.id = t.route_id
    GROUP BY r.sub_area
    ORDER BY visit_count DESC
    LIMIT 20;
    '''
    cursor.execute(query)
    return cursor.fetchall()

def get_highest_rated_climbs(cursor):
    """Get highest rated climbs"""
    query = '''
    SELECT 
        DISTINCT r.route_name,
        r.yds_rating,
        r.avg_stars,
        r.num_votes
    FROM Routes r
    JOIN Ticks t ON r.id = t.route_id
    WHERE r.num_votes >= 10
    ORDER BY r.avg_stars DESC, num_votes DESC
    LIMIT 40
    '''
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