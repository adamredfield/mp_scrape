import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.analysis.ai_analysis_helper_functions import construct_prompt, process_route_response, save_analysis_results
from src.database.utils import create_connection
import json
from pathlib import Path
import os
import time
from openai import OpenAI
from typing import Optional

def get_system_prompt():
    return (
        "You are an experienced climbing route analyst. Your task is to analyze routes and rank their core characteristics by importance.\n\n"
        "Tag Categories:\n"
        "1. styles: Identify the dominant / primary climbing styles that define the route.\n"
        "Note: Focus on overarching physical style(s) that are most representative of the route's character. (e.g., crack, chimney, face, overhang, slab, scramble, ridge)\n"
        "Note: This should NOT include climb types like trad/sport - only the physical style.\n"
        "- Rank styles by their prominence in the route (1 being most dominant)\n"
        "- Maximum of 3 styles, ranked by importance\n" 
        "2. features: Rank specific route features that are essential to the route's identity (e.g., hand-crack, finger-crack). \n"
        "Note: ideally these should act as sub-tags of the style. (e.g. style: crack, features: hand-crack, finger-crack, wide-crack, offwidth, corner). \n"
        "- Keep features specific but standardized (use 'hand-crack' not 'perfect hand crack')\n"
        "- Maximum of 4 features, ranked by importance\n\n"
        "3. descriptors: Rank key characteristics about difficulty or experience.\n"
        "- Focus on defining characteristics\n"
        "- Maximum of 4 descriptors, ranked by importance\n\n"
        "4. rock_type: Type of rock only (e.g., granite, limestone, sandstone, gneiss). Do not include characteristics here.\n\n"
        "Note: Only one rock type per route.\n"
        "Note: The rock type should be mainly derived from the route's location.\n"
        "CRITICAL: Return a valid JSON object exactly matching this format:\n"
        "{\n"
        '  "styles": {"ranked_tags": [{"rank": 1, "tag": "primary_style"}, {"rank": 2, "tag": "secondary_style"}]},\n'
        '  "features": {"ranked_tags": [{"rank": 1, "tag": "main_feature"}, {"rank": 2, "tag": "secondary_feature"}]},\n'
        '  "descriptors": {"ranked_tags": [{"rank": 1, "tag": "primary_descriptor"}, {"rank": 2, "tag": "secondary_descriptor"}]},\n'
        '  "rock_type": {"tag": "rock_type"}\n'
        "}\n\n"
        "- Rank 1 is always the most important/dominant characteristic\n"
        "- Include ONLY features explicitly mentioned or clearly implied in the route's data\n"
        "- Do not add any extra text or formatting\n"
        "- Use hyphens for compound terms (e.g., 'hand-crack' not 'hand crack')\n" 
        "- Ensure all JSON strings are properly escaped\n"
        "- Do not use line breaks within reasoning strings"
    )

def get_routes_batch(cursor, limit=1000):
    """Get a batch of routes that haven't been analyzed yet"""
    query = '''
    SELECT 
        r.id as route_id,
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
        STRING_AGG(rc.comment, ' | ') as comments
    FROM routes.Routes r
    LEFT JOIN routes.RouteComments rc ON r.id = rc.route_id
    LEFT JOIN analysis.RouteAnalysis_v2 ra ON r.id = ra.route_id
    WHERE ra.id IS NULL
    and r.avg_stars > 3
    GROUP BY r.id
    LIMIT %s
    '''
    cursor.execute(query, (limit,))
    columns = [description[0] for description in cursor.description]
    results = cursor.fetchall()
    
    routes = []
    for result in results:
        current_route_data = dict(zip(columns, result))
        
        combined_grade = ' '.join(filter(None, [
            current_route_data.get('yds_rating') or '',
            current_route_data.get('hueco_rating') or '',
            current_route_data.get('aid_rating') or '',
            current_route_data.get('danger_rating') or '',
            current_route_data.get('commitment_grade') or ''
        ])).strip() or None

        combined_location = ' > '.join(filter(None, [
            current_route_data.get('region') or '',
            current_route_data.get('main_area') or '',
            current_route_data.get('sub_area') or '',
            current_route_data.get('specific_location') or ''
        ])).strip() or None

        route_for_analysis = {
            'route_id': current_route_data['route_id'],
            'route_name': current_route_data['route_name'],
            'combined_grade': combined_grade,
            'avg_stars': current_route_data['avg_stars'],
            'num_votes': current_route_data['num_votes'],
            'location': combined_location,
            'route_type': current_route_data['route_type'],
            'fa': current_route_data['fa'],
            'description': current_route_data['description'],
            'protection': current_route_data['protection'],
            'comments': current_route_data['comments']
        }
        routes.append(route_for_analysis)
    
    return routes

def upload_batch_file(file_path: str) -> Optional[str]:
    """Upload the JSONL file to OpenAI and return the file ID"""
    try:
        client = OpenAI()
        with open(file_path, "rb") as file:
            batch_input_file = client.files.create(
                file=file,
                purpose="batch" 
            )
            print(f"File uploaded successfully. File ID: {batch_input_file.id}")
            return batch_input_file 
    except Exception as e:
        print(f"Error uploading file: {e}")
        return None

def create_batch_job(batch_input_file: object) -> Optional[str]:
    """Create a batch processing job and return the batch ID"""
    try:
        client = OpenAI()
        batch_input_file_id = batch_input_file.id
        response = client.batches.create(
            input_file_id=batch_input_file_id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={
                "description": "Mountain Project route analysis batch"
            }
        )
        print(f"Batch job created. Batch ID: {response.id}")
        return response.id
    except Exception as e:
        print(f"Error creating batch job: {e}")
        return None

def monitor_batch_job(batch_id: str, check_interval: int = 60):
    """Monitor the batch job status"""
    try:
        client = OpenAI()
        output_dir = Path("batch_results")
        output_dir.mkdir(exist_ok=True)
        while True:
            batch = client.batches.retrieve(batch_id)
            print(f"Status: {batch.status}")
            
            if batch.status in ["completed", "failed", "cancelled"]:
                if batch.output_file_id:
                    # Download and process results
                    file_response = client.files.content(batch.output_file_id)
                    results_file = output_dir / f"batch_results_{batch_id}.jsonl"
                    with open(results_file, 'w') as f:
                        f.write(file_response.text)
                    print(f"Results saved to: {results_file}")
                    
                    # Check for errors
                    if batch.error_file_id:
                        error_results = client.files.content(batch.error_file_id)
                        error_file = output_dir / f"batch_errors_{batch_id}.jsonl"
                        with open(error_file, 'w') as f:
                            f.write(error_results.text)
                        print(f"Errors saved to: {error_file}")
                return batch.status
            time.sleep(check_interval)
    except Exception as e:
        print(f"Error monitoring batch job: {e}")
        return "error"
    
def process_batch_results(batch_id: str):
    """Process the batch results and save to database using existing pipeline format"""
    try:
        results_file = Path("batch_results") / f"batch_results_{batch_id}.jsonl"

        if not results_file.exists():
            print(f"Error: Results file not found at {results_file}")
            return
        
        print(f"Processing results from: {results_file}")
        processed_count = 0
        failed_count = 0

        with create_connection() as conn:
            cursor = conn.cursor()
            
            with open(results_file, 'r') as f:
                for line in f:
                    try:
                        batch_result = json.loads(line)
                        
                        # Create the format expected by process_route_response
                        ai_response = {
                            'route_id': batch_result['custom_id'],
                            'tags': batch_result['response']['body']['choices'][0]['message']['content']
                        }
                        
                        # Process using existing pipeline function
                        processed_result = process_route_response(ai_response)
                        
                        if processed_result:
                            # Save to database using existing function
                            save_analysis_results(cursor, processed_result)
                            conn.commit()
                            processed_count += 1
                            print(f"Processed and saved analysis for route {processed_result['route_id']}")
                    except Exception as e:
                        failed_count += 1
                        print(f"Error processing route: {e}")
                        conn.rollback()
                        continue
            
            print(f"\nProcessing complete. Processed: {processed_count}, Failed: {failed_count}")
            
    except Exception as e:
        print(f"Error processing batch results: {e}")
        if 'conn' in locals():
            conn.rollback()

def main():
    print("Starting batch processing...")
    
    with create_connection() as conn:
        cursor = conn.cursor()
        print("Connected to database...")
        routes = get_routes_batch(cursor, limit=1050)
        print(f"Retrieved {len(routes)} routes from database")
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = Path("batch_files")
        output_dir.mkdir(exist_ok=True)
        filename = output_dir / f"routes_batch_{timestamp}.jsonl"
        
        with open(filename, 'w') as f:
            for route in routes:
                entry = {
                    "custom_id": f"{route['route_id']}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": "gpt-4o",
                        "messages": [
                            {"role": "system", "content": get_system_prompt()},
                            {"role": "user", "content": construct_prompt(route)}
                        ],
                        "max_tokens": 1000,
                        "temperature": 0.2
                    }
                }
                f.write(json.dumps(entry) + '\n')
        
        print(f"Created batch file with {len(routes)} routes")
        print(f"Output file: {filename}")

        batch_input_file = upload_batch_file(str(filename))
        if not batch_input_file:
                print("Failed to upload batch file. Exiting.")
                return
        
        batch_id = create_batch_job(batch_input_file)
        if batch_id:
            print("Starting batch job monitoring...")
            final_status = monitor_batch_job(batch_id)
            print(f"Batch processing completed with status: {final_status}")

            if final_status == "completed":
                print("Processing and saving results...")
                process_batch_results(batch_id)
            else:
                print(f"Batch job failed with status: {final_status}")
            

if __name__ == "__main__":
    main()