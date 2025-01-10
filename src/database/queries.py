import time
import psycopg2
from functools import wraps
from src.scraping.helper_functions import sanitize_route_data

def with_retry(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                    last_exception = e
                    if (("SSL connection has been closed" in str(e) or 
                         "cursor already closed" in str(e)) and 
                        attempt < max_retries - 1):
                        print(f"Database connection failed on attempt {attempt + 1}, retrying in {delay} seconds...")
                        
                        # Get new cursor if needed
                        if "cursor already closed" in str(e):
                            cursor = args[0]
                            if hasattr(cursor, 'connection'):
                                try:
                                    args = list(args)
                                    args[0] = cursor.connection.cursor()
                                    args = tuple(args)
                                except Exception as conn_err:
                                    print(f"Failed to get new cursor: {conn_err}")
                                    raise
                        
                        time.sleep(delay)
                        continue
                    raise
                except Exception as e:
                    # Don't retry other types of exceptions
                    raise
            raise last_exception
        return wrapper
    return decorator

@with_retry()
def check_routes_exists(cursor, route_ids):
    """Check if routes exist in database"""
    route_id_list = [int(id) for id in route_ids]
    placeholders = ','.join(['%s' for _ in route_id_list])
    query = f"SELECT id FROM routes.Routes WHERE id IN ({placeholders})"
    cursor.execute(query, tuple(route_id_list))
    results = {row[0] for row in cursor.fetchall()} # return set of route ids that exist
    print(f"Found existing routes: {results}")
    return results

@with_retry()
def insert_comments_batch(cursor, comments):  
    failed_comments = []
    try:
        print(f"Received {len(comments)} comments to insert")
        if not comments:
            print("No comments to insert")
            return 0, []
        
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
        RETURNING id
        """
        cursor.execute(comments_sql)
        inserted_count = cursor.rowcount
        print(f"Successfully inserted {inserted_count} comments")
        return inserted_count, [] 
        
    except Exception as e:
        print(f"Batch insert failed: {str(e)}")
        print("Falling back to individual inserts...")
        
        # Second attempt: individual inserts
        successful_count = 0
        for comment in comments:
            try:
                cursor.execute("""
                    INSERT INTO routes.RouteComments (
                        route_id, comment, comment_hash, insert_date
                    ) VALUES (
                        %(route_id)s, %(comment)s, 
                        encode(digest(%(comment)s, 'sha256'), 'hex'),
                        %(insert_date)s
                    )
                    ON CONFLICT (route_id, comment_hash) DO NOTHING
                    RETURNING id
                """, comment)
                cursor.connection.commit()
                
                if cursor.rowcount > 0:
                    successful_count += 1
                    
            except Exception as e:
                failed_comments.append({
                    'route_id': comment['route_id'],
                    'comment': comment['comment'][:50] + '...' if len(comment['comment']) > 50 else comment['comment'],
                    'error': str(e)
                })
                print(f"Failed to insert comment for route {comment['route_id']}: {str(e)}")
                continue
        
        print(f"\nIndividual inserts complete:")
        print(f"Successfully inserted: {successful_count} comments")
        if failed_comments:
            print(f"Failed to insert {len(failed_comments)} comments:")
            for comment in failed_comments:
                print(f"- Route {comment['route_id']}: {comment['comment']}")
        
        return successful_count, failed_comments

@with_retry()
def insert_ticks_batch(cursor, tick_data):
    failed_ticks = []

    for tick in tick_data:
        if tick['type'] is None:
            tick['type'] = ''
        if tick['pitches_climbed'] is None:
            tick['pitches_climbed'] = None 
        
    try:
        args_str = ','.join(
            cursor.mogrify(
                "(%(user_id)s, %(route_id)s, %(date)s, %(type)s, %(note)s, encode(digest(COALESCE(%(note)s, ''), 'sha256'), 'hex'),%(pitches_climbed)s, %(insert_date)s)",
                tick
            ).decode('utf-8')
            for tick in tick_data
        )
        tick_sql = f"""
            INSERT INTO routes.Ticks (user_id, route_id, date, type, note, note_hash, pitches_climbed, insert_date)
            VALUES {args_str}
            ON CONFLICT ON CONSTRAINT ticks_user_id_route_id_date_type_note_hash_key DO NOTHING
            RETURNING id
        """
        cursor.execute(tick_sql)
        inserted_count = cursor.rowcount
        print(f"Successfully inserted {inserted_count} ticks")
        return inserted_count, []
    except Exception as e:
        print(f"Batch insert failed: {str(e)}")
        print("Falling back to individual inserts...")
        
        # Second attempt: individual inserts
        successful_count = 0
        for tick in tick_data:
            try:
                cursor.execute("""
                    INSERT INTO routes.Ticks (
                        user_id, route_id, date, type, note, note_hash, 
                        pitches_climbed, insert_date
                    ) VALUES (
                        %(user_id)s, %(route_id)s, %(date)s, %(type)s, %(note)s, 
                        encode(digest(COALESCE(%(note)s, ''), 'sha256'), 'hex'),
                        %(pitches_climbed)s, %(insert_date)s
                    ) 
                    ON CONFLICT ON CONSTRAINT ticks_user_id_route_id_date_type_note_hash_key DO NOTHING
                    RETURNING id
                """, tick)
                cursor.connection.commit()
                
                if cursor.rowcount > 0:
                    successful_count += 1
                    
            except Exception as e:
                failed_ticks.append({
                    'user_id': tick['user_id'],
                    'route_id': tick['route_id'],
                    'date': tick['date'],
                    'error': str(e)
                })
                print(f"Failed to insert tick for route {tick['route_id']} by user {tick['user_id']}: {str(e)}")
                continue
        
        print(f"\nIndividual inserts complete:")
        print(f"Successfully inserted: {successful_count} ticks")
        if failed_ticks:
            print(f"Failed to insert {len(failed_ticks)} ticks:")
            for tick in failed_ticks:
                print(f"- User {tick['user_id']} Route {tick['route_id']} Date {tick['date']}")
        
        return successful_count, failed_ticks

@with_retry()
def insert_routes_batch(cursor, routes_data):
    failed_routes = []
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
        RETURNING id
        """ 
        cursor.execute(route_sql)
        inserted_count = cursor.rowcount
        print(f"Successfully inserted {inserted_count} routes")
        return inserted_count, []
        
    except Exception as e:
        print(f"Batch insert failed: {str(e)}")
        print("Falling back to individual inserts...")
        
        # Second try: Insert routes one at a time
        successful_count = 0
        for route in routes_data:
            try:
                cursor.execute("""
                    INSERT INTO routes.Routes (
                        id, route_name, route_url, yds_rating, hueco_rating, aid_rating, 
                        danger_rating, avg_stars, num_votes, region, main_area, sub_area, 
                        specific_location, route_type, length_ft, pitches, commitment_grade, 
                        fa, description, protection, primary_photo_url, insert_date
                    ) VALUES (
                        %(route_id)s, %(route_name)s, %(route_url)s, %(yds_rating)s, 
                        %(hueco_rating)s, %(aid_rating)s, %(danger_rating)s, %(avg_stars)s, 
                        %(num_votes)s, %(region)s, %(main_area)s, %(sub_area)s, 
                        %(specific_location)s, %(route_type)s, %(length_ft)s, %(pitches)s, 
                        %(commitment_grade)s, %(fa)s, %(description)s, %(protection)s, 
                        %(primary_photo_url)s, %(insert_date)s
                    ) ON CONFLICT (id) DO NOTHING
                    RETURNING id
                """, route)
                cursor.connection.commit()
                
                if cursor.rowcount > 0:
                    successful_count += 1
                    
            except Exception as e:
                failed_routes.append({
                    'route_id': route['route_id'],
                    'route_name': route['route_name'],
                    'error': str(e)
                })
                print(f"Failed to insert route {route['route_id']} - {route['route_name']}: {str(e)}")
                continue
        
        print(f"\nIndividual inserts complete:")
        print(f"Successfully inserted: {successful_count} routes")
        if failed_routes:
            print(f"Failed to insert {len(failed_routes)} routes:")
            for route in failed_routes:
                print(f"- Route {route['route_id']} ({route['route_name']})")
        
        return successful_count, failed_routes