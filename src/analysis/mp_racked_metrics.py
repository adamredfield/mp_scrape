import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.analysis.ai_analysis_helper_functions import get_grade_group
from operator import itemgetter
import pandas as pd
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
                    WHEN route_type ILIKE '%aid%' AND length_ft IS NULL AND pitches IS NOT NULL -- aid multipitch
                    THEN (SELECT avg(length_ft/ pitches) FROM routes.Routes r WHERE route_type ILIKE '%aid%' AND length_ft IS NOT NULL and pitches IS NOT NULL) * pitches
                    ELSE (SELECT avg(length_ft) FROM routes.Routes r WHERE route_type ILIKE '%trad%'AND length_ft IS NOT NULL and pitches IS NULL AND length_ft < 230)
                END AS estimated_length
        FROM routes.Routes
        )
        """

def get_deduped_ticks_cte(user_id=None, year='2024'):
    """
    Creates a CTE for deduped ticks with optional user and year filtering
    
    Args:
        user_id: Optional user ID to filter by
        year: Optional year to filter ticks by
    Returns:
        str: SQL CTE for deduped ticks
    """

    conditions = []
    
    if year:
        conditions.append(f"EXTRACT(YEAR FROM t.date) = {year}")
    
    if user_id:
        conditions.append(f"t.user_id = '{user_id}'")
    
    # Combine conditions with WHERE if any exist, otherwise omit WHERE
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    deduped_ticks_cte = f"""
        WITH deduped_ticks_base AS(
                SELECT *,
                ROW_NUMBER() OVER (PARTITION BY route_id ORDER BY date DESC) as rn
                FROM routes.Ticks t
                {where_clause}
            ),
        deduped_ticks AS (  
            SELECT * FROM deduped_ticks_base
            WHERE rn = 1
        )
    """
    return deduped_ticks_cte

def route_type_filter(route_types):
    if route_types:
        type_conditions = []
        for route_type in route_types:
            type_conditions.append(f"r.route_type ILIKE '%{route_type}%'")
        type_filter = f"AND ({' OR '.join(type_conditions)})"
    else:
        type_filter = ''
    return type_filter

def year_filter(year=None, year_range=None, use_where=True, table_alias='t'):
    """Generate SQL clause for year filtering
    
    Args:
        year: Optional single year to filter by
        year_range: Optional tuple of (start_year, end_year) to filter between
        use_where: If True, starts with WHERE, otherwise starts with AND (default True)
        table_alias: Table alias to use (default 't')
    
    Returns:
        str: SQL filter clause
    """
    if not year and not year_range:
        return ''
        
    prefix = 'WHERE' if use_where else 'AND'
    
    if year_range:
        start_year, end_year = year_range
        return f"{prefix} EXTRACT(YEAR FROM {table_alias}.date) BETWEEN {start_year} AND {end_year}"
    else:
        return f"{prefix} EXTRACT(YEAR FROM {table_alias}.date) = {year}"

def add_user_filter(user_id, table_alias='t'):
    """
    Add user filtering to a query
    Args:
        query: SQL query string (can be empty)
        user_id: User ID to filter by
        table_alias: Alias of the Ticks table in the query (default 't')
    """
    return f"AND {table_alias}.user_id = '{user_id}'"

def add_fa_name_filter(fa_name, use_where=False, table_alias='fa'):
    """
    Add first ascensionist filtering to a query
    Args:
        fa_name: First ascensionist name or partnership to filter by
        table_alias: Alias of the FA table in the query (default 'fa')
    Returns:
        SQL filter string
    """
    if not fa_name or fa_name == "All FAs":
        return ""

    prefix = 'WHERE' if use_where else 'AND'
    
    if " & " in str(fa_name):
        climber1, climber2 = fa_name.split(" & ")
        # Escape single quotes in names
        climber1 = climber1.replace("'", "''")
        climber2 = climber2.replace("'", "''")
        return f"""
        {prefix} {table_alias}.route_id IN (
            SELECT a1.route_id
            FROM analysis.fa a1
            JOIN analysis.fa a2 ON a1.route_id = a2.route_id 
            WHERE a1.fa_type = a2.fa_type
            AND a1.fa_name = '{climber1}'
            AND a2.fa_name = '{climber2}'
        )
        """
    fa_name = fa_name.replace("'", "''")
    return f"{prefix} {table_alias}.fa_name = '{fa_name}'"

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

def get_raw_grade_data(conn, user_id=None, tick_type=None):
    """Get raw grade data for debugging"""
    tick_filter = "AND t.type = 'Lead / Fell/Hung'" if tick_type == 'fall' else ""
    
    query = f"""
    SELECT 
        r.route_name,
        r.yds_rating as grade,
        r.route_type,
        t.type as tick_type,
        COUNT(*) as count
    FROM routes.Routes r
    JOIN routes.Ticks t ON r.id = t.route_id
    WHERE r.yds_rating = '5.0'
    {tick_filter}
    {add_user_filter(user_id)}
    GROUP BY r.route_name, r.yds_rating, r.route_type, t.type
    """
    return conn.query(query)

def get_grade_distribution(conn, route_types=None, level='base', year_start=None, year_end=None, user_id=None, tick_type='send'):
    """Get distribution of sends by grade with configurable grouping and route"""

    send_filter = """
    (
        r.route_type ILIKE '%Aid%' -- All aid climbs count as sends
        OR t.type = 'Solo'
        OR t.type != 'Lead / Fell/Hung'
    )
    """

    falls_filter = """
    (
        r.route_type NOT ILIKE '%Aid%'  -- Exclude aid climbs from falls
        AND t.type = 'Lead / Fell/Hung'  
        AND t.type != 'Solo'
    )
    """

    tick_filter = send_filter if tick_type == 'send' else falls_filter

    grade_column = """
    CASE 
        WHEN r.route_type ILIKE '%Boulder%' THEN r.hueco_rating 
        WHEN r.route_type ILIKE '%Aid%' THEN r.aid_rating 
    ELSE r.yds_rating END"""

    query = f"""
    WITH base_data AS (
        SELECT 
            {grade_column} AS grade,
            CASE 
                WHEN r.route_type ILIKE '%Alpine%' THEN 'Alpine'
                WHEN r.route_type ILIKE '%Aid%' THEN 'Aid'
                WHEN r.route_type ILIKE '%Trad%' THEN 'Trad'
                WHEN r.route_type ILIKE '%Sport%' THEN 'Sport'
                WHEN r.route_type ILIKE '%TR%' THEN 'TR'
                ELSE r.route_type 
            END AS route_type,
            1 as count  -- Count each climb once
        FROM routes.Routes r
        JOIN routes.Ticks t ON r.id = t.route_id
        WHERE {grade_column} IS NOT NULL
        AND {tick_filter}
        {route_type_filter(route_types)}
        {year_filter(year_range=(year_start, year_end), use_where=False)}
        {add_user_filter(user_id)}
    )
    SELECT 
        grade,
        route_type,
        SUM(count) as count,
        ROUND(SUM(count) * 100.0 / SUM(SUM(count)) OVER(), 2) as percentage
    FROM base_data
    GROUP BY grade, route_type
    ORDER BY grade DESC;
    """

    print(query)

    results =  conn.query(query)

    grouped_grades = {}

    for _, row in results.iterrows():
        grade = row['grade']
        count = row['count']
        route_type = row['route_type']
        grouped_grade = get_grade_group(grade, level)

        if grouped_grade not in grouped_grades:
            grouped_grades[grouped_grade] = {}

        if route_type not in grouped_grades[grouped_grade]:
            grouped_grades[grouped_grade][route_type] = 0

        grouped_grades[grouped_grade][route_type] += count

    total_count = sum(
        sum(type_counts.values()) 
        for type_counts in grouped_grades.values()
    )

    filtered_results = []
    for grade, type_counts in grouped_grades.items():
        for route_type, count in type_counts.items():
            filtered_results.append({
                'grade': grade,
                'count': count,
                'route_type': route_type,
                'percentage': round(count * 100.0 / total_count, 2)
            })
    
    filtered_results.sort(key=lambda x: (grade_sort_key(x['grade']), x['route_type']))
    
    return filtered_results


def grade_sort_key(grade):
    # Handle V grades
    if grade.startswith('V'):
        try:
            return (1000, int(grade[1:]))  # Put V grades at the top
        except (ValueError, IndexError):
            return (1000, 0)
    
    # Aid grades
    if grade.startswith('A') or grade.startswith('C'):
        try:
            return (2000, int(grade[1:]))  # Put aid grades at the end
        except (ValueError, IndexError):
            return (2000, 0)
    
    # YDS grades
    if grade.startswith('5.'):
        cleaned_grade = grade.replace('5.', '')
        
        if len(cleaned_grade) == 1:  # e.g. 5.9
            return (100, int(cleaned_grade), 0)
        
  # Grades with letters or modifiers
        base_part = ''
        modifier = ''
        
        # Get base grade
        for i, char in enumerate(cleaned_grade):
            if char.isdigit():
                base_part += char
            else:
                modifier = cleaned_grade[i:]
                break
        
        base_grade = int(base_part)
        
        # Order modifiers: -, a, b, c, d, +
        modifier_values = {
            '-': 1,
            'a': 2,
            'a/b': 2.5,
            'b': 3,
            'b/c': 4,
            '': 4,
            'c': 5,
            'c/d': 5.5,
            'd': 6,
            '+': 7
        }
        
        modifier_val = modifier_values.get(modifier.lower(), 0)
        return (100, base_grade, modifier_val)
    
    return (0, 0, 0)

def get_route_details(conn, grade, route_type, tick_type='send', user_id=None, grade_grain='base', year_start=None, year_end=None):
    """Get detailed route information for a specific grade and type"""

    route_type_case = """
    CASE 
        WHEN r.route_type ILIKE '%Alpine%' THEN 'Alpine'
        WHEN r.route_type ILIKE '%Aid%' THEN 'Aid'
        WHEN r.route_type ILIKE '%Trad%' THEN 'Trad'
        WHEN r.route_type ILIKE '%Sport%' THEN 'Sport'
        WHEN r.route_type ILIKE '%TR%' THEN 'TR'
        ELSE r.route_type 
    END
    """

    send_filter = """
    (
        r.route_type ILIKE '%Aid%'
        OR t.type = 'Solo'
        OR t.type != 'Lead / Fell/Hung'
    )
    """

    falls_filter = """
    (
        r.route_type NOT ILIKE '%Aid%'
        AND t.type = 'Lead / Fell/Hung'
        AND t.type != 'Solo'
    )
    """

    tick_filter = send_filter if tick_type == 'send' else falls_filter

    grade_column = """
    CASE 
        WHEN r.route_type ILIKE '%Boulder%' THEN r.hueco_rating 
        WHEN r.route_type ILIKE '%Aid%' THEN r.aid_rating 
    ELSE r.yds_rating END"""

    query = f"""
    WITH route_data AS (
        SELECT 
            r.route_name,
            r.main_area,
            r.route_type,
            {route_type_case} as calculated_type,
            t.date,
            t.type as tick_type,
            r.pitches,
            {grade_column} as original_grade,
            r.route_url
        FROM routes.Routes r
        JOIN routes.Ticks t ON r.id = t.route_id
        WHERE {tick_filter}
        AND {route_type_case} = :route_type
        AND {grade_column} IS NOT NULL
        {add_user_filter(user_id)}
        {year_filter(year_range=(year_start, year_end), use_where=False)}
    )
    SELECT * from route_data
    """
    
    params = {
        'route_type': route_type
    }
    
    results = conn.query(query, params=params)
    df = pd.DataFrame(results)

    if not df.empty:
        df['grouped_grade'] = df['original_grade'].fillna('').apply(
            lambda x: get_grade_group(str(x), grade_grain) if x else None
        )
        df = df[df['grouped_grade'] == grade]
        df = df.drop(['grouped_grade', 'calculated_type'], axis=1)
    return df

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
    {get_deduped_ticks_cte(user_id)}
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
    JOIN deduped_ticks t ON r.id = t.route_id
    WHERE r.num_votes >= 10
    {route_type_filter(route_types)}
    {year_filter(year, use_where=False)}
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

def get_bigwall_routes(conn, user_id=None, route_types=None):
    """Get all bigwall routes"""
    query = f'''
    {estimated_lengths_cte}
    SELECT
        t.date,
        r.route_name,
        TRIM(NULLIF(CONCAT_WS(' ', r.yds_rating, r.hueco_rating, r.aid_rating, r.danger_rating), '')) as grade,
        r.commitment_grade,
        CAST(COALESCE(r.length_ft, el.estimated_length) AS INTEGER) as length,
        CONCAT(r.main_area, ', ', r.region) as area,
        r.main_area,
        r.route_url,
        r.primary_photo_url,
        r.route_type,
        STRING_AGG(DISTINCT NULLIF(CASE 
            WHEN tav.mapped_type = 'style' AND tav.mapped_tag IS NOT NULL 
            THEN tav.mapped_tag 
        END, ''), ', ') as styles,
        STRING_AGG(DISTINCT NULLIF(CASE 
            WHEN tav.mapped_type = 'feature' AND tav.mapped_tag IS NOT NULL 
            THEN tav.mapped_tag 
        END, ''), ', ') as features,
        STRING_AGG(DISTINCT NULLIF(CASE 
            WHEN tav.mapped_type = 'descriptor' AND tav.mapped_tag IS NOT NULL 
            THEN tav.mapped_tag 
        END, ''), ', ') as descriptors,
        STRING_AGG(DISTINCT NULLIF(CASE 
            WHEN tav.mapped_type = 'rock_type' AND tav.mapped_tag IS NOT NULL 
            THEN tav.mapped_tag 
        END, ''), ', ') as rock_type
    FROM routes.Ticks t 
    JOIN routes.Routes r on r.id = t.route_id 
    LEFT JOIN estimated_lengths el on el.id = t.route_id 
    LEFT JOIN analysis.fa fa on fa.route_id = r.id
    LEFT JOIN analysis.taganalysisview tav on tav.route_id = r.id 
    {year_filter(year_range=(1999, 2025), use_where=True)}
    {add_user_filter(user_id)}
    {route_type_filter(route_types)}
    AND (
        r.length_ft >= 1000 
        OR el.estimated_length >= 1000 
        OR r.commitment_grade IN ('IV', 'V', 'VI', 'VII')
    )
    AND r.commitment_grade NOT IN ('I', 'II', 'III')
    GROUP BY 
    t.date,
    r.route_name,
    r.yds_rating,
    r.hueco_rating,
    r.aid_rating,
    r.danger_rating,
    r.commitment_grade,
    r.length_ft,
    el.estimated_length,
    r.main_area,
    r.region,
    r.route_url,
    r.primary_photo_url,
    r.route_type
    ORDER BY commitment_grade DESC, length DESC;
    '''
    return conn.query(query)

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
    {year_filter(year, use_where=False)}
    {add_user_filter(user_id)}
    GROUP BY year, r.{area_type}
    ORDER BY year DESC, length_climbed DESC;
    """
    return conn.query(query).itertuples(index=False)

def total_routes(conn, user_id=None, year_start=None, year_end=None):
    query = f"""
    SELECT
        date,
        COUNT(DISTINCT route_id)
    FROM routes.Ticks t
    {year_filter(year_range=(year_start, year_end), use_where=True)}
    {add_user_filter(user_id)}
    GROUP BY date
    """
    return conn.query(query)

def most_climbed_route(conn, user_id=None, year_start=None, year_end=None):
    query = f"""
        {estimated_lengths_cte},
        route_tags AS (
            SELECT 
                route_id,
                STRING_AGG(DISTINCT NULLIF(CASE 
                    WHEN mapped_type = 'style' THEN mapped_tag 
                    END, ''), ', ') as styles,
                STRING_AGG(DISTINCT NULLIF(CASE 
                    WHEN mapped_type = 'feature' THEN mapped_tag 
                    END, ''), ', ') as features,
                STRING_AGG(DISTINCT NULLIF(CASE 
                    WHEN mapped_type = 'descriptor' THEN mapped_tag 
                END, ''), ', ') as descriptors,
                STRING_AGG(DISTINCT NULLIF(CASE 
                    WHEN mapped_type = 'rock_type' THEN mapped_tag 
                END, ''), ', ') as rock_type
        FROM analysis.taganalysisview
        GROUP BY route_id
    )
    SELECT DISTINCT     
        r.route_name,
        r.specific_location,
        TRIM(NULLIF(CONCAT_WS(' ', r.yds_rating, r.hueco_rating, r.aid_rating, r.danger_rating, r.commitment_grade), '')) grade,
        CAST(COALESCE(r.length_ft, el.estimated_length) AS INTEGER) as length,
        array_agg(t.date ORDER BY t.date) as dates,
        array_agg(t.type ORDER BY t.date) as types,
        array_agg(t.note ORDER BY t.date) as notes,
        rt.styles,
        rt.features,
        rt.descriptors,
        rt.rock_type,
        min(t.date) first_climbed,
        COUNT(*) times_climbed,
        r.primary_photo_url,
        r.route_url
        FROM routes.Ticks t
        JOIN routes.Routes r ON t.route_id = r.id
        LEFT JOIN estimated_lengths el on el.id = t.route_id
		LEFT JOIN route_tags rt on rt.route_id = r.id	
        {year_filter(year_range=(year_start, year_end), use_where=True)}
        {add_user_filter(user_id)}
        GROUP BY r.route_name, r.specific_location, r.yds_rating, r.hueco_rating, 
                 r.aid_rating, r.danger_rating, r.commitment_grade, el.estimated_length, r.length_ft,
                 r.primary_photo_url, r.route_url, rt.styles, rt.features, rt.descriptors, rt.rock_type
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """
    print(query)
    result = conn.query(query)
    if result.empty:
        return None

    return result.iloc[0]

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
                STRING_AGG(DISTINCT CONCAT(r.main_area, ', ', r.region), ' & ') areas,
                STRING_AGG(r.route_url, ' | ') route_urls,
                STRING_AGG(r.primary_photo_url, ' | ') photo_urls
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
        row['areas'],
        row['route_urls'],
        row['photo_urls']
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
        {get_deduped_ticks_cte(user_id)}
        SELECT tav.mapped_type, tav.mapped_tag tag_value, count(*) as count
        FROM analysis.TagAnalysisView tav 
        JOIN deduped_ticks dt on dt.route_id = tav.route_id
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

def get_top_first_ascensionists(conn, user_id=None):
    f"""
    Get the most prolific first ascensionists
    Returns: List of (name, count) tuples
    """
    query = f"""
    {get_deduped_ticks_cte(user_id, year=None)}
    SELECT fa_name, COUNT(*) as fa_count
    FROM analysis.fa
    JOIN deduped_ticks t on t.route_id = fa.route_id
    WHERE fa_type IN ('FA', 'FFA', 'FCA')
    {add_user_filter(user_id)}
    GROUP BY fa_name
    ORDER BY fa_count desc
    LIMIT 10
    """
    result = conn.query(query)
    return result.values.tolist()

def get_first_ascensionist_by_decade(conn, name, user_id=None):
    """
    Get a first ascensionist's activity by decade
    Returns: List of (decade, count) tuples
    """
    query = f"""
    {get_deduped_ticks_cte(user_id, year=None)}
    SELECT 
        CONCAT(FLOOR(fa.year::int/10)*10, 's') as decade,
        COUNT(*) as fa_count
    FROM analysis.fa fa
    JOIN deduped_ticks t on t.route_id = fa.route_id
    WHERE fa_type IN ('FA', 'FFA', 'FCA')
    AND fa.year IS NOT null and length(fa.year::text) = 4
    {add_fa_name_filter(name, use_where=False)}
    {add_user_filter(user_id)}
    GROUP BY FLOOR(fa.year::int/10)*10
    ORDER BY decade
    """
    result = conn.query(query)
    return result.values.tolist()

def get_first_ascensionist_areas(conn, name, user_id=None):
    """
    Get the areas where a first ascensionist was most active
    Returns: List of (area_name, count) tuples
    """
    query = f"""
    {get_deduped_ticks_cte(user_id, year=None)}
    SELECT 
        r.main_area as area_name,
        COUNT(*) as fa_count
    FROM analysis.fa fa
    JOIN routes.routes r ON fa.route_id = r.id
    JOIN deduped_ticks t on t.route_id = fa.route_id
    WHERE fa_type IN ('FA', 'FFA', 'FCA')
    {add_fa_name_filter(name, use_where=False)}
    {add_user_filter(user_id)}
    GROUP BY r.main_area
    ORDER BY fa_count DESC
    LIMIT 10
    """
    result = conn.query(query)
    return result.values.tolist()

def get_first_ascensionist_grades(conn, name, user_id=None):
    """
    Get distribution of grades for a first ascensionist
    Returns: List of (grade, count) tuples
    """
    query = f"""
    {get_deduped_ticks_cte(user_id, year=None)}
    SELECT 
        r.yds_rating,
        COUNT(*) as route_count
    FROM analysis.fa fa
    JOIN routes.routes r ON fa.route_id = r.id
    JOIN deduped_ticks t on t.route_id = fa.route_id
    WHERE fa_type IN ('FA', 'FFA', 'FCA')
    {add_fa_name_filter(name, use_where=False)}
    {add_user_filter(user_id)}
    AND r.yds_rating IS NOT NULL
    GROUP BY r.yds_rating
    ORDER BY count(*) desc
    """
    result = conn.query(query)
    return result.values.tolist()

def get_collaborative_ascensionists(conn, name, user_id=None):
    """
    Find climbers who frequently did first ascents with given climber
    Returns: List of (partner_name, count) tuples
    """
    if name == "All FAs":
        # Query for most frequent partnerships overall
        query = f"""
        {get_deduped_ticks_cte(user_id, year=None)},
        partnerships AS (
            SELECT 
                LEAST(a1.fa_name, a2.fa_name) as climber1,
                GREATEST(a1.fa_name, a2.fa_name) as climber2,
                a1.route_id
            FROM analysis.fa a1
            JOIN analysis.fa a2 ON a1.route_id = a2.route_id 
                AND a1.fa_type = a2.fa_type
                AND a1.fa_name != a2.fa_name
            JOIN deduped_ticks t on t.route_id = a1.route_id
            WHERE a1.fa_type IN ('FA', 'FFA', 'FCA')
            {add_user_filter(user_id)}
        )
        SELECT 
            CONCAT(climber1, ' & ', climber2) as partnership,
            COUNT(DISTINCT route_id) as partnership_count
        FROM partnerships
        GROUP BY climber1, climber2
        HAVING COUNT(DISTINCT route_id) > 1
        ORDER BY partnership_count DESC
        LIMIT 10;
        """
    else:
        query = f"""
        WITH same_routes AS (
            SELECT DISTINCT a1.route_id, a2.fa_name as partner_name
            FROM analysis.fa a1
            JOIN analysis.fa a2 ON a1.route_id = a2.route_id 
                AND a1.fa_type = a2.fa_type
                AND a1.fa_name != a2.fa_name
            JOIN routes.ticks t on t.route_id = a1.route_id
            WHERE a1.fa_type IN ('FA', 'FFA', 'FCA')
            {add_fa_name_filter(name, use_where=False, table_alias='a1')}
            {add_user_filter(user_id)}
        )
        SELECT 
            partner_name,
            COUNT(*) as partnership_count
        FROM same_routes
        GROUP BY partner_name
        HAVING COUNT(*) > 1
        ORDER BY partnership_count DESC
        LIMIT 10;
        """
    result = conn.query(query)
    return result.values.tolist()


def get_fa_routes(conn, fa_name, user_id):
    """Get all routes where person was FA."""
    query = f"""
    {get_deduped_ticks_cte(user_id,year=None)}
    SELECT CONCAT_WS(' ~ ',
        r.route_name,
        CONCAT_WS(' > ',
            r.main_area
        ),
        TRIM(NULLIF(CONCAT_WS(' ',
            r.yds_rating,
            r.hueco_rating,
            r.aid_rating,
            r.danger_rating,
            r.commitment_grade
        ), ''))
) as route_display
    FROM analysis.fa
    JOIN routes.routes r on r.id = fa.route_id
    JOIN deduped_ticks t on t.route_id = fa.route_id
    {add_fa_name_filter(fa_name, use_where=True)}
    {add_user_filter(user_id, table_alias = 't')}
    ORDER BY r.avg_stars DESC
    """
    result = conn.query(query)
    return result.values.tolist()


def get_partnership_routes(conn, fa_name, partner_name, user_id):
    """
    Get routes where both climbers were FAs together.
    
    Args:
        conn: Database connection
        fa_name: Name of the primary FA
        partner_name: Name of the partner FA
        user_id: User ID for filtering
    
    Returns:
        List of routes done together
    """
    query = f"""
    {get_deduped_ticks_cte(user_id, year=None)}
    SELECT
        CONCAT_WS(' ~ ',
            r.route_name,
            CONCAT_WS(' > ',
                r.main_area
            ),
            TRIM(NULLIF(CONCAT_WS(' ',
                r.yds_rating,
                r.hueco_rating,
                r.aid_rating,
                r.danger_rating,
                r.commitment_grade
            ), ''))
        ) as route_display
    FROM routes.routes r
    JOIN analysis.fa fa1 ON r.id = fa1.route_id
    JOIN analysis.fa fa2 ON r.id = fa2.route_id
    JOIN deduped_ticks t on t.route_id = r.id
    WHERE fa1.fa_name = '{fa_name.replace("'", "''")}'
    AND fa2.fa_name = '{partner_name.replace("'", "''")}'
    AND fa1.fa_type = fa2.fa_type
    AND t.user_id = '{user_id}'
    ORDER BY r.avg_stars DESC
    """
    return conn.query(query).values.tolist()


def get_user_year_range(conn, user_id):
    """Get min and max years from user's tick data"""
    query = f"""
    SELECT 
        EXTRACT(YEAR FROM MIN(date))::integer as min_year,
        EXTRACT(YEAR FROM MAX(date))::integer as max_year
    FROM routes.Ticks
    WHERE user_id = '{user_id}'
    """
    result = conn.query(query)
    return result.iloc[0]['min_year'], result.iloc[0]['max_year']