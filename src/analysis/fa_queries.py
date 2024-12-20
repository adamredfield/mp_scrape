def get_top_first_ascensionists(cursor, user_id, limit=10, type='FA'):
    """
    Get the most prolific first ascensionists
    Returns: List of (name, count) tuples
    """
    query = """
    SELECT fa_name, COUNT(*) as fa_count
    FROM analysis.fa
    WHERE fa_type = %s
    GROUP BY fa_name
    ORDER BY fa_count desc
    LIMIT %s
    """
    cursor.execute(query, (type, limit))
    return cursor.fetchall()

def get_first_ascensionist_by_decade(cursor, user_id,  name, type='FA'):
    """
    Get a first ascensionist's activity by decade
    Returns: List of (decade, count) tuples
    """
    query = """
    SELECT 
        CONCAT(FLOOR(year::int/10)*10, 's') as decade,
        COUNT(*) as fa_count
    FROM analysis.fa
    WHERE fa_name = %s 
    WHERE fa_type = %s
    WHERE year IS NOT null and length(year::text) = 4
    GROUP BY FLOOR(year::int/10)*10
    ORDER BY decade
    """
    cursor.execute(query, (name, user_id,  type))
    return cursor.fetchall()

def get_first_ascensionist_areas(cursor, name, limit=10):
    """
    Get the areas where a first ascensionist was most active
    Returns: List of (area_name, count) tuples
    """
    query = """
    SELECT 
        r.main_area as area_name,
        COUNT(*) as fa_count
    FROM analysis.fa fa
    JOIN routes.routes r ON fa.route_id = r.id
    WHERE fa.fa_name = 'Layton Kor'
    GROUP BY r.main_area
    ORDER BY fa_count DESC
    LIMIT %s
    """
    cursor.execute(query, (name, limit))
    return cursor.fetchall()

def get_first_ascensionist_grades(cursor, name, type='FA'):
    """
    Get distribution of grades for a first ascensionist
    Returns: List of (grade, count) tuples
    """
    query = """
    SELECT 
        r.yds_rating,
        COUNT(*) as route_count
    FROM analysis.fa fa
    JOIN routes.routes r ON fa.route_id = r.id
    WHERE fa.fa_name = %s
    --AND fa.type = %s
    AND r.yds_rating IS NOT NULL
    GROUP BY r.yds_rating
    ORDER BY count(*) desc
    """
    cursor.execute(query, (name, type))
    return cursor.fetchall()

def get_collaborative_ascensionists(cursor, name, limit=10):
    """
    Find climbers who frequently did first ascents with given climber
    Returns: List of (partner_name, count) tuples
    """
    query = """
    WITH same_routes AS (
        SELECT DISTINCT a1.route_id, a2.fa_name as partner_name
        FROM analysis.fa a1
        JOIN analysis.fa a2 
        ON a1.route_id = a2.route_id 
        AND a1.fa_type = a2.fa_type
        AND a1.fa_name != a2.fa_name
        WHERE a1.fa_name = 'Royal Robbins'
    )
    SELECT 
        partner_name,
        COUNT(*) as partnership_count
    FROM same_routes
    GROUP BY partner_name
    ORDER BY partnership_count DESC
    LIMIT %s
    """
    cursor.execute(query, (name, limit))
    return cursor.fetchall() 