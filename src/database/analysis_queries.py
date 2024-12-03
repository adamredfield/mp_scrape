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

def get_trad_grade_distribution(cursor):
    """Get distribution of trad sends by grade"""
    query = '''
    SELECT 
        r.yds_rating,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Ticks WHERE type NOT IN ('Lead / Fell/Hung')), 2) as percentage
    FROM Routes r
    JOIN Ticks t ON r.id = t.route_id
    WHERE r.yds_rating IS NOT NULL AND route_type = 'Trad'
    GROUP BY r.yds_rating
    ORDER BY COUNT(*) DESC;
    '''
    cursor.execute(query)
    return cursor.fetchall()

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