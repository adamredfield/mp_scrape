import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import openai
from datetime import datetime
import json
from datetime import timezone

# for running analysis locally 
def get_next_route(cursor):
    """Get routes from database that haven't been analyzed yet"""
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
    LEFT JOIN analysis.RouteAnalysis ra ON r.id = ra.route_id
    WHERE ra.id IS NULL  -- Only get routes not yet analyzed
    GROUP BY r.id
    LIMIT 1
    '''
    cursor.execute(query)
    columns = [description[0] for description in cursor.description]
    result = cursor.fetchone()
    current_route_data = dict(zip(columns, result)) if result else None

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
    return route_for_analysis

def get_grade_group(grade:str, level:str = 'base') -> str:

    if grade.startswith('V'):
        return grade
    if grade.startswith('A') or grade.startswith('C'):
        return grade 

    if grade.startswith('5.'):
        grade_prefix = '5.'
        cleaned_grade = grade.replace('5.', '')
    else:
        return grade
    
    if len(cleaned_grade) == 1: # e.g. 5.9
        base_grade = cleaned_grade
        grade_suffix = None
    elif cleaned_grade[1].isdigit(): # e.g. 5.10 or 5.10a
        base_grade = cleaned_grade[:2]
        if len(cleaned_grade) == 3:
            grade_suffix = cleaned_grade[2]
        else:
            grade_suffix = None
    else: # e.g. 5.9+
        base_grade = cleaned_grade[0]
        grade_suffix = cleaned_grade[1]
    
    if level == 'base':
        return f'{grade_prefix}{base_grade}'
    elif level == 'granular':
        if grade_suffix in ['a', 'b', '-']:
            return f'{grade_prefix}{base_grade}-'
        if grade_suffix in ['c', 'd', '+']:
            return f'{grade_prefix}{base_grade}+'
        else:
            return f'{grade_prefix}{base_grade}'
    else:
        return grade 

def construct_prompt(route):

    prompt_header = '''
    Analyze the following climbing route data and classify it into tags based on the provided JSON structure:

    Return a JSON object with tags and reasoning for style, features, descriptors, and rock_type.
    Ensure that the tags reflect the key attributes of the climbing route.
    Return ONLY the JSON object, without any markdown formatting or code blocks.
    '''

    route_details = [
        f"Name: {route['route_name']}",
        f"Grade: {route['combined_grade']}",
        f"Location: {route['location']}",
        f"Type: {route['route_type']}",
    ]
    if route.get('description'):
        route_details.append(f"Description: {route['description']}")
    if route.get('protection'):
        route_details.append(f"Protection: {route['protection']}")
    if route.get('comments'):
        route_details.append(f"Comments: {route['comments']}")
    
    prompt = f"{prompt_header}\n\nRoute Data:\n" + "\n".join(route_details) + "\n"

    return prompt

def process_route(route: dict, max_retries = 2) -> dict:

    openai.api_key = os.getenv('OPENAI_API_KEY')

    messages = [
        {"role": "system",
        "content": (
            "You are an experienced climbing route analyst. Your task is to analyze routes and categorize their core characteristics.\n\n"
            "Tag Categories:\n"
            "1. styles: Identify the primary climbing styles that define the route."
            "Note: Focus on the dominant style(s) that are most representative of the route's character. "
            "Note: This should NOT include climb types like trad/sport - only the physical style. "
            "Examples: (crack, chimney, face, overhang, slab, scramble, ridge). "
            "Examples that should be features, not styles: (offwidth, corner, roof, dihedral, flake, arete, traverse, lieback, undercling, pinch). "
            "We want to capture the style(s) that defines the route. We can have more than one style but we really want to capture the primary style(s). No more than 2 styles.\n"
            "2. features: Highlight specific route features that are essential to the route's identity (e.g., hand-crack, finger-crack, offwidth, dihedral, squeeze). \n"
            "Note: ideally these should act as sub-tags of the style. (e.g. style: crack, features: hand-crack). \n"
            "Note: We want to keep these specific but relatively general. (e.g. hand-crack vs. double-hand crack).\n"
            "These should complement the primary style(s) identified.\n"
            "Note: Please no more than 3 features. Only include features that are most defining of the route. If only one feature is most defining, then only include one feature.\n"
            "3. descriptors: Capture key characteristics about difficulty or experience that are central to the route (e.g., technical, burly, runout, polished, chossy, adventurous, scary, mellow).\n"
            "Note: Please no more than 3 descriptors. Only include descriptors that are most defining of the route. If only one descriptor is most defining, then only include one descriptor.\n"
            "4. rock_type: Type of rock only (e.g., granite, limestone, sandstone, gneiss). Do not include characteristics here.\n\n"
            "Note: Only one rock type per route.\n"
            "Note: The rock type should be mainly derived from the route's location.\n"
            "CRITICAL: You must return a valid JSON object exactly matching this format:\n"
            '{'
            '"styles": {"tags": [], "reasoning": "brief explanation of why these styles were chosen"}, '
            '"features": {"tags": [], "reasoning": "brief explanation of identified features"}, '
            '"descriptors": {"tags": [], "reasoning": "brief explanation of chosen characteristics"}, '
            '"rock_type": {"tags": [], "reasoning": "brief explanation of rock type determination"}'
            '}}\n\n'
            "Important Rules:\n"
            "- Prioritize styles and features that are most defining of the route\n"
            "- Include ONLY features explicitly mentioned or clearly implied in the route's data\n"
            "- Provide concise but specific reasoning for each category\n"
            "- Do not add any extra text or formatting"
            "- Ensure all JSON strings are properly escaped\n"
            "- Do not use line breaks within reasoning strings"
        )},
        {"role": "user", "content": construct_prompt(route)}
    ]

    for attempt in range(max_retries):
        try:    
            # Make API call
            response = openai.chat.completions.create(
            model="gpt-4o",  
            messages=messages,
            max_tokens=500,
                temperature=0.2
            )

            # Process responses
            response_text = response.choices[0].message.content.strip()

            response_text = response_text.replace('```json', '').replace('```', '')  # Remove code blocks
            response_text = response_text.replace('\n', ' ')  # Remove newlines
            response_text = response_text.strip()  # Clean up whitespace   

            try:
                parsed_tags = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"JSON Parse Error on attempt {attempt + 1}:")
                print(f"Error details: {str(e)}")
                print(f"Error position: {e.pos}")
                print(f"Problematic text around error:")
                start = max(0, e.pos - 50)
                end = min(len(response_text), e.pos + 50)
                print(response_text[start:end])
                continue

            result = {
                "route_id": route["route_id"],
                "tags": json.dumps(parsed_tags),
                "insert_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            return result
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error on attempt {attempt + 1}:")
            print(f"Error details: {str(e)}")
            print(f"Error position: {e.pos}")
            print(f"Problematic text around error:\n{response_text[max(0, e.pos-50):e.pos+50]}")
            
            if attempt > max_retries - 1:
                print(f"Retrying... ({attempt + 2}/{max_retries})")
                continue
            return None
        except Exception as e:
            print(f"API Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying... ({attempt + 2}/{max_retries})")
                continue
            return None

    print(f"Failed to process {route['route_name']} after {max_retries} attempts")
    return None

def process_route_response(ai_response: dict) -> dict:
    try:
        tags_dict = json.loads(ai_response['tags'])

        tag_type_mapping = {
            'styles': 'style',
            'features': 'feature',
            'descriptors': 'descriptor',
            'rock_type': 'rock_type'
        }

        processed_data = {
            'route_id': ai_response['route_id'],
            'tags': [], # [(db_col_name, tag), ...]
            'reasoning': [],
            'insert_date': datetime.now(timezone.utc).isoformat()  # [(db_col_name, reasoning), ...]
        }

        for ai_response_key, db_col_name in tag_type_mapping.items():
            data = tags_dict[ai_response_key]

            # extend for multiple tags per type
            processed_data['tags'].extend((db_col_name, tag) for tag in data['tags'])
            # append for single reasoning per type
            processed_data['reasoning'].append((db_col_name, data['reasoning']))

        return processed_data
    except KeyError as e:
        print(f"Error processing AI response: {e}")
        return None

def save_analysis_results(cursor, result):
    try:
        # Insert RouteAnalysis
        analysis_insert_sql = """
        INSERT INTO analysis.RouteAnalysis (
            route_id,
            insert_date
        ) VALUES (%s, %s)
        RETURNING id
        """
        cursor.execute(analysis_insert_sql, (
            result['route_id'],
            result['insert_date']
        ))
        analysis_id = cursor.fetchone()[0]

        # Insert RouteAnalysisTags
        tag_insert_sql = """
        INSERT INTO analysis.RouteAnalysisTags (
            analysis_id,
            tag_type,
            tag_value,
            insert_date
        ) VALUES (%s, %s, %s, %s)
        """
        for tag_type, tag_value in result['tags']:
            cursor.execute(tag_insert_sql, (
                analysis_id,
                tag_type,
                tag_value,
                result['insert_date']
            ))

        # Insert RouteAnalysisTagsReasoning
        reasoning_insert_sql = """
        INSERT INTO analysis.RouteAnalysisTagsReasoning (
            analysis_id,
            tag_type,
            reasoning,
            insert_date
        ) VALUES (%s, %s, %s, %s)
        """
        for tag_type, reasoning in result['reasoning']:
            cursor.execute(reasoning_insert_sql, (
                analysis_id,
                tag_type,
                reasoning,
                result['insert_date']
            ))

    except Exception as e:
        print(f"Error saving analysis results: {e}")

