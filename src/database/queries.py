def check_routes_exists(cursor, route_ids):
    """Check if routes exist in database"""
    route_id_list = ','.join(['%s'] * len(route_ids))
    cursor.execute(
        f"SELECT id FROM routes.Routes WHERE id IN ({route_id_list})",
        tuple(route_ids)
    )
    return {row[0] for row in cursor.fetchall()} # return set of route ids that exist

def insert_comments_batch(cursor, comments):  
    try:
        args_str = ','.join(
cursor.mogrify(
                "(%(route_id)s, %(comment)s, encode(digest(%(comment)s, 'sha256'), 'hex'), %(insert_date)s)",
                comment
            ).decode('utf-8')
            for comment in comments
        )
        comments_sql = f"""
        INSERT INTO routes.RouteComments (
            route_id, comment, comment_hash, insert_date
        ) VALUES {args_str}
        ON CONFLICT (route_id, comment_hash) DO NOTHING
        """
        cursor.execute(comments_sql)
        print(f"Successfully inserted {len(comments)} comments")
        
    except Exception as e:
        print(f"Error inserting comments batch: {str(e)}")
        raise

def insert_ticks_batch(cursor, tick_data):
    args_str = ','.join(
        cursor.mogrify(
            "(%(user_id)s, %(route_id)s, %(date)s, %(type)s, %(note)s, %(insert_date)s)",
            tick
        ).decode('utf-8') 
        for tick in tick_data
    )
    tick_sql = f"""
        INSERT INTO routes.Ticks (user_id, route_id, date, type, note, insert_date)
        VALUES {args_str}
        ON CONFLICT (user_id, route_id, date) DO NOTHING
    """
    try:
        cursor.execute(tick_sql)
        print(f"Successfully inserted {len(tick_data)} ticks")
    except Exception as e:
        print(f"Error inserting tick batch: {str(e)}")
        raise

def insert_routes_batch(cursor, routes_data):
    try:
        args_str = ','.join(
            cursor.mogrify(
                """(
                    %(route_id)s, %(route_name)s, %(route_url)s, %(yds_rating)s, 
                    %(hueco_rating)s, %(aid_rating)s, %(danger_rating)s, %(avg_stars)s, 
                    %(num_votes)s, %(region)s, %(main_area)s, %(sub_area)s, 
                    %(specific_location)s, %(route_type)s, %(length_ft)s, %(pitches)s, 
                    %(commitment_grade)s, %(fa)s, %(description)s, %(protection)s, 
                    %(primary_photo_url)s, %(insert_date)s
                )""",
                route
            ).decode('utf-8')
            for route in routes_data
        )

        route_sql = f"""
        INSERT INTO routes.Routes (
            id, route_name, route_url, yds_rating, hueco_rating, aid_rating, 
            danger_rating, avg_stars, num_votes, region, main_area, sub_area, 
            specific_location, route_type, length_ft, pitches, commitment_grade, 
            fa, description, protection, primary_photo_url, insert_date
        ) VALUES {args_str}
        ON CONFLICT (id) DO NOTHING
        """ 
        cursor.execute(route_sql)
        print(f"Successfully inserted {len(routes_data)} routes")
        
    except Exception as e:
        print(f"Error inserting routes batch: {str(e)}")
        raise

