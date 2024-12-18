import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.analysis.ai_analysis_helper_functions import get_grade_group
from operator import itemgetter

def route_type_filter(route_types):
    if route_types:
        type_conditions = []
        for route_type in route_types:
            type_conditions.append(f"r.route_type ILIKE '%{route_type}%'")
        type_filter = f"AND ({' OR '.join(type_conditions)})"
    else:
        type_filter = ''
    return type_filter

def year_filter(year=None):
    """Generate SQL WHERE clause for year filtering
    Args:
        year: Optional year to filter by. If None, no filter is applied
    """
    return f"AND EXTRACT(YEAR FROM t.date) = {year}" if year else ''

def add_user_filter(user_id, table_alias='t'):
    """
    Add user filtering to a query
    Args:
        query: SQL query string (can be empty)
        user_id: User ID to filter by
        table_alias: Alias of the Ticks table in the query (default 't')
    """
    return f"AND {table_alias}.user_id = '{user_id}'"

def get_tick_type_distribution(conn, route_types=None, user_id=None):
    """Get distribution of tick types (Lead, TR, etc.)"""
    query = f"""
    SELECT 
        type,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM routes.Ticks WHERE type IS NOT NULL), 2) as percentage
    FROM routes.Ticks t
    JOIN routes.Routes r ON t.route_id = r.id
    WHERE type IS NOT NULL
    {route_type_filter(route_types)}
    {add_user_filter(user_id)}
    GROUP BY type
    ORDER BY count DESC;
    """
    return conn.query(query)

def get_grade_distribution(conn, route_types=None, level='base', year=None, user_id=None):
    """Get distribution of sends by grade with configurable grouping and route"""

    grade_column = """
    CASE 
        WHEN r.route_type ILIKE '%Boulder%' THEN r.hueco_rating 
        WHEN r.route_type ILIKE '%Aid%' THEN r.aid_rating 
    ELSE r.yds_rating END"""

    query = f"""
    SELECT 
        {grade_column} AS grade,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (
            SELECT COUNT(*)
            FROM routes.Ticks t
            JOIN routes.Routes r2 ON t.route_id = r2.id
            WHERE r2.route_type IS NOT NULL
            AND (
                (r2.route_type NOT ILIKE '%Aid%' AND t.type != 'Lead / Fell/Hung')  -- Filter out fell/hung for non-aid
                OR (r2.route_type ILIKE '%Aid%')                                     -- Keep all ticks for aid
            )
            {route_type_filter(route_types)}
            {year_filter(year)}
            {add_user_filter(user_id)}
        ), 2) as percentage
    FROM routes.Routes r
    JOIN routes.Ticks t ON r.id = t.route_id
    WHERE {grade_column} IS NOT NULL
    AND (
        (r.route_type NOT ILIKE '%Aid%' AND t.type != 'Lead / Fell/Hung') -- only include fell / hung for aid routes
        OR (r.route_type ILIKE '%Aid%')
    )
    {route_type_filter(route_types)}
    {year_filter(year)}
    {add_user_filter(user_id)}
    GROUP BY grade
    ORDER BY COUNT(*) DESC;
    """

    results =  conn.query(query)

    grouped_grades = {}

    for _, row in results.iterrows():
        grade = row['grade']
        count = row['count']
        grouped_grade = get_grade_group(grade, level)
        if grouped_grade in grouped_grades:
            grouped_grades[grouped_grade] += count
        else:
            grouped_grades[grouped_grade] = count

    total_count = sum(grouped_grades.values())

    filtered_results = [
        {
            'Grade': grade,
            'Count': count,
            'Percentage': round(count * 100.0 / total_count, 2)
        }
        for grade, count in grouped_grades.items()
    ]
    
    filtered_results.sort(key = itemgetter('Count'), reverse = True)
    
    return filtered_results

def get_highest_rated_climbs(conn, selected_styles=None, route_types=None, year=None, tag_type=None, user_id=None):
    """Get highest rated climbs"""
    style_filter = ""
    if selected_styles:
        style_conditions = [
            f"(',' || STRING_AGG(tav.mapped_tag, ',') || ',') ILIKE '%,{style},%'"
            for style in selected_styles
        ]
        style_filter = f"HAVING {' AND '.join(style_conditions)}"

    query = f"""
    WITH deduped_ticks AS(
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY route_id ORDER BY date DESC) as rn
    FROM routes.Ticks
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
        STRING_AGG(tav.mapped_tag, ', ') as tags,
        r.primary_photo_url,
        r.route_url
    FROM routes.Routes r
    LEFT JOIN analysis.TagAnalysisView tav on r.id = tav.route_id 
        AND tav.mapped_type = '{tag_type}'
    JOIN deduped_ticks t ON r.id = t.route_id AND rn = 1
    WHERE r.num_votes >= 10
    {route_type_filter(route_types)}
    {year_filter(year)}
    {add_user_filter(user_id)}
    GROUP BY r.route_name, r.main_area, r.specific_location, r.yds_rating, r.hueco_rating, 
             r.aid_rating, r.danger_rating, r.commitment_grade, r.avg_stars, r.num_votes,
             r.primary_photo_url, r.route_url
    {style_filter}
    ORDER BY r.avg_stars DESC, num_votes DESC
    LIMIT 20
    """
    return conn.query(query)

def get_route_type_preferences(conn, user_id=None):
    """Analyze preferences for different route types"""
    query = f'''
    SELECT 
        r.route_type,
        COUNT(*) as count,
        AVG(r.avg_stars) as avg_rating,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM routes.Ticks), 2) as percentage
    FROM routes.Routes r
    JOIN routes.Ticks t ON r.id = t.route_id
    WHERE r.route_type IS NOT NULL
    AND r.route_type IN ('Trad', 'Boulder', 'Sport', 'Aid')
    {add_user_filter(user_id)}
    GROUP BY r.route_type
    ORDER BY count DESC
    '''
    return conn.query(query)

def get_bigwall_routes(cursor, user_id=None):
    """Get all bigwall routes"""
    query = '''
    SELECT  
        t.date,
        STRING_AGG(concat(r.route_name, ' - ', TRIM(NULLIF(CONCAT_WS(' ', r.yds_rating, r.hueco_rating, r.aid_rating,r.danger_rating, r.commitment_grade), ''))), ' | ') routes,
        CAST(round(sum(coalesce(r.length_ft, el.estimated_length)),0) AS INTEGER) total_length,
        STRING_AGG(DISTINCT r.main_area || ' | ') areas
    FROM routes.Ticks t 
    JOIN routes.Routes r on r.id = t.route_id 
    LEFT JOIN estimated_lengths el on el.id = t.route_id 
    WHERE TO_CHAR(t.date, 'YYYY') ILIKE '2024'
    {add_user_filter(user_id)}
    GROUP BY t.date
    ORDER BY total_length desc
    LIMIT 1;
    '''
    cursor.execute(query)
    return cursor.fetchall()

def get_length_climbed(conn, area_type="main_area", year=None, user_id=None):
    query = f"""
    {estimated_lengths_cte}
    SELECT 
        EXTRACT(YEAR FROM t.date) as year,
        r.{area_type} location,
        sum(coalesce(r.length_ft, el.estimated_length)) length_climbed
    FROM routes.Routes r
    JOIN routes.Ticks t ON r.id = t.route_id
    LEFT JOIN estimated_lengths el on el.id = r.id
    WHERE t.date IS NOT NULL AND EXTRACT(YEAR FROM t.date) >= 1999
    {year_filter(year)}
    {add_user_filter(user_id)}
    GROUP BY year, r.{area_type}
    ORDER BY year DESC, length_climbed DESC;
    """
    return conn.query(query).itertuples(index=False)

estimated_lengths_cte = f"""
        WITH estimated_lengths AS (
        SELECT  id,
                CASE WHEN route_type ILIKE '%trad%' AND length_ft IS NULL AND pitches IS NULL -- trad single-pitch
                    THEN (SELECT avg(length_ft) FROM routes.Routes r WHERE route_type ILIKE '%trad%'AND length_ft IS NOT NULL and pitches IS NULL AND length_ft < 230) -- avg single-pitch trad pitch length
                    WHEN route_type ILIKE '%trad%' AND length_ft IS NULL AND pitches IS NOT NULL -- trad multipitch
                    THEN (SELECT avg(length_ft/ pitches) FROM routes.Routes r WHERE route_type ILIKE '%trad%' AND length_ft IS NOT NULL and pitches IS NOT NULL) * pitches
                    WHEN route_type ILIKE '%sport%' AND length_ft IS NULL AND pitches IS NOT NULL -- sport single-pitch
                    THEN (SELECT avg(length_ft) FROM routes.Routes r WHERE route_type ILIKE '%sport%'AND length_ft IS NOT NULL and pitches IS NULL AND length_ft < 230) -- avg single-pitch sport pitch length
                    WHEN route_type ILIKE '%sport%' AND length_ft IS NULL AND pitches IS NOT NULL -- sport multipitch
                    THEN (SELECT avg(length_ft/ pitches) FROM routes.Routes r WHERE route_type ILIKE '%sport%' AND length_ft IS NOT NULL and pitches IS NOT NULL) * pitches
                    WHEN route_type ILIKE '%boulder%' AND length_ft IS NULL
                    THEN (SELECT avg(length_ft) FROM routes.Routes r WHERE route_type ILIKE '%boulder%' AND length_ft IS NOT NULL) -- boulder
                    ELSE (SELECT avg(length_ft) FROM routes.Routes r WHERE route_type ILIKE '%trad%'AND length_ft IS NOT NULL and pitches IS NULL AND length_ft < 230)
                END AS estimated_length
        FROM routes.Routes
        )
        """

def total_routes(conn, user_id=None):
    query = f"SELECT COUNT(DISTINCT route_id) FROM routes.Ticks t WHERE date::text ILIKE '%2024%' {add_user_filter(user_id)}"
    return conn.query(query).iloc[0,0]

def most_climbed_route(conn, user_id=None):
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
        FROM routes.Ticks t
        JOIN routes.Routes r ON t.route_id = r.id
        LEFT JOIN estimated_lengths el on el.id = t.route_id 
        WHERE EXTRACT(YEAR FROM t.date) = 2024
        {add_user_filter(user_id)}
        GROUP BY r.route_name, r.specific_location, r.yds_rating, r.hueco_rating, 
                 r.aid_rating, r.danger_rating, r.commitment_grade, el.estimated_length
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """
    result = conn.query(query)
    if result.empty:
        return None
    
    row = result.iloc[0]
    route_parts = row[0].split(' ~ ')
    if len(route_parts) == 2:
        route_name, rest = route_parts
        location_parts = rest.split('>')
        clean_location = location_parts[-1].strip() if '>' in rest else rest
        clean_route = f"{route_name} ~ {clean_location}"
        return (clean_route,) + tuple(row[1:])

def top_rated_routes(conn, user_id=None):
    query = f"""
        SELECT r.route_name, r.avg_stars
        FROM routes.Routes r
        JOIN routes.Ticks t ON t.route_id = r.id
        WHERE EXTRACT(YEAR FROM t.date) = 2024
        {add_user_filter(user_id)}
        ORDER BY r.avg_stars DESC
        LIMIT 5
    """
    return conn.query(query)

def days_climbed(conn, user_id=None):
    query = f"""
        SELECT COUNT(DISTINCT date)
        FROM routes.Ticks
        WHERE date::text ILIKE '%2024%'
        {add_user_filter(user_id)}
    """
    return conn.query(query).iloc[0,0]

def top_climbing_style(conn, user_id=None):
    query = """
        SELECT rat.tag_value, count(*)
        from analysis.RouteAnalysis ra
        JOIN analysis.RouteAnalysisTags rat on rat.analysis_id = ra.id
        JOIN analysis.RouteAnalysisTagsReasoning ratr on ratr.analysis_id = rat.analysis_id AND rat.tag_type = ratr.tag_type
        JOIN routes.Ticks t on t.route_id = ra.route_id 
        WHERE rat.tag_type = 'style' AND t.date ILIKE '%2024%'
        {add_user_filter(user_id)}
        GROUP BY rat.tag_value 
        ORDER BY count(*) desc
        LIMIT 1;
    """
    return conn.query(query).iloc[0,0]

def biggest_climbing_day(conn, user_id=None):
    query = f"""
        {estimated_lengths_cte}
        SELECT  t.date,
                STRING_AGG(
                    concat(r.route_name, ' ~ ', 
                          TRIM(SUBSTRING(r.specific_location FROM POSITION('>' IN r.specific_location) + 1)), 
                          ' - ', 
                          TRIM(NULLIF(CONCAT_WS(' ', r.yds_rating, r.hueco_rating, r.aid_rating, r.danger_rating, r.commitment_grade), '')), 
                          ' - ',
                          CAST(coalesce(r.length_ft,el.estimated_length) AS INT),' ft'
                    ), ' | '
                ) routes,
                CAST(ROUND(SUM(COALESCE(r.length_ft, el.estimated_length)),0) AS INTEGER) total_length,
                STRING_AGG(DISTINCT CONCAT(r.main_area, ', ', r.region), ' & ') areas
        FROM routes.Ticks t 
        JOIN routes.Routes r on r.id = t.route_id 
        LEFT JOIN estimated_lengths el on el.id = t.route_id 
        WHERE EXTRACT(YEAR FROM t.date) = 2024
        {add_user_filter(user_id)}
        GROUP BY t.date
        ORDER BY total_length desc
    LIMIT 1;
    """

    result = conn.query(query)
    
    if result.empty:
        return None
    
    row = result.iloc[0]
    
    return (
        row['date'],
        row['routes'],
        row['total_length'],
        row['areas']
    )

def top_grade(conn, level, user_id=None):
    query = f"""
    WITH grade_counts AS (
        SELECT
        	CASE
	        	WHEN r.route_type ILIKE '%Boulder%' THEN r.hueco_rating 
	        	WHEN r.route_type ILIKE '%Aid%' THEN r.aid_rating 
	        	ELSE r.yds_rating END AS grade,
	        	count(*)
        FROM routes.Routes r
        join routes.Ticks t on t.route_id = r.id
        WHERE date::text ILIKE '%2024%'
        {add_user_filter(user_id)}
        GROUP BY grade 
        ORDER BY count(*) desc
        )
    SELECT *
    FROM grade_counts
    WHERE grade IS NOT NULL
    """

    results = conn.query(query)

    grouped_grades = {}

    for _, row in results.iterrows():
        grade = row['grade']
        count = row['count']
        grouped_grade = get_grade_group(grade, level)
        if grouped_grade in grouped_grades:
            grouped_grades[grouped_grade] += count
        else:
            grouped_grades[grouped_grade] = count
    
    return max(grouped_grades.items(), key=itemgetter(1))[0]  

def states_climbed(conn, user_id=None):
    query = f"""
        SELECT region, count(distinct date) days_out, count(*) routes
        FROM routes.Routes r
        JOIN routes.Ticks t on t.route_id = r.id
        WHERE date::text ILIKE '%2024%'
        {add_user_filter(user_id)}
        GROUP BY region
        ORDER BY days_out desc;
    """
    result = conn.query(query)
    
    return result.values.tolist()


def sub_areas_climbed(conn, user_id=None):
    query = f"""
        SELECT sub_area , count(distinct date) days_out, count(*) routes
        FROM routes.Routes r
        JOIN routes.Ticks t on t.route_id = r.id
        WHERE date::text ILIKE '%2024%'
        {add_user_filter(user_id)}
        GROUP BY sub_area 
        ORDER BY days_out desc;
    """
    result = conn.query(query)
    
    return result.values.tolist()

def regions_climbed(conn, user_id=None):
    query = f"""
        SELECT count(distinct region)
        FROM routes.Routes r
        JOIN routes.Ticks t on t.route_id = r.id
        WHERE date::text ILIKE '%2024%'
        {add_user_filter(user_id)}
    """
    return conn.query(query).iloc[0,0]

def regions_sub_areas(conn, user_id=None):
    query = f"""
        SELECT count(distinct sub_area)
        FROM routes.Routes r
        JOIN routes.Ticks t on t.route_id = r.id
        WHERE date::text ILIKE '%2024%'
        {add_user_filter(user_id)}
    """
    return conn.query(query).iloc[0,0]

def top_tags(conn, tag_type, user_id=None):
    
    query = f"""
        WITH deduped_ticks AS(
            SELECT *,
            ROW_NUMBER() OVER (PARTITION BY route_id ORDER BY date DESC) as rn
            FROM routes.Ticks t
            WHERE date::text ILIKE '%2024%'
            {add_user_filter(user_id, 't')}
        )
        SELECT tav.mapped_type, tav.mapped_tag tag_value, count(*) as count
        FROM analysis.TagAnalysisView tav 
        JOIN deduped_ticks dt on dt.route_id = tav.route_id AND dt.rn = 1
        GROUP BY tav.mapped_type, tav.mapped_tag
        ORDER BY count DESC;
    """
    all_results = conn.query(query)
    filtered = all_results[all_results['mapped_type'].str.lower() == tag_type.lower()]

    filtered = filtered.rename(columns={
        'mapped_type': 'Type',
        'tag_value': 'Tag',
        'count': 'Count'
    })

    return filtered