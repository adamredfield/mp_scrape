import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import openai
import sqlite3
from src.database.utils import create_connection
from typing import List
from datetime import datetime
import json

openai.api_key = os.getenv('OPENAI_API_KEY')

def get_routes_for_analysis(cursor, batch_size=10):
    """Get routes from database that haven't been analyzed yet"""
    query = '''
    SELECT 
        r.id,
        r.route_name,
        r.yds_rating,
        r.avg_stars,
        r.num_votes,
        r.region,
        r.main_area,
        r.sub_area,
        r.specific_location,
        r.route_type,
        r.length_ft,
        r.pitches,
        r.commitment_grade,
        r.fa,
        r.description,
        r.protection,
        GROUP_CONCAT(rc.comment, ' | ') as comments
    FROM Routes r
    LEFT JOIN RouteComments rc ON r.id = rc.route_id
    LEFT JOIN RouteAnalysis ra ON r.id = ra.route_id
    WHERE ra.id IS NULL  -- Only get routes not yet analyzed
    GROUP BY r.id
    LIMIT :batch_size
    '''
    cursor.execute(query, {'batch_size': batch_size})
    columns = [description[0] for description in cursor.description]
    results = cursor.fetchall()
    return [dict(zip(columns, row)) for row in results]

def construct_single_prompt(route):

    prompt_header = '''
    Analyze the following climbing route data and classify it into tags based on the provided JSON structure:

    Return a JSON object containing:
    1. "style": General climbing styles (e.g., crack, face, slab, overhang, chimney, etc.).
    2. "features": Specific route features (e.g., hand-crack, finger-crack, fist-crack, off-fingers, offwidth, dihedral, corner, seam, etc.).
    3. "descriptors": Characteristics that describe difficulty or experience (e.g., technical, burly, runout, polished, chossy, adventurous, scary, mellow, exciting, bigwall, etc.).
    4. "rock_type": Type of rock (e.g., granite, limestone, sandstone, gneiss, etc.). Do not include characteristics like "polished" here—only the rock type.

    Ensure that the tags reflect the key attributes of the climbing route. The final output must strictly adhere to this format:
    Return ONLY the JSON object, without any markdown formatting or code blocks.

    {
        "tags": {
            "style": [],
            "features": [],
            "descriptors": [],
            "rock_type": []
        }
    }
    '''

    route_details = [
        f"Name: {route['route_name']}",
        f"Grade: {route['yds_rating']}",
        f"Location: {route['region']} > {route['main_area']} > {route['sub_area']}",
        f"Type: {route['route_type']}",
    ]

    if route.get('length_ft'):
        route_details.append(f"Length: {route['length_ft']} ft")
    if route.get('pitches'):
        route_details.append(f"Pitches: {route['pitches']}")
    if route.get('description'):
        route_details.append(f"Description: {route['description']}")
    if route.get('protection'):
        route_details.append(f"Protection: {route['protection']}")
    if route.get('comments'):
        route_details.append(f"Comments: {route['comments']}")
    
    prompt = f"{prompt_header}\n\nRoute Data:\n" + "\n".join(route_details) + "\n"

    return prompt

def process_batch(batch: List[dict]) -> List[dict]:
    """Process a batch of routes"""

    results = []    
    for route in batch:
        messages = [
            {"role": "system",
            "content": (
                "You are an experienced and expert climber tasked with analyzing and classifiying climbing routes. "
                "The outputs will be used in a dashboard. "
                "This dashboard will allow climbers to visualize the types of routes they climb and to find other climbs in styles they enjoy. "
                "For each route, provide tags in the specified JSON structure."
                "Return ONLY the JSON object, without any markdown formatting or code blocks."
            )},
            {"role": "user", "content": construct_single_prompt(route)}
        ]
        try:    
            # Make API call
            response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500,
                temperature=0.3
            )

            # Process responses
            response_text = response.choices[0].message.content.strip()
            print(f"Response for {route['route_name']}: {response_text}")

            try:
                parsed_tags = json.loads(response_text)  # Make sure it's valid JSON
                result = {
                    "route_id": route["id"],
                    "tags": json.dumps(parsed_tags),
                    "insert_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                results.append(result)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON for route {route['route_name']}: {e}")
                continue

        except Exception as e:
            print(f"Error processing route {route['route_name']}: {e}")
            continue
    
    return results

def save_analysis_results(cursor, connection, results):
    """Save analysis results to database"""
    insert_sql = '''
    INSERT INTO RouteAnalysis (
        route_id,
        tags,
        insert_date
    ) VALUES (
        :route_id,
        json(:tags),
        :insert_date
    )
    '''
    
    try:
        cursor.executemany(insert_sql, results)
        connection.commit()
    except sqlite3.IntegrityError as e:
        print(f"Error inserting analysis results: {e}")

def main():
    try:    
        connection = create_connection()
        cursor = connection.cursor()

        while True:
            batch = get_routes_for_analysis(cursor)
            if not batch:
                print("No new routes to analyze")
                return
        
            print(f"Processing {len(batch)} routes...")
            results = process_batch(batch)
            
            if results:
                save_analysis_results(cursor, connection, results)
                print(f"Analyzed and saved results for {len(results)} routes")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    main()
