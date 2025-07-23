#!/usr/bin/env python3
"""
Route Semantic Search
Search climbing routes using natural language queries via embeddings
"""

import os
import sys
import json
import openai
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.database.utils import create_connection
from src.vectordb.embedding_functions import generate_embedding

def search_routes(query, limit=10, use_llm_intelligence=True, debug=False):
    """
    Ultimate search engine with LLM intelligence for query understanding and result ranking
    
    Args:
        query (str): Natural language search query
        limit (int): Number of results to return
        use_llm_intelligence (bool): Use LLM for query understanding and reranking
        debug (bool): Show debug information
    
    Returns:
        List of route matches with enhanced relevance scores
    """
    
    if debug:
        print(f"🔍 Searching for: '{query}'")
        print(f"🧠 LLM Intelligence: {'ON' if use_llm_intelligence else 'OFF'}")
    
    # Step 1: LLM Query Understanding (if enabled)
    if use_llm_intelligence:
        query_analysis = understand_query_with_llm(query)
        if debug and query_analysis:
            print(f"📝 Query Understanding: {query_analysis}")
        
        # Use enhanced query for embedding search
        search_query = query_analysis.get('enhanced_query', query) if query_analysis else query
        filters = query_analysis.get('filters', {}) if query_analysis else {}
    else:
        search_query = query
        filters = {}
    
    # Step 2: Generate embedding and perform semantic search
    query_embedding = generate_embedding(search_query, model="text-embedding-3-small")
    
    if not query_embedding:
        print("❌ Failed to generate embedding for query")
        return []
    
    # Step 3: Execute database search with intelligent filtering
    with create_connection() as connection:
        cursor = connection.cursor()
        
        # Get more candidates than needed for LLM reranking
        candidate_limit = limit * 3 if use_llm_intelligence else limit
        similarity_threshold = 0.25 if use_llm_intelligence else 0.35
        
        results = execute_vector_search(
            cursor, 
            query_embedding, 
            filters, 
            candidate_limit,
            similarity_threshold
        )
        
        if debug:
            print(f"📊 Found {len(results)} candidates from vector search")
    
    # Step 4: LLM Reranking (if enabled and we have results)
    if use_llm_intelligence and results and len(results) > limit:
        if debug:
            print("🎯 Applying LLM reranking...")
        
        results = rerank_results_with_llm(
            query, 
            results, 
            query_analysis,
            limit,
            debug
        )
    else:
        results = results[:limit]
    
    if debug:
        print(f"✅ Returning {len(results)} final results")
    
    return results

def understand_query_with_llm(query):
    """
    Use LLM to understand query intent and extract search parameters
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return None
    
    client = openai.OpenAI(api_key=api_key)
    
    system_prompt = """You are an expert climbing route search assistant. Analyze queries and extract search intent.

Return JSON with:
1. enhanced_query: Optimized query for embedding search (keep natural language but emphasize key concepts)
2. filters: Specific filters to apply
3. intent: What the user is looking for
4. key_concepts: Important concepts to boost in ranking

Geographic mappings:
- "desert" → regions: Utah, Arizona, Nevada, New Mexico
- "sierra" → region: California, area contains "Sierra"
- "yosemite" → region: California, area: "Yosemite"
- "alpine" → regions: Colorado, Wyoming, Washington, Montana

Formation types: tower, wall, crack, slab, chimney, arete, roof

Quality terms:
- "classic" → min_stars: 3.5, min_votes: 20
- "popular" → min_votes: 50
- "obscure" or "hidden gem" → max_votes: 30

Grade terms:
- "easy" or "beginner" → max_grade: "5.6"
- "moderate" → max_grade: "5.9"
- "hard" or "difficult" → min_grade: "5.10a"

Example response:
{
    "enhanced_query": "desert sandstone tower crack climbing exposed multipitch",
    "filters": {
        "regions": ["Utah", "Arizona"],
        "formation_type": "tower",
        "min_pitches": 2
    },
    "intent": "Looking for desert tower climbing routes",
    "key_concepts": ["desert", "tower", "sandstone", "multipitch"]
}"""

    user_prompt = f'Analyze this climbing search query: "{query}"'
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=300
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Query understanding error: {e}")
        return None

def execute_vector_search(cursor, embedding, filters, limit, threshold):
    """
    Execute the vector database search with filters
    """
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
    
    where_conditions = []
    params = [embedding, embedding, threshold]
    
    # Apply intelligent filters
    if filters.get('regions'):
        placeholders = ','.join(['%s'] * len(filters['regions']))
        where_conditions.append(f"r.region IN ({placeholders})")
        params.extend(filters['regions'])
    
    if filters.get('region'):
        where_conditions.append("r.region ILIKE %s")
        params.append(f"%{filters['region']}%")
    
    if filters.get('area'):
        where_conditions.append("r.main_area ILIKE %s")
        params.append(f"%{filters['area']}%")
    
    if filters.get('min_stars'):
        where_conditions.append("r.avg_stars >= %s")
        params.append(filters['min_stars'])
    
    if filters.get('min_votes'):
        where_conditions.append("r.num_votes >= %s")
        params.append(filters['min_votes'])
    
    if filters.get('max_votes'):
        where_conditions.append("r.num_votes <= %s")
        params.append(filters['max_votes'])
    
    if filters.get('min_pitches'):
        where_conditions.append("r.pitches >= %s")
        params.append(filters['min_pitches'])
    
    if filters.get('max_grade'):
        where_conditions.append("r.yds_rating <= %s")
        params.append(filters['max_grade'])
    
    # Formation type filter
    if filters.get('formation_type'):
        formation = filters['formation_type']
        formation_keywords = {
            'tower': ['tower', 'spire', 'pinnacle'],
            'wall': ['wall', 'face', 'headwall'],
            'crack': ['crack', 'splitter'],
            'slab': ['slab']
        }
        
        if formation in formation_keywords:
            keywords = formation_keywords[formation]
            formation_conditions = []
            for keyword in keywords:
                formation_conditions.append("r.route_name ILIKE %s")
                params.append(f"%{keyword}%")
                formation_conditions.append("r.specific_location ILIKE %s")
                params.append(f"%{keyword}%")
            
            where_conditions.append(f"({' OR '.join(formation_conditions)})")
    
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

def rerank_results_with_llm(query, results, query_analysis, limit, debug=False):
    """
    Use LLM to rerank results based on relevance to original query
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return results[:limit]
    
    client = openai.OpenAI(api_key=api_key)
    
    # Prepare route summaries (limit to top candidates to save tokens)
    candidates = results[:min(20, len(results))]
    route_summaries = []
    
    for i, route in enumerate(candidates):
        grade_parts = [
            route.get('yds_rating'),
            route.get('aid_rating'),
            route.get('commitment_grade')
        ]
        grade = ' '.join(filter(None, grade_parts)) or 'Ungraded'
        
        location = f"{route.get('region', '')} > {route.get('main_area', '')}"
        
        summary = {
            'id': i,
            'name': route['route_name'],
            'grade': grade,
            'type': route.get('route_type'),
            'location': location,
            'stars': route.get('avg_stars'),
            'votes': route.get('num_votes'),
            'pitches': route.get('pitches'),
            'length_ft': route.get('length_ft'),
            'similarity_score': round(route['similarity_score'], 3)
        }
        route_summaries.append(summary)
    
    # Create reranking prompt
    intent = query_analysis.get('intent', 'Finding climbing routes') if query_analysis else 'Finding climbing routes'
    key_concepts = query_analysis.get('key_concepts', []) if query_analysis else []
    
    system_prompt = f"""You are a climbing route search expert. Rerank these routes by relevance to the user's query.

Original query: "{query}"
User intent: {intent}
Key concepts: {key_concepts}

Consider:
1. How well the route matches the specific intent
2. Location accuracy (if location was specified)
3. Formation type match (tower/wall/crack/slab)
4. Grade appropriateness
5. Style and characteristics

Return JSON with ranked route IDs in order of best match:
{{"ranked_ids": [array of route IDs, best match first]}}

Only include routes that are genuinely relevant to the query."""

    user_prompt = f"Routes to rank:\n{json.dumps(route_summaries, indent=2)}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
            max_tokens=150
        )
        
        result = json.loads(response.choices[0].message.content)
        ranked_ids = result.get('ranked_ids', [])
        
        if debug:
            print(f"🎯 LLM ranked {len(ranked_ids)} routes")
        
        # Reorder results based on LLM ranking
        reranked = []
        for rid in ranked_ids:
            if isinstance(rid, int) and 0 <= rid < len(candidates):
                reranked.append(candidates[rid])
        
        # Add any remaining results
        seen_route_ids = {r['route_id'] for r in reranked}
        for route in results:
            if route['route_id'] not in seen_route_ids and len(reranked) < limit:
                reranked.append(route)
        
        return reranked[:limit]
        
    except Exception as e:
        if debug:
            print(f"Reranking error: {e}")
        return results[:limit]

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
    """Interactive search mode with ultimate LLM intelligence"""
    print("🏔️  Ultimate Route Search Engine")
    print("Powered by LLM intelligence for query understanding and result ranking")
    print("Examples: 'desert towers', 'moderate sierra ridge climbs', 'classic yosemite cracks'")
    print("Commands: 'quit' to exit, 'debug' to toggle debug mode, 'simple' for basic search\n")
    
    use_llm = True
    debug_mode = False
    print("🧠 LLM Intelligence: ON")
    print("🔍 Debug Mode: OFF")
    print()
    
    while True:
        try:
            query = input("🎯 Search query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Happy climbing!")
                break
            
            if query.lower() == 'debug':
                debug_mode = not debug_mode
                status = "ON" if debug_mode else "OFF"
                print(f"🔍 Debug Mode: {status}")
                continue
            
            if query.lower() == 'simple':
                use_llm = not use_llm
                status = "ON" if use_llm else "OFF"
                print(f"🧠 LLM Intelligence: {status}")
                continue
            
            if not query:
                continue
            
            # Use the ultimate search engine
            results = search_routes(
                query, 
                limit=5, 
                use_llm_intelligence=use_llm,
                debug=debug_mode
            )
                
            format_search_results(results)
            
        except KeyboardInterrupt:
            print("\n👋 Happy climbing!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ultimate climbing route search with LLM intelligence")
    parser.add_argument("query", nargs="?", help="Natural language search query")
    parser.add_argument("--limit", type=int, default=10, help="Number of results to return")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM intelligence (basic search only)")
    parser.add_argument("--debug", action="store_true", help="Show debug information")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive search mode")
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_search()
    elif args.query:
        # Use the ultimate search engine
        results = search_routes(
            args.query, 
            limit=args.limit,
            use_llm_intelligence=not args.no_llm,
            debug=args.debug
        )
        format_search_results(results)
    else:
        print("🏔️  Ultimate Route Search Engine")
        print("Use --interactive for interactive mode or provide a search query")
        print("\nExamples:")
        print("  python search_routes.py 'desert towers'")
        print("  python search_routes.py 'moderate sierra ridge climbs' --debug")
        print("  python search_routes.py 'classic yosemite cracks' --limit 5")
        print("  python search_routes.py --interactive")