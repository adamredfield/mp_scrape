"""
Route embedding functions for semantic search
Optimized for natural language similarity rather than structured analysis
"""

import json
import openai
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(project_root, '.env'))
sys.path.append(project_root)

def get_routes_for_embedding(cursor, limit=50, user_id=None, force_regenerate=False, offset=0):
    """Get routes that need embeddings generated"""
    
    # If user_id is provided, prioritize their ticked routes
    if user_id:
        # Choose query based on whether we want to regenerate all or just missing
        if force_regenerate:
            query = '''
            SELECT
                r.id as route_id,
                r.route_name,
                r.yds_rating,
                r.hueco_rating,
                r.aid_rating,
                r.danger_rating,
                r.commitment_grade,
                r.avg_stars,
                r.num_votes,
                r.region,
                r.main_area,
                r.sub_area,
                r.specific_location,
                r.route_type,
                r.length_ft,
                r.pitches,
                r.fa,
                r.description,
                r.protection,
                STRING_AGG(rc.comment, ' | ') as comments
            FROM routes.Routes r
            INNER JOIN routes.Ticks t ON r.id = t.route_id
            LEFT JOIN routes.RouteComments rc ON r.id = rc.route_id
            WHERE t.user_id = %s   -- All routes this user has ticked
            GROUP BY r.id
            ORDER BY r.id  -- Process systematically by route ID
            LIMIT %s OFFSET %s
            '''
        else:
            query = '''
            SELECT
                r.id as route_id,
                r.route_name,
                r.yds_rating,
                r.hueco_rating,
                r.aid_rating,
                r.danger_rating,
                r.commitment_grade,
                r.avg_stars,
                r.num_votes,
                r.region,
                r.main_area,
                r.sub_area,
                r.specific_location,
                r.route_type,
                r.length_ft,
                r.pitches,
                r.fa,
                r.description,
                r.protection,
                STRING_AGG(rc.comment, ' | ') as comments
            FROM routes.Routes r
            INNER JOIN routes.Ticks t ON r.id = t.route_id
            LEFT JOIN routes.RouteComments rc ON r.id = rc.route_id
            LEFT JOIN vectors.route_embeddings re ON r.id = re.route_id AND re.content_type = 'full_route'
            WHERE re.id IS NULL  -- Only get routes without embeddings
            AND t.user_id = %s   -- Only routes this user has ticked
            GROUP BY r.id
            ORDER BY r.avg_stars DESC, r.num_votes DESC  -- Prioritize high-quality routes
            LIMIT %s OFFSET %s
            '''
        cursor.execute(query, (user_id, limit, offset))
    else:
        # Original query for general routes
        query = '''
        SELECT
            r.id as route_id,
            r.route_name,
            r.yds_rating,
            r.hueco_rating,
            r.aid_rating,
            r.danger_rating,
            r.commitment_grade,
            r.avg_stars,
            r.num_votes,
            r.region,
            r.main_area,
            r.sub_area,
            r.specific_location,
            r.route_type,
            r.length_ft,
            r.pitches,
            r.fa,
            r.description,
            r.protection,
            STRING_AGG(rc.comment, ' | ') as comments
        FROM routes.Routes r
        LEFT JOIN routes.RouteComments rc ON r.id = rc.route_id
        LEFT JOIN vectors.route_embeddings re ON r.id = re.route_id AND re.content_type = 'full_route'
        WHERE re.id IS NULL  -- Only get routes without embeddings
        GROUP BY r.id
        ORDER BY r.avg_stars DESC, r.num_votes DESC  -- Prioritize popular routes
        LIMIT %s OFFSET %s
        '''
        cursor.execute(query, (limit, offset))
    
    columns = [description[0] for description in cursor.description]
    results = cursor.fetchall()
    return [dict(zip(columns, row)) for row in results]

def get_existing_ai_tags(cursor, route_id):
    """Get existing AI analysis tags for a route"""
    query = '''
    SELECT 
        rat.tag_type,
        rat.tag_value,
        rat.rank
    FROM analysis.RouteAnalysisTags_v2 rat
    JOIN analysis.RouteAnalysis_v2 ra ON rat.analysis_id = ra.id
    WHERE ra.route_id = %s
    ORDER BY rat.tag_type, rat.rank
    '''
    cursor.execute(query, (route_id,))
    columns = [description[0] for description in cursor.description]
    results = cursor.fetchall()
    tags = {}
    for row in results:
        tag_data = dict(zip(columns, row))
        tag_type = tag_data['tag_type']
        if tag_type not in tags:
            tags[tag_type] = []
        tags[tag_type].append({
            'tag': tag_data['tag_value'],
            'rank': tag_data['rank']
        })
    return tags

def create_embedding_text(route_data, ai_tags=None):
    """
    Create search-optimized embedding text that prioritizes AI tags and geographic context.
    Leverages existing LLM analysis for maximum searchability.
    """
    parts = []
    
    # 1. GEOGRAPHIC CONTEXT FIRST - Critical for location-based searches
    geo_context = get_geographic_context(route_data)
    if geo_context:
        parts.append(geo_context)
    
    # 2. AI TAGS - PRIORITIZED - These are your LLM-analyzed characteristics
    if ai_tags:
        # Rock type - Important for material-based searches
        if rock_types := ai_tags.get('rock_type'):
            rock_type = rock_types[0]['tag'] if isinstance(rock_types, list) else rock_types.get('tag', '')
            if rock_type:
                parts.append(f"{rock_type} rock climbing")
        
        # Climbing styles - Core search terms
        if styles := ai_tags.get('style'):
            style_names = [tag['tag'] for tag in sorted(styles, key=lambda x: x['rank'])[:3]]
            parts.append(f"{', '.join(style_names)} climbing")
        
        # Key features - Specific characteristics climbers search for
        if features := ai_tags.get('feature'):
            feature_names = [tag['tag'] for tag in sorted(features, key=lambda x: x['rank'])[:4]]
            parts.append(f"Features: {', '.join(feature_names)}")
        
        # Descriptors - Experience-based terms
        if descriptors := ai_tags.get('descriptor'):
            desc_names = [tag['tag'] for tag in sorted(descriptors, key=lambda x: x['rank'])[:3]]
            parts.append(f"Character: {', '.join(desc_names)}")
    
    # 3. FORMATION TYPE - Detect if it's a tower, wall, crack, etc.
    formation = detect_formation_type(route_data)
    if formation:
        parts.append(f"{formation} formation")
    
    # 4. CORE ROUTE IDENTITY
    route_name = route_data.get('route_name', '')
    grade = combine_grade(route_data)
    route_type = route_data.get('route_type', 'climb')
    
    identity = f"{route_name} is a {grade} {route_type}"
    
    # Add dimensions
    if route_data.get('length_ft'):
        identity += f" that's {route_data['length_ft']} feet"
    if route_data.get('pitches') and route_data['pitches'] > 1:
        identity += f" in {route_data['pitches']} pitches"
    
    parts.append(identity)
    
    # 5. LOCATION - Now that context is established
    location = combine_location(route_data)
    if location:
        parts.append(f"Located in {location}")
    
    # 6. QUALITY INDICATOR - Important for "classic" searches
    if route_data.get('avg_stars') and route_data.get('num_votes', 0) >= 10:
        stars = route_data['avg_stars']
        votes = route_data['num_votes']
        if stars >= 3.5:
            parts.append(f"Classic highly-rated {stars:.1f} star route with {votes} votes")
        elif stars >= 3.0:
            parts.append(f"Popular {stars:.1f} star route")
    
    # 7. COMMITMENT GRADE - For big route searches
    if route_data.get('commitment_grade'):
        commitment = route_data['commitment_grade']
        if commitment in ['IV', 'V', 'VI', 'VII']:
            parts.append(f"Grade {commitment} big wall alpine adventure")
    
    # 8. KEY CHARACTERISTICS from description - But more selective
    if route_data.get('description'):
        desc = clean_text(route_data['description'])
        if desc:
            # Extract only the most search-relevant phrases
            key_phrases = extract_search_keywords(desc)
            if key_phrases:
                parts.append(f"Notable features: {key_phrases}")
    
    # 9. PROTECTION - Important for style searches
    if route_data.get('protection'):
        protection = clean_text(route_data['protection'])
        if protection:
            # Simplify protection info to key concepts
            protection_summary = summarize_protection(protection)
            if protection_summary:
                parts.append(f"Protection: {protection_summary}")
    
    return ". ".join(parts) + "."

def get_geographic_context(route_data):
    """
    Add explicit geographic context that climbers search for
    """
    region = route_data.get('region', '')
    main_area = route_data.get('main_area', '')
    sub_area = route_data.get('sub_area', '')
    
    # Desert climbing regions
    if region in ['Utah', 'Arizona', 'Nevada', 'New Mexico']:
        if any(area in str(main_area).lower() for area in ['moab', 'indian creek', 'castle valley', 'fisher towers']):
            return "Desert sandstone tower and crack climbing"
        elif 'zion' in str(main_area).lower():
            return "Desert sandstone wall climbing"
        elif 'red rocks' in str(main_area).lower():
            return "Desert limestone climbing"
        else:
            return "Desert climbing"
    
    # California granite
    elif region == 'California':
        if 'yosemite' in str(main_area).lower():
            return "Granite crack and big wall climbing"
        elif 'joshua tree' in str(main_area).lower():
            return "Desert granite climbing"
        elif any(area in str(main_area).lower() for area in ['tahoe', 'tuolumne', 'sierra']):
            return "Sierra granite climbing"
        elif 'coast' in str(main_area).lower() or 'big sur' in str(main_area).lower():
            return "Coastal climbing"
    
    # Alpine regions
    elif region in ['Colorado', 'Wyoming', 'Montana', 'Washington']:
        return "Alpine mountain climbing"
    
    # Other regions
    elif region in ['Kentucky', 'Tennessee', 'West Virginia']:
        return "Limestone sport climbing"
    elif region == 'New Hampshire':
        return "Granite climbing"
    
    return None

def detect_formation_type(route_data):
    """
    Detect if this is a tower, wall, crack, slab, etc.
    """
    route_name = route_data.get('route_name', '').lower()
    location = route_data.get('specific_location', '').lower()
    combined = f"{route_name} {location}"
    
    # Formation type keywords
    formations = {
        'tower': ['tower', 'spire', 'pinnacle', 'needle'],
        'wall': ['wall', 'face', 'headwall'],
        'crack': ['crack', 'splitter', 'corner', 'dihedral'],
        'slab': ['slab', 'friction'],
        'arete': ['arete', 'ridge', 'buttress'],
        'chimney': ['chimney', 'squeeze'],
        'roof': ['roof', 'overhang', 'ceiling']
    }
    
    for formation_type, keywords in formations.items():
        if any(keyword in combined for keyword in keywords):
            return formation_type
    
    return None

def extract_search_keywords(description):
    """
    Extract only the most search-relevant terms from description
    """
    # Keywords that climbers commonly search for
    search_keywords = [
        'exposed', 'runout', 'pumpy', 'sustained', 'technical', 'steep',
        'overhang', 'traverse', 'crux', 'delicate', 'powerful', 'classic',
        'splitter', 'perfect', 'varied', 'interesting', 'spectacular',
        'committing', 'scary', 'safe', 'beginner', 'moderate', 'advanced'
    ]
    
    desc_lower = description.lower()
    found_keywords = []
    
    for keyword in search_keywords:
        if keyword in desc_lower:
            found_keywords.append(keyword)
            if len(found_keywords) >= 5:  # Limit to most relevant
                break
    
    return ', '.join(found_keywords) if found_keywords else None

def summarize_protection(protection_text):
    """
    Simplify protection info to key searchable concepts
    """
    protection_lower = protection_text.lower()
    
    # Key protection concepts
    if 'bolt' in protection_lower and 'anchor' in protection_lower:
        return "bolted route with anchors"
    elif 'bolt' in protection_lower:
        return "bolted protection"
    elif 'runout' in protection_lower or 'sparse' in protection_lower:
        return "runout sparse protection"
    elif 'cam' in protection_lower and 'nut' in protection_lower:
        return "cams and nuts protection"
    elif 'cam' in protection_lower:
        return "cam protection"
    elif any(word in protection_lower for word in ['trad', 'rack', 'gear']):
        return "traditional gear protection"
    elif 'piton' in protection_lower:
        return "piton protection"
    
    return None

def combine_grade(route_data):
    """Combine all grade components like existing function"""
    grade_parts = [
        route_data.get('yds_rating') or '',
        route_data.get('hueco_rating') or '',
        route_data.get('aid_rating') or '',
        route_data.get('danger_rating') or '',
        route_data.get('commitment_grade') or ''
    ]
    combined = ' '.join(filter(None, grade_parts)).strip()
    return combined if combined else 'ungraded'

def combine_location(route_data):
    """Combine location hierarchy like existing function"""
    location_parts = [
        route_data.get('region') or '',
        route_data.get('main_area') or '',
        route_data.get('sub_area') or '',
        route_data.get('specific_location') or ''
    ]
    combined = ' > '.join(filter(None, location_parts)).strip()
    return combined if combined else None

def clean_text(text):
    """Clean text for embedding - remove excessive whitespace, special chars"""
    if not text:
        return ""
    
    # Remove excessive whitespace and newlines
    cleaned = ' '.join(text.split())
    
    # Remove common data artifacts
    cleaned = cleaned.replace(' | ', '. ')  # Comment separators become sentences
    
    return cleaned.strip()

def generate_embedding(text, model="text-embedding-3-small"):
    """Generate embedding using OpenAI API"""
    api_key = os.getenv('OPENAI_API_KEY')
    print(f"Debug: API key loaded: {api_key[:10] if api_key else 'None'}...")
    
    # Create client with API key
    client = openai.OpenAI(api_key=api_key)
    
    try:
        response = client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def create_route_metadata(route_data, ai_tags=None):
    """Create searchable metadata for filtering"""
    metadata = {
        'grade': combine_grade(route_data),
        'route_type': route_data.get('route_type'),
        'region': route_data.get('region'),
        'main_area': route_data.get('main_area'),
        'length_ft': route_data.get('length_ft'),
        'pitches': route_data.get('pitches'),
        'avg_stars': route_data.get('avg_stars'),
        'num_votes': route_data.get('num_votes')
    }
    
    # Add AI tag metadata for filtering
    if ai_tags:
        for tag_type, tags in ai_tags.items():
            if tags:
                # Store top tags for each type
                top_tags = [tag['tag'] for tag in sorted(tags, key=lambda x: x['rank'])[:3]]
                metadata[f'{tag_type}_tags'] = top_tags
    
    # Remove None values
    return {k: v for k, v in metadata.items() if v is not None}

def save_route_embedding(cursor, route_id, content_type, content_source, embedding, metadata):
    """Save embedding to database"""
    try:
        insert_sql = """
        INSERT INTO vectors.route_embeddings (
            route_id,
            content_type,
            content_source,
            embedding,
            metadata,
            created_at,
            updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (route_id, content_type)
        DO UPDATE SET
            content_source = EXCLUDED.content_source,
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata,
            updated_at = EXCLUDED.updated_at
        """
        
        now = datetime.now()
        cursor.execute(insert_sql, (
            route_id,
            content_type,
            content_source,
            embedding,
            json.dumps(metadata),
            now,
            now
        ))
        
        print(f"Saved embedding for route {route_id}")
        return True
        
    except Exception as e:
        print(f"Error saving embedding for route {route_id}: {e}")
        return False

def process_route_for_embedding(cursor, route_data):
    """Full pipeline: route data -> embedding text -> embedding -> database"""
    route_id = route_data['route_id']
    
    try:
        # Get existing AI tags if available
        ai_tags = get_existing_ai_tags(cursor, route_id)
        
        # Create embedding text
        embedding_text = create_embedding_text(route_data, ai_tags)
        
        # Generate embedding
        embedding = generate_embedding(embedding_text)
        if not embedding:
            return False
        
        # Create metadata
        metadata = create_route_metadata(route_data, ai_tags)
        
        # Save to database
        success = save_route_embedding(
            cursor, 
            route_id, 
            'full_route', 
            embedding_text, 
            embedding, 
            metadata
        )
        
        if success:
            print(f"✓ Processed embedding for '{route_data['route_name']}'")
        
        return success
        
    except Exception as e:
        print(f"Error processing route {route_id}: {e}")
        return False