import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.database.utils import create_connection
from src.analysis.fa_parsing import parse_fa_data
from src.database import queries
from psycopg2.extras import DictCursor

def test_fa_processing():

    with create_connection() as conn:
        cursor = conn.cursor(cursor_factory=DictCursor)
    
        # Get sample of routes with FA data
        cursor.execute("""
            SELECT id, fa
            FROM routes.Routes
            WHERE fa IS NOT NULL
            AND id not in (SELECT route_id FROM analysis.fa);
        """)
        
        routes = cursor.fetchall()
        
        # Process each route
        print("\nProcessing First Ascents...")
        print("-" * 50)
        
        for route in routes:
            route_id = route['id']
            fa_string = route['fa']
            
            print(f"\nProcessing route {route_id}")
            print(f"FA string: {fa_string}")
            
            fas = parse_fa_data(fa_string)
            print("Parsed data:")
            for fa in fas:
                print(f"  Name: {fa['name']}, Type: {fa['type']}, Year: {fa['year']}")
                
                try:
                    cursor.execute(
                        queries.INSERT_FIRST_ASCENT,
                        (route_id, fa['name'], fa['type'], fa['year'])
                    )
                    print("  Successfully inserted into database")
                except Exception as e:
                    print(f"  Error inserting into database: {e}")
        
        # Commit changes and show some results
        conn.commit()
        
        print("\nSample of processed data:")
        print("-" * 50)
        
        cursor.execute("""
            SELECT r.route_name as route_name, fa.fa_name, fa.fa_type, fa.year
            FROM routes.fa fa
            JOIN routes.Routes r ON fa.route_id = r.id
            LIMIT 10;
        """)
        
        results = cursor.fetchall()
        for result in results:
            print(f"\nRoute: {result['route_name']}")
            print(f"Climber: {result['climber_name']}")
            print(f"Type: {result['ascent_type']}")
            print(f"Year: {result['year']}")
        
        cursor.close()
        conn.close()

if __name__ == "__main__":
    test_fa_processing()