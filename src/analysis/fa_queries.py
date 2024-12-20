def get_top_first_ascensionists(cursor, limit=10, type='FA'):
    """
    Get the most prolific first ascensionists
    Returns: List of (name, count) tuples
    """
    query = """
    SELECT name, COUNT(*) as fa_count
    FROM route_first_ascents
    WHERE type = %s
    GROUP BY name
    ORDER BY fa_count DESC
    LIMIT %s
    """
    cursor.execute(query, (type, limit))
    return cursor.fetchall()

def get_first_ascensionist_by_decade(cursor, name, type='FA'):
    """
    Get a first ascensionist's activity by decade
    Returns: List of (decade, count) tuples
    """
    query = """
    SELECT 
        CONCAT(FLOOR(year::int/10)*10, 's') as decade,
        COUNT(*) as fa_count
    FROM route_first_ascents
    WHERE name = %s 
    AND type = %s
    AND year IS NOT NULL
    GROUP BY FLOOR(year::int/10)*10
    ORDER BY decade
    """
    cursor.execute(query, (name, type))
    return cursor.fetchall()

def get_first_ascensionist_areas(cursor, name, limit=10):
    """
    Get the areas where a first ascensionist was most active
    Returns: List of (area_name, count) tuples
    """
    query = """
    SELECT 
        a.name as area_name,
        COUNT(*) as fa_count
    FROM route_first_ascents fa
    JOIN routes r ON fa.route_id = r.id
    JOIN areas a ON r.area_id = a.id
    WHERE fa.name = %s
    GROUP BY a.name
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
        r.grade,
        COUNT(*) as route_count
    FROM route_first_ascents fa
    JOIN routes r ON fa.route_id = r.id
    WHERE fa.name = %s
    AND fa.type = %s
    AND r.grade IS NOT NULL
    GROUP BY r.grade
    ORDER BY r.grade
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
        SELECT DISTINCT a1.route_id, a2.name as partner_name
        FROM route_first_ascents a1
        JOIN route_first_ascents a2 
        ON a1.route_id = a2.route_id 
        AND a1.type = a2.type
        AND a1.name != a2.name
        WHERE a1.name = %s
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