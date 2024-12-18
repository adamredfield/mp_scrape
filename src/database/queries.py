import time
import psycopg2
from functools import wraps

def with_retry(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except psycopg2.OperationalError as e:
                    last_exception = e
                    if "SSL connection has been closed" in str(e) and attempt < max_retries - 1:
                        print(f"Database connection failed on attempt {attempt + 1}, retrying in {delay} seconds...")
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
        RETURNING id
        """
        cursor.execute(comments_sql)
        inserted_count = cursor.rowcount
        print(f"Successfully inserted {inserted_count} comments")
        
    except Exception as e:
        print(f"Error inserting comments batch: {str(e)}")
        raise

@with_retry()
def insert_ticks_batch(cursor, tick_data):

    for tick in tick_data:
        if tick['type'] is None:
            tick['type'] = ''

    args_str = ','.join(
        cursor.mogrify(
            "(%(user_id)s, %(route_id)s, %(date)s, %(type)s, %(note)s, encode(digest(COALESCE(%(note)s, ''), 'sha256'), 'hex'), %(insert_date)s)",
            tick
        ).decode('utf-8')
        for tick in tick_data
    )
    tick_sql = f"""
        INSERT INTO routes.Ticks (user_id, route_id, date, type, note, note_hash, insert_date)
        VALUES {args_str}
        ON CONFLICT ON CONSTRAINT ticks_user_id_route_id_date_type_note_hash_key DO NOTHING
        RETURNING id
    """
    try:
        cursor.execute(tick_sql)
        inserted_count = cursor.rowcount
        print(f"Successfully inserted {inserted_count} ticks")
    except Exception as e:
        print(f"Error inserting tick batch: {str(e)}")
        raise

@with_retry()
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
        RETURNING id
        """ 
        cursor.execute(route_sql)
        inserted_count = cursor.rowcount
        print(f"Successfully inserted {inserted_count} routes")
        
    except Exception as e:
        print(f"Error inserting routes batch: {str(e)}")
        raise

