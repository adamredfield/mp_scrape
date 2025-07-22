"""
Route embedding functions for semantic search
Optimized for natural language similarity rather than structured analysis
"""

import json
import openai
import os
import sys
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
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
    Create natural language text optimized for semantic search embeddings.
    No instruction text, just clean content that represents how people think about routes.
    """
    parts = []
    
    # Core route identity - most important for search
    route_identity = f"{route_data['route_name']} is a {combine_grade(route_data)} {route_data['route_type'] or 'climb'}"
    
    # Add length and pitch info
    if route_data.get('length_ft'):
        route_identity += f" that's {route_data['length_ft']} feet"
    if route_data.get('pitches') and route_data['pitches'] > 1:
        route_identity += f" in {route_data['pitches']} pitches"
    
    parts.append(route_identity)
    
    # Route description - PRIORITIZED - contains rich semantic content
    if route_data.get('description'):
        desc = clean_text(route_data['description'])
        if desc:
            parts.append(f"Route description: {desc}")
    
    # Community insights - PRIORITIZED - climber experiences contain nuanced language
    if route_data.get('comments'):
        comments = clean_text(route_data['comments'])
        if comments:
            # Limit comment length for embeddings
            comment_sample = comments[:300] + "..." if len(comments) > 300 else comments
            parts.append(f"Climber feedback: {comment_sample}")
    
    # Location - hierarchical for area-based search
    location = combine_location(route_data)
    if location:
        parts.append(f"Located in {location}")
    
    # Commitment grade - important for big routes
    if route_data.get('commitment_grade'):
        commitment = route_data['commitment_grade']
        if commitment in ['IV', 'V', 'VI', 'VII']:
            parts.append(f"Commitment grade {commitment} big wall or alpine route")
    
    # Quality rating - important for recommendations
    if route_data.get('avg_stars') and route_data.get('num_votes'):
        stars = route_data['avg_stars']
        votes = route_data['num_votes']
        if votes >= 10:  # Only mention rating if statistically significant
            parts.append(f"Rated {stars:.1f} stars by {votes} climbers")
    
    # Protection info - important for planning
    if route_data.get('protection'):
        protection = clean_text(route_data['protection'])
        if protection:
            parts.append(f"Protection: {protection}")
    
    # AI-generated tags - leverage existing analysis
    if ai_tags:
        # Climbing styles
        styles = ai_tags.get('style', [])
        if styles:
            style_names = [tag['tag'] for tag in sorted(styles, key=lambda x: x['rank'])[:3]]
            parts.append(f"Climbing style: {', '.join(style_names)}")
        
        # Key features
        features = ai_tags.get('feature', [])
        if features:
            feature_names = [tag['tag'] for tag in sorted(features, key=lambda x: x['rank'])[:4]]
            parts.append(f"Key features: {', '.join(feature_names)}")
        
        # Descriptors
        descriptors = ai_tags.get('descriptor', [])
        if descriptors:
            desc_names = [tag['tag'] for tag in sorted(descriptors, key=lambda x: x['rank'])[:3]]
            parts.append(f"Character: {', '.join(desc_names)}")
        
        # Rock type
        rock_types = ai_tags.get('rock_type', [])
        if rock_types:
            parts.append(f"Rock type: {rock_types[0]['tag']}")
    
    # First ascent - historical context
    if route_data.get('fa'):
        fa = clean_text(route_data['fa'])
        if fa:
            parts.append(f"First ascent: {fa}")
    
    return ". ".join(parts) + "."

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
    openai.api_key = os.getenv('OPENAI_API_KEY')
    
    try:
        response = openai.embeddings.create(
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