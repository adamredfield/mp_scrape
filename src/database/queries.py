import sqlite3

def insert_route(cursor, connection, route_data):
    # Insert into Routes table if the route_id is not already in the table (unique constraint)
    route_sql = '''
    INSERT OR IGNORE INTO Routes (
        id, route_name, route_url, yds_rating, hueco_rating, aid_rating, danger_rating, avg_stars, num_votes,
    region, main_area, sub_area, specific_location, route_type, length_ft, pitches, commitment_grade, fa, description, protection, primary_photo_url, insert_date
    ) VALUES (     
        :route_id, :route_name, :route_url, :yds_rating, :hueco_rating, :aid_rating, :danger_rating, :avg_stars, :num_votes,
        :region, :main_area, :sub_area, :specific_location, :route_type, :length_ft, :pitches, :commitment_grade, :fa, :description, :protection, :primary_photo_url, :insert_date)
    '''
    try:
        cursor.execute(route_sql, route_data)
        connection.commit()
    except sqlite3.IntegrityError as e:
        print(f"Error inserting {route_data['route_name']}: {e}")
    
def insert_comments(cursor, connection, comments):
    # Insert comments into RouteComments table
    if comments:
        comments_sql = '''
        INSERT OR IGNORE INTO RouteComments (
            route_id, comment
        ) VALUES (
            :route_id, :comment)
        '''
        try:    
            cursor.executemany(comments_sql, comments)
            connection.commit()
        except sqlite3.IntegrityError as e:
            print(f"Error inserting comments: {e}")

def insert_tick(cursor, connection, tick_data):
    tick_sql = '''
    INSERT OR IGNORE INTO Ticks (
        route_id, date, type, note
    ) VALUES (
        :route_id, :date, :type, :note
    )
    '''
    try:
        cursor.execute(tick_sql, tick_data)
        connection.commit()
    except sqlite3.IntegrityError as e:
        print(f"Error inserting {tick_data['route_name']}: {e}")

def check_route_exists(cursor, route_id):
    cursor.execute("SELECT id FROM Routes WHERE id = :route_id", {"route_id": route_id})
    existing_route = cursor.fetchone()
    return existing_route is not None   