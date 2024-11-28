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

def get_grade_distribution(cursor):
    """Get distribution of sends by grade"""
    query = '''
    SELECT 
        r.yds_rating,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Ticks WHERE type NOT IN ('Lead / Fell/Hung')), 2) as percentage
    FROM Routes r
    JOIN Ticks t ON r.id = t.route_id
    WHERE r.yds_rating IS NOT NULL
    GROUP BY r.yds_rating
    ORDER BY COUNT(*) DESC
    '''
    cursor.execute(query)
    return cursor.fetchall()

def get_most_climbed_areas(cursor):
    """Get most frequently climbed areas"""
    query = '''
    SELECT 
        r.location,
        COUNT(*) as visit_count,
        AVG(r.avg_stars) as avg_rating
    FROM Routes r
    JOIN Ticks t ON r.id = t.route_id
    GROUP BY r.location
    ORDER BY visit_count DESC
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
    '''
    cursor.execute(query)
    return cursor.fetchall()

def get_seasonal_patterns(cursor):
    """Analyze climbing patterns by month"""
    query = '''
    SELECT 
        strftime('%m', date) as month,
        COUNT(*) as climb_count,
        AVG(CASE 
            WHEN r.yds_rating LIKE '5.13%' THEN 13
            WHEN r.yds_rating LIKE '5.12%' THEN 12
            WHEN r.yds_rating LIKE '5.11%' THEN 11
            WHEN r.yds_rating LIKE '5.10%' THEN 10
            WHEN r.yds_rating LIKE '5.9%' THEN 9
            ELSE 8
        END) as avg_grade
    FROM Ticks t
    JOIN Routes r ON t.route_id = r.id
    GROUP BY month
    ORDER BY month
    '''
    cursor.execute(query)
    return cursor.fetchall()

def get_route_type_preferences(cursor):
    """Analyze preferences for different route types"""
    query = '''
    SELECT 
        r.type,
        COUNT(*) as count,
        AVG(r.avg_stars) as avg_rating,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Ticks), 2) as percentage
    FROM Routes r
    JOIN Ticks t ON r.id = t.route_id
    WHERE r.type IS NOT NULL
    GROUP BY r.type
    ORDER BY count DESC
    '''
    cursor.execute(query)
    return cursor.fetchall()        