#!/usr/bin/env python3
"""
Route Semantic Search
Search climbing routes using natural language queries via embeddings
"""

import os
import sys
import json
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.database.utils import create_connection
from src.vectordb.embedding_functions import generate_embedding

def search_routes(query, limit=10, filters=None, similarity_threshold=0.35):
    """
    Search routes using semantic similarity
    
    Args:
        query (str): Natural language search query
        limit (int): Number of results to return
        filters (dict): Optional filters (grade, area, stars, etc.)
        similarity_threshold (float): Minimum similarity score (0.0-1.0)
    
    Returns:
        List of route matches with similarity scores
    """
    
    print(f"🔍 Searching for: '{query}'")
    query_embedding = generate_embedding(query, model="text-embedding-3-small")
    
    if not query_embedding:
        print("❌ Failed to generate embedding for query")
        return []
    
    with create_connection() as connection:
        cursor = connection.cursor()
        
        # Build the search query with similarity threshold
        base_query = """
        WITH similarity_scores AS (
            SELECT 
                re.route_id,
                re.content_source,
                re.metadata,
                1 - (re.embedding <=> %s::vector) as similarity_score
            FROM vectors.route_embeddings re
            WHERE re.content_type = 'full_route'
                AND 1 - (re.embedding <=> %s::vector) >= %s
        )
        SELECT 
            ss.route_id,
            r.route_name,
            r.yds_rating,
            r.hueco_rating,
            r.aid_rating,
            r.danger_rating,
            r.commitment_grade,
            r.route_type,
            r.region,
            r.main_area,
            r.sub_area,
            r.specific_location,
            r.avg_stars,
            r.num_votes,
            r.length_ft,
            r.pitches,
            r.fa,
            r.description,
            r.protection,
            ss.similarity_score,
            ss.content_source,
            ss.metadata
        FROM similarity_scores ss
        JOIN routes.Routes r ON r.id = ss.route_id
        """
        
        # Add filters if provided
        where_conditions = []
        params = [query_embedding, query_embedding, similarity_threshold]  # For the embedding comparisons and threshold
        
        if filters:
            # Star rating filter
            if filters.get('min_stars'):
                where_conditions.append("r.avg_stars >= %s")
                params.append(filters['min_stars'])
            
            # Location filters
            if filters.get('region'):
                where_conditions.append("r.region ILIKE %s")
                params.append(f"%{filters['region']}%")
                
            if filters.get('area'):
                where_conditions.append("r.main_area ILIKE %s")
                params.append(f"%{filters['area']}%")
                
            # Route type filter
            if filters.get('route_type'):
                where_conditions.append("r.route_type ILIKE %s")
                params.append(f"%{filters['route_type']}%")
            
            # Grade filters
            if filters.get('min_grade') or filters.get('max_grade'):
                # This is complex - for now, simple string comparison
                if filters.get('min_grade'):
                    where_conditions.append("r.yds_rating >= %s")
                    params.append(filters['min_grade'])
                if filters.get('max_grade'):
                    where_conditions.append("r.yds_rating <= %s")
                    params.append(filters['max_grade'])
            
            # Length filters
            if filters.get('min_length'):
                where_conditions.append("r.length_ft >= %s")
                params.append(filters['min_length'])
                
            if filters.get('max_length'):
                where_conditions.append("r.length_ft <= %s")
                params.append(filters['max_length'])
            
            # Pitch count filters
            if filters.get('min_pitches'):
                where_conditions.append("r.pitches >= %s")
                params.append(filters['min_pitches'])
                
            if filters.get('max_pitches'):
                where_conditions.append("r.pitches <= %s")
                params.append(filters['max_pitches'])
                
            # Commitment grade filter
            if filters.get('min_commitment'):
                # Convert commitment grades to sortable values
                commitment_order = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7}
                min_val = commitment_order.get(filters['min_commitment'], 0)
                commitment_conditions = []
                for grade, val in commitment_order.items():
                    if val >= min_val:
                        commitment_conditions.append(f"r.commitment_grade = '{grade}'")
                if commitment_conditions:
                    where_conditions.append(f"({' OR '.join(commitment_conditions)})")
        
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)
        
        base_query += """
        ORDER BY ss.similarity_score DESC
        LIMIT %s
        """
        params.append(limit)
        
        try:
            cursor.execute(base_query, params)
            columns = [description[0] for description in cursor.description]
            results = cursor.fetchall()
            
            # Convert to list of dictionaries
            search_results = []
            for row in results:
                result = dict(zip(columns, row))
                
                # Parse metadata if it exists
                if result.get('metadata'):
                    try:
                        result['metadata'] = json.loads(result['metadata']) if isinstance(result['metadata'], str) else result['metadata']
                    except:
                        result['metadata'] = {}
                
                search_results.append(result)
            
            return search_results
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            return []

def format_search_results(results):
    """Format search results for display"""
    if not results:
        print("No routes found matching your query.")
        return
    
    print(f"\n🎯 Found {len(results)} matching routes:\n")
    
    for i, route in enumerate(results, 1):
        print(f"{i}. {route['route_name']}")
        
        # Basic info - combine all grades
        grade_parts = [
            route.get('yds_rating'),
            route.get('hueco_rating'), 
            route.get('aid_rating'),
            route.get('danger_rating'),
            route.get('commitment_grade')
        ]
        grade = ' '.join(filter(None, grade_parts)) or 'Ungraded'
        route_type = route['route_type'] or 'Unknown'
        print(f"   Grade: {grade} | Type: {route_type}")
        
        # Location
        location_parts = [part for part in [route['region'], route['main_area'], route['sub_area']] if part]
        if location_parts:
            print(f"   Location: {' > '.join(location_parts)}")
        
        # Quality and length
        if route['avg_stars'] and route['num_votes']:
            stars = route['avg_stars']
            votes = route['num_votes']
            print(f"   Rating: {stars:.1f}★ ({votes} votes)")
        
        if route['length_ft']:
            length_str = f"{route['length_ft']} ft"
            if route['pitches'] and route['pitches'] > 1:
                length_str += f", {route['pitches']} pitches"
            print(f"   Length: {length_str}")
        
        # Similarity score
        similarity = route['similarity_score']
        print(f"   Match: {similarity:.1%}")
        
        # Description preview
        if route['description']:
            desc_preview = route['description'][:150]
            if len(route['description']) > 150:
                desc_preview += "..."
            print(f"   Description: {desc_preview}")
        
        print()  # Empty line between results

def interactive_search():
    """Interactive search mode"""
    print("🏔️  Route Semantic Search")
    print("Enter natural language queries to find climbing routes")
    print("Examples: 'steep overhanging crack', 'easy slab in Yosemite', 'classic 5.9 trad'")
    print("Type 'quit' to exit\n")
    
    while True:
        try:
            query = input("Search query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Happy climbing!")
                break
            
            if not query:
                continue
            
            # Basic search (can add filter parsing later)
            results = search_routes(query, limit=5)
            format_search_results(results)
            
        except KeyboardInterrupt:
            print("\n👋 Happy climbing!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Search climbing routes using semantic similarity")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Number of results to return")
    parser.add_argument("--min-stars", type=float, help="Minimum star rating")
    parser.add_argument("--region", help="Filter by region")
    parser.add_argument("--area", help="Filter by main area")
    parser.add_argument("--type", help="Filter by route type")
    parser.add_argument("--min-grade", help="Minimum YDS grade (e.g., 5.9)")
    parser.add_argument("--max-grade", help="Maximum YDS grade (e.g., 5.11)")
    parser.add_argument("--min-length", type=int, help="Minimum length in feet")
    parser.add_argument("--max-length", type=int, help="Maximum length in feet")
    parser.add_argument("--min-pitches", type=int, help="Minimum number of pitches")
    parser.add_argument("--max-pitches", type=int, help="Maximum number of pitches")
    parser.add_argument("--min-commitment", choices=['IV', 'V', 'VI', 'VII'], help="Minimum commitment grade")
    parser.add_argument("--threshold", type=float, default=0.35, help="Similarity threshold (0.0-1.0)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive search mode")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_search()
    elif args.query:
        # Build filters
        filters = {}
        if args.min_stars:
            filters['min_stars'] = args.min_stars
        if args.region:
            filters['region'] = args.region
        if args.area:
            filters['area'] = args.area
        if args.type:
            filters['route_type'] = args.type
        if args.min_grade:
            filters['min_grade'] = args.min_grade
        if args.max_grade:
            filters['max_grade'] = args.max_grade
        if args.min_length:
            filters['min_length'] = args.min_length
        if args.max_length:
            filters['max_length'] = args.max_length
        if args.min_pitches:
            filters['min_pitches'] = args.min_pitches
        if args.max_pitches:
            filters['max_pitches'] = args.max_pitches
        if args.min_commitment:
            filters['min_commitment'] = args.min_commitment
        
        # Perform search
        results = search_routes(args.query, limit=args.limit, filters=filters, similarity_threshold=args.threshold)
        format_search_results(results)
    else:
        print("Use --interactive for interactive mode or provide a search query")
        print("Example: python search_routes.py 'steep crack climb'")