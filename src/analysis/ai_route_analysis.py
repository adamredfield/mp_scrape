import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import openai
import sqlite3
from src.database.utils import create_connection
from typing import List

openai.api_key = os.getenv('OPENAI_API_KEY')

def get_routes_for_analysis(cursor, batch_size=1):
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
    prompt = "Analyze the following climbing routes. For each route, provide:\n"
    prompt += "- Tags: Key classifications such as 'dihedral,' 'crack-climb,' 'face-climb,' etc.\n"
    prompt += f"Name: {route['route_name']}\n"
    prompt += f"Grade: {route['yds_rating']}\n"
    prompt += f"Location: {route['region']} > {route['main_area']} > {route['sub_area']}\n"
    prompt += f"Type: {route['route_type']}"
    if route['length_ft']:
        prompt += f" | Length: {route['length_ft']} ft"
    if route['pitches']:
        prompt += f" | Pitches: {route['pitches']}"
    prompt += f"\nDescription: {route['description']}\n"
    if route['protection']:
        prompt += f"Protection: {route['protection']}\n"
    prompt += f"Comments: {route['comments']}\n[END]\n\n"
    return prompt

def process_batch(batch: List[dict]) -> List[dict]:
    """Process a batch of routes"""
    messages = [
        {"role": "system", "content": "You are a climbing route analyzer. For each route, provide only comma-separated tags."},
        {"role": "user", "content": "\n".join([construct_single_prompt(route) for route in batch])}
    ]

    # Make batch API call
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=500,
        temperature=0.3
    )

    # Process responses
    results = []
    responses = response.choices[0].message.content.strip().split("\n\n")

    for i, response in enumerate(responses):
        if i < len(batch):  # Safety check
            result = {
                "route_id": batch[i]["id"],
                "tags": response.strip()
            }
            results.append(result)
    
    return results


def save_analysis_results(cursor, connection, results):
    """Save analysis results to database"""
    insert_sql = '''
    INSERT INTO RouteAnalysis (
        route_id,
        tags
    ) VALUES (
        :route_id,
        :tags
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
