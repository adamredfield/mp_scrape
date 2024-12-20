import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

import openai
from datetime import datetime
import json
from datetime import timezone
import pandas as pd
import re

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

def process_names(section):
    """Helper function to process names with pairing logic"""
    name_pairs = []
    # Split on commas first, then handle 'and' within each part
    parts = [p.strip() for p in section.split(',') if p.strip()]
    
    for part in parts:
        # Split on 'and' or '&' if present
        if ' and ' in part.lower() or '&' in part:
            names = re.split(r'\s+(?:and|&)\s+', part, flags=re.IGNORECASE)
            
            # Check for shared last name pattern
            if len(names) == 2 and all(re.match(r'^[A-Za-z]+$', n.strip()) for n in names):
                # Look for a last name after these first names
                remaining = part.split(names[-1])[-1].strip()
                if remaining and re.match(r'^[A-Za-z]+$', remaining):
                    name_pairs.append(f"{names[0].strip()} {remaining}")
                    name_pairs.append(f"{names[1].strip()} {remaining}")
                    continue
            
            # If no shared last name, add names individually
            name_pairs.extend(names)
        else:
            # Handle potential first-last name pairs
            words = part.split()
            if len(words) >= 2:
                name_pairs.append(part)
            else:
                name_pairs.append(part)
    
    return [name.strip() for name in name_pairs if name.strip()]

def clean_name(name):
    """Clean and standardize climber names"""
    if not name:
        return ""
        
    # Remove leading/trailing punctuation and whitespace
    name = re.sub(r'^[\W_]+|[\W_]+$', '', name)
    
    # Remove common noise words and patterns
    noise_patterns = [
        r'\b(?:and|with)\b',  # Common conjunctions
        r'\d{1,2}[-/]\d{1,2}[-/](?:20)?\d{2}',  # Modern date formats
        r'\d{1,2}/\d{1,2}(?:/\d{2,4})?',  # Other date formats
        # Only match months when they appear alone or with year/season indicators
        r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b(?:\s+(?:\d{4}|\d{2}|early|late|mid|spring|summer|fall|winter))?',
        r'\b(?:jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b(?:\s+(?:\d{4}|\d{2}|early|late|mid|spring|summer|fall|winter))?',
        r'\b(?:spring|summer|fall|winter)\b',  # Seasons
        r'\b(?:early|late|mid)\b',  # Time period modifiers
        r'\b(?:circa|c\.|ca\.|approximately|approx\.)\b',  # Approximate date indicators
        r'\b(?:unknown|various)\b',  # Unknown climbers
        r'\b(?:et\.? al\.?)\b',  # Et al.
        r'\b(?:did the first free ascent)\b',  # Common phrases
        r'\b(?:ffa|fa)\b',  # Remove type indicators within names
        r'\b(?:on|in|at|by|the)\b',  # Common prepositions and articles
    ]
    
    for pattern in noise_patterns:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    # Clean up any remaining artifacts
    name = re.sub(r'\s+', ' ', name)  # Replace multiple spaces with single space
    name = name.strip()
    
    # Skip if only numbers/spaces/symbols remain
    if not name or re.match(r'^[\d\s\W]+$', name):
        return ""
    
    # Capitalize first letter of each word
    name = ' '.join(word.capitalize() for word in name.split())
    
    return name

def clean_year(year_str):
    """
    Clean and standardize year format.
    For decades (e.g., '1960s' or '60s'), returns the middle year (e.g., '1965')
    """
    if not year_str:
        return None
    
    try:
        # Check if it's a decade format
        decade_match = re.search(r'(?:19|20)?\d{2}(?:\'s|s)$', year_str)
        if decade_match:
            # Remove 's or s suffix
            base_year = re.sub(r'(?:\'s|s)$', '', decade_match.group())
            
            # If it's a 2-digit year, assume 19xx
            if len(base_year) == 2:
                base_year = f"19{base_year}"
            
            # Return middle of the decade (base_year + 5)
            return str(int(base_year) + 5)
        
        # Handle 4-digit years (e.g., '1960')
        if len(year_str) == 4:
            return year_str
        
        # Handle 2-digit years (e.g., '60')
        year_match = re.search(r'\d{2}', year_str)
        if year_match:
            return f"19{year_match.group()}"
        
        return None
        
    except Exception as e:
        print(f"Error cleaning year {year_str}: {e}")
        return None

def parse_fa_data(fa_string):
    """
    Parse first ascent data into structured format.
    Returns a list of dictionaries containing:
    - name: First Ascensionist name
    - type: FA or FFA
    - year: Year of ascent (might be approximate or None)
    """
    if not fa_string or pd.isna(fa_string):
        return []
    
    results = []
    fa_string = fa_string.lower()

    # Split on 'ffa' first - anything after is FFA
    sections = re.split(r'ffa\W*', fa_string, maxsplit=1)

    # Process FA section
    fa_section = sections[0]
    fa_section = re.split(r'fa\W*', fa_section)[-1].strip()

    date_pattern = r'\d{1,2}[-/]\d{1,2}[-/](?:20)?\d{2}'
    year_pattern = r'(?:1|2)\d{3}(?:\'s|s)?|(?:\'|\~)?(?:19|20)\d{2}(?:\'s|s)?|\d{2}(?:\'s|s)|\d{0,2}\?'

    # Process FA section
    fa_year = None
    date_match = re.search(date_pattern, fa_section)
    if date_match:
        # Extract year from date format
        date_parts = date_match.group().split('-')
        if len(date_parts) != 3:
            date_parts = date_match.group().split('/')
        year = date_parts[-1]
        fa_year = '20' + year if len(year) == 2 else year
        # Remove the entire date from the section
        fa_section = re.sub(date_pattern, '', fa_section)
    else:
        # Try year pattern if no date found
        year_match = re.search(year_pattern, fa_section)
        if year_match:
            fa_year = clean_year(year_match.group())
            fa_section = fa_section.replace(year_match.group(), '').strip()
    
    # Process FA names
    for name in process_names(fa_section):
        cleaned_name = clean_name(name)
        if cleaned_name:
            results.append({
                'name': cleaned_name,
                'type': 'FA',
                'year': fa_year
            })

    # Process FFA section if it exists
    if len(sections) > 1:
        ffa_section = sections[1].strip()
        ffa_year = None
        
        # Try date pattern first
        date_match = re.search(date_pattern, ffa_section)
        if date_match:
            # Extract year from date format
            date_parts = date_match.group().split('-')
            if len(date_parts) != 3:
                date_parts = date_match.group().split('/')
            year = date_parts[-1]
            ffa_year = '20' + year if len(year) == 2 else year
            ffa_section = re.sub(date_pattern, '', ffa_section)
        else:
            # Try year pattern if no date found
            year_match = re.search(year_pattern, ffa_section)
            if year_match:
                ffa_year = clean_year(year_match.group())
                ffa_section = ffa_section.replace(year_match.group(), '').strip()

        # Process FFA names
        for name in process_names(ffa_section):
            cleaned_name = clean_name(name)
            if cleaned_name:
                results.append({
                    'name': cleaned_name,
                    'type': 'FFA',
                    'year': ffa_year
                })

    return results



