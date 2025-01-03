import os
import sys
import streamlit as st
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.analysis.filters_ctes import add_user_filter, route_type_filter, year_filter, estimated_lengths_cte, get_deduped_ticks_cte
from operator import itemgetter
import pandas as pd

def get_grade_group(grade:str, level:str = 'base') -> str:

    if grade.startswith('V'):
        return grade
    if grade.startswith('A') or grade.startswith('C'):
        return grade 

    if grade.startswith('5.'):
        grade_prefix = '5.'
        cleaned_grade = grade.replace('5.', '')
    else:
        return grade
    
    if len(cleaned_grade) == 1: # e.g. 5.9
        base_grade = cleaned_grade
        grade_suffix = None
    elif cleaned_grade[1].isdigit(): # e.g. 5.10 or 5.10a
        base_grade = cleaned_grade[:2]
        if len(cleaned_grade) == 3:
            grade_suffix = cleaned_grade[2]
        else:
            grade_suffix = None
    else: # e.g. 5.9+
        base_grade = cleaned_grade[0]
        grade_suffix = cleaned_grade[1]
    
    if level == 'base':
        return f'{grade_prefix}{base_grade}'
    elif level == 'granular':
        if grade_suffix in ['a', 'b', '-']:
            return f'{grade_prefix}{base_grade}-'
        if grade_suffix in ['c', 'd', '+']:
            return f'{grade_prefix}{base_grade}+'
        else:
            return f'{grade_prefix}{base_grade}'
    else:
        return grade 


def get_grade_distribution(conn, route_types=None, level='base', year_start=None, year_end=None, user_id=None, tick_type='send', tick_types=None):
    """Get distribution of sends by grade with configurable grouping and route"""

    if tick_type == 'send':
        if not tick_types:
            tick_types = [
                'Lead / Pinkpoint',
                'Lead / Onsight',
                'Lead / Redpoint',
                'Lead / Flash',
                'Solo'
        ]
        send_conditions = [f"t.type = '{t}'" for t in tick_types]
        tick_filter = f"({' OR '.join(send_conditions)})"
    else:
        tick_filter = """
        (
            r.route_type NOT ILIKE '%Aid%'  -- Exclude aid climbs from falls
            AND t.type = 'Lead / Fell/Hung'  
            AND t.type != 'Solo'
        )
        """

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

    results =  conn.query(query)

    if results.empty:
        if tick_type == 'send':
            st.write("")
            st.write("")
            st.write(f"No sends found for {tick_types}")
        return[]

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
        if grade == 'V-easy':
            return (1000, -1, 2)  # Sort below V0
        
        grade = grade[1:]  # Remove 'V' prefix
        base_part = ''
        modifier = ''
        
        # Handle range grades (V0-1, V2-3, etc) and modifiers
        if '-' in grade:
            parts = grade.split('-')
            try:
                # Handle ranges like V0-1
                if len(parts) == 2 and parts[1].isdigit():
                    base_grade = int(parts[0])
                    return (1000, base_grade, 2.5)
                # Handle minus modifier (V1-)
                elif parts[1] == '':
                    base_grade = int(parts[0])
                    return (1000, base_grade, 1)
            except ValueError:
                return (1000, 0, 0)
        
        # Handle plus grades and plain grades
        if '+' in grade:
            try:
                base_grade = int(grade.replace('+', ''))
                return (1000, base_grade, 3)
            except ValueError:
                return (1000, 0, 0)
        
        # Plain V grade
        try:
            base_grade = int(grade)
            return (1000, base_grade, 2)
        except ValueError:
            return (1000, 0, 0)
        
    if grade.startswith('A') or grade.startswith('C'):
        base_part = ''
        modifier = ''
        
        # Get the prefix (A or C)
        prefix = grade[0]
        
        # Skip the A or C prefix
        grade = grade[1:]
        
        # Extract base grade and modifier
        for i, char in enumerate(grade):
            if char.isdigit():
                base_part += char
            else:
                modifier = grade[i:]
                break
        
        try:
            base_grade = int(base_part)
            
            # Aid grade modifier values
            aid_modifier_values = {
                '-': 1, 
                '': 2,
                '+': 3 
            }
            
            modifier_val = aid_modifier_values.get(modifier, 2)
            
            # A harder than C
            prefix_value = 3000 if prefix == 'A' else 2000
            
            return (prefix_value, base_grade, modifier_val)
        except ValueError:
            return (2000, 0, 0)
        
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

def get_route_details(conn, grade, clicked_type=None,filtered_types=None, tick_type='send', tick_types=None, user_id=None, grade_grain='base', year_start=None, year_end=None):
    """Get detailed route information for a specific grade and type"""

    if tick_type == 'send':
        if not tick_types:
            tick_types = [
                'Lead / Pinkpoint',
                'Lead / Onsight',
                'Lead / Redpoint',
                'Lead / Flash',
                'Solo'
            ]
        send_conditions = [f"t.type = '{t}'" for t in tick_types]
        tick_filter = f"({' OR '.join(send_conditions)})"
    else:
        tick_filter = """
        (
            r.route_type NOT ILIKE '%Aid%'
            AND t.type = 'Lead / Fell/Hung'
            AND t.type != 'Solo'
        )
        """

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
            CASE 
                WHEN r.route_type ILIKE '%Alpine%' THEN 'Alpine'
                WHEN r.route_type ILIKE '%Aid%' THEN 'Aid'
                WHEN r.route_type ILIKE '%Trad%' THEN 'Trad'
                WHEN r.route_type ILIKE '%Sport%' THEN 'Sport'
                WHEN r.route_type ILIKE '%TR%' THEN 'TR'
                ELSE r.route_type 
            END AS route_type_calc,
            t.date,
            t.type as tick_type,
            r.pitches,
            {grade_column} as original_grade,
            r.route_url
        FROM routes.Routes r
        JOIN routes.Ticks t ON r.id = t.route_id
        WHERE {tick_filter}
        AND {grade_column} IS NOT NULL
        {route_type_filter(filtered_types)}
        {add_user_filter(user_id)}
        {year_filter(year_range=(year_start, year_end), use_where=False)}
    )
    SELECT * from route_data
    WHERE route_type_calc = :clicked_type
    """

    params = {
        'clicked_type': clicked_type
    }
    
    results = conn.query(query, params=params)
    df = pd.DataFrame(results)

    if not df.empty:
        df['grouped_grade'] = df['original_grade'].fillna('').apply(
            lambda x: get_grade_group(str(x), grade_grain) if x else None
        )
        df = df[df['grouped_grade'] == grade]
        df = df.drop(['grouped_grade'], axis=1)
    return df

def get_highest_rated_climbs(conn, selected_styles=None, route_types=None, year_start=None, year_end=None, tag_type=None, user_id=None):

    """Get highest rated climbs"""
    style_filter = ""
    if selected_styles:
        style_conditions = [
            f"(',' || STRING_AGG(tav.mapped_tag, ',') || ',') ILIKE '%,{style},%'"
            for style in selected_styles
        ]
        style_filter = f"HAVING {' AND '.join(style_conditions)}"

    query = f"""
    {get_deduped_ticks_cte(user_id=user_id, year_start=year_start, year_end=year_end)}
    SELECT 
        DISTINCT r.route_name,
        r.main_area,
        r.specific_location,
        TRIM(NULLIF(CONCAT_WS(' ', 
            r.yds_rating,
            r.hueco_rating,
            r.aid_rating,
            r.danger_rating,
            r.commitment_grade), '')) as grade,
        r.avg_stars,
        r.num_votes,
        STRING_AGG(tav.mapped_tag, ', ') as styles,
        r.primary_photo_url,
        r.route_url
    FROM routes.Routes r
    LEFT JOIN analysis.TagAnalysisView tav on r.id = tav.route_id 
        AND tav.mapped_type = '{tag_type}'
    JOIN deduped_ticks t ON r.id = t.route_id
    WHERE r.num_votes >= 15
    {route_type_filter(route_types)}
    {year_filter(year_range=(year_start, year_end), use_where=False)}
    {add_user_filter(user_id)}
    GROUP BY r.route_name, r.main_area, r.specific_location, r.yds_rating, r.hueco_rating, 
             r.aid_rating, r.danger_rating, r.commitment_grade, r.avg_stars, r.num_votes,
             r.primary_photo_url, r.route_url
    {style_filter}
    ORDER BY r.avg_stars DESC, num_votes DESC
    LIMIT 20
    """
    print(query)
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

def get_length_climbed(conn, area_type="main_area", user_id=None, year_start=None, year_end=None):
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
    {year_filter(year_range=(year_start, year_end), use_where=False)}
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
    result = conn.query(query)
    if result.empty:
        return None

    return result.iloc[0]

def days_climbed(conn, user_id=None):
    query = f"""
        SELECT COUNT(DISTINCT date)
        FROM routes.Ticks
        WHERE date::text ILIKE '%2024%'
        {add_user_filter(user_id)}
    """
    return conn.query(query).iloc[0,0]

def biggest_climbing_day(conn, user_id=None, year_start=None, year_end=None):

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
                STRING_AGG(COALESCE(r.commitment_grade, 'None'), ' | ') commitment_grades,
                CAST(ROUND(SUM(COALESCE(r.length_ft, el.estimated_length)),0) AS INTEGER) total_length,
                STRING_AGG(DISTINCT CONCAT(r.main_area, ', ', r.region), ' & ') areas,
                STRING_AGG(r.route_url, ' | ') route_urls,
                STRING_AGG(r.primary_photo_url, ' | ') photo_urls
        FROM routes.Ticks t 
        JOIN routes.Routes r on r.id = t.route_id 
        LEFT JOIN estimated_lengths el on el.id = t.route_id 
        {year_filter(year_range=(year_start, year_end), use_where=True)}
        {add_user_filter(user_id)}
        GROUP BY t.date
        ORDER BY total_length desc
    LIMIT 10;
    """

    result = conn.query(query)
    
    if result.empty:
        return None

    return [
        (
            row['date'],
            row['routes'],
            row['commitment_grades'],
            row['total_length'],
            row['areas'],
            row['route_urls'],
            row['photo_urls']
        )
        for _, row in result.iterrows()
    ]

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

def states_climbed(conn, user_id=None, year_start=None, year_end=None):
    query = f"""
        SELECT region, count(distinct date) days_out, count(*) routes
        FROM routes.Routes r
        JOIN routes.Ticks t on t.route_id = r.id
        {year_filter(year_range=(year_start, year_end), use_where=True)}
        {add_user_filter(user_id)}
        GROUP BY region
        ORDER BY days_out desc;
    """
    result = conn.query(query)
    
    return result.values.tolist()

def sub_areas_climbed(conn, user_id=None, year_start=None, year_end=None):
    query = f"""
        SELECT sub_area , count(distinct date) days_out, count(*) routes
        FROM routes.Routes r
        JOIN routes.Ticks t on t.route_id = r.id
        {year_filter(year_range=(year_start, year_end), use_where=True)}
        {add_user_filter(user_id)}
        GROUP BY sub_area 
        ORDER BY days_out desc
        Limit 10;
    """
    result = conn.query(query)
    
    return result.values.tolist()

def regions_climbed(conn, user_id=None, year_start=None, year_end=None):
    query = f"""
        SELECT count(distinct region)
        FROM routes.Routes r
        JOIN routes.Ticks t on t.route_id = r.id
        {year_filter(year_range=(year_start, year_end), use_where=True)}
        {add_user_filter(user_id)}
        Limit 10
    """
    return conn.query(query).iloc[0,0]

def regions_sub_areas(conn, user_id=None, year_start=None, year_end=None):
    query = f"""
        SELECT count(distinct sub_area)
        FROM routes.Routes r
        JOIN routes.Ticks t on t.route_id = r.id
        {year_filter(year_range=(year_start, year_end), use_where=True)}
        {add_user_filter(user_id)}
    """
    return conn.query(query).iloc[0,0]

def top_tags(conn, tag_type, user_id=None, year_start=None, year_end=None):
    
    query = f"""
        {get_deduped_ticks_cte(user_id=user_id, year_start=year_start, year_end=year_end)}
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

def get_classics_count(conn, user_id=None, year_start=None, year_end=None, route_types=None, tag_type=None, selected_styles=None):
    style_filter = ""
    if selected_styles:
        style_conditions = [
            f"(',' || STRING_AGG(tav.mapped_tag, ',') || ',') ILIKE '%,{style},%'"
            for style in selected_styles
        ]
        style_filter = f"HAVING {' AND '.join(style_conditions)}"
    query = f"""
        SELECT DISTINCT r.id
        FROM routes.Ticks t
        JOIN routes.Routes r ON t.route_id = r.id
        LEFT JOIN analysis.TagAnalysisView tav on r.id = tav.route_id 
            AND tav.mapped_type = '{tag_type}'
        {year_filter(year_range=(year_start, year_end), use_where=True)}
        {add_user_filter(user_id)}
        {route_type_filter(route_types)}
        AND r.avg_stars >= 3.5
        AND r.num_votes >= 15
        GROUP BY r.id
        {style_filter};
    """
    return len(conn.query(query))