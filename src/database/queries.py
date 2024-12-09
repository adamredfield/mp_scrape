import psycopg2

def insert_route(cursor, connection, route_data):
    route_sql = '''
    INSERT INTO Routes (
        id, route_name, route_url, yds_rating, hueco_rating, aid_rating, danger_rating, 
        avg_stars, num_votes, region, main_area, sub_area, specific_location, route_type, 
        length_ft, pitches, commitment_grade, fa, description, protection, primary_photo_url, 
        insert_date
    ) VALUES (     
        %(route_id)s, %(route_name)s, %(route_url)s, %(yds_rating)s, %(hueco_rating)s, 
        %(aid_rating)s, %(danger_rating)s, %(avg_stars)s, %(num_votes)s, %(region)s, 
        %(main_area)s, %(sub_area)s, %(specific_location)s, %(route_type)s, %(length_ft)s, 
        %(pitches)s, %(commitment_grade)s, %(fa)s, %(description)s, %(protection)s, 
        %(primary_photo_url)s, %(insert_date)s
    )
    ON CONFLICT (id) DO NOTHING
    '''
    try:
        cursor.execute(route_sql, route_data)
        connection.commit()
    except Exception as e:
        print(f"Error inserting {route_data['route_name']}: {e}")
        connection.rollback()

def insert_comments(cursor, connection, comments):
    if comments:
        comments_sql = '''
        INSERT INTO RouteComments (
            route_id, comment, insert_date
        ) VALUES (
            %(route_id)s, %(comment)s, %(insert_date)s
        )
        ON CONFLICT (route_id, comment) DO NOTHING
        '''
        try:    
            cursor.executemany(comments_sql, comments)
            connection.commit()
        except Exception as e:
            print(f"Error inserting comments: {e}")
            connection.rollback()

def insert_tick(cursor, connection, tick_data):
    tick_sql = '''
    INSERT INTO Ticks (
        route_id, date, type, note, insert_date
    ) VALUES (
        %(route_id)s, %(date)s, %(type)s, %(note)s, %(insert_date)s
    )
    ON CONFLICT (route_id, date) DO NOTHING
    '''
    try:
        cursor.execute(tick_sql, tick_data)
        connection.commit()
    except Exception as e:
        print(f"Error inserting tick: {e}")
        connection.rollback()

def check_route_exists(cursor, route_id):
    """Check if route exists in PostgreSQL"""
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM Routes WHERE id = %s)",
        (route_id,)
    )
    return cursor.fetchone()[0]   