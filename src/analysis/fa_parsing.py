import re
import pandas as pd

def parse_section(section, ascent_type, date_patterns, year_pattern) -> list[dict]:
    results = []
    section = section.strip()
    
    year = None
    
    full_year_match = re.search(r'\b(?:18|19|20)\d{2}\b', section)
    if full_year_match:
        year = full_year_match.group()
        section = re.sub(full_year_match.group(), '', section)
    else:
        # Try date patterns if no full year found
        for pattern in date_patterns:
            date_match = re.search(pattern, section)
            if date_match:
                date_str = date_match.group()
                # Extract year from the end of the date string
                year = re.search(r'(?:18|19|20)?\d{2,4}$', date_str).group()
                
                # Handle 2-digit vs 4-digit years
                if len(year) == 2:
                    year_num = int(year)
                    year = f"20{year}" if year_num < 50 else f"19{year}"
                elif len(year) == 4:
                    year = year
                    
                section = re.sub(pattern, '', section)
                break
        
        # Try year pattern if no date found
        if not year:
            year_match = re.search(year_pattern, section)
            if year_match:
                # Get the full match including any decade suffix
                full_match = year_match.group()
                year = clean_year(full_match)
                # Remove the entire match from the section
                matched_text = re.escape(full_match)
                section = re.sub(f'{matched_text}', '', section).strip()
    # Process names
    for name in process_names(section):
        cleaned_name = clean_name(name)
        if cleaned_name:
            results.append({
                'name': cleaned_name,
                'type': ascent_type,
                'year': year
            })
    return results

def parse_fa_data(fa_string) -> list[dict]:
    """
    Parse first ascent data into structured format.
    Returns a list of dictionaries containing:
    - name: First Ascensionist name
    - type: FA, FFA, or FCA
    - year: Year of ascent (might be approximate or None)
    """
    if not fa_string or pd.isna(fa_string):
        return []
    
    results = []
    fa_string = fa_string.lower()

    # Define patterns
    date_patterns = [
        r'\d{1,2}[-/]\d{1,2}[-/](?:18|19|20)?\d{2}',  # Full dates: MM/DD/YY or MM-DD-YY
        r'\d{1,2}[-/](?:18|19|20)?\d{2}',              # Month/Year: MM/YY or MM/YYYY
        r'\d{1,2}[-/]\d{4}',                           # Month/Year: MM/YYYY
    ]
    year_pattern = r'(?:18|19|20)?\d{2,4}(?:\'s|s)?'   # Simplified year pattern that includes decade suffix and 1800s

    ascent_types = [
        ('ffa', 'FFA'),  # First Free Ascent
        ('fca', 'FCA'),  # First Clean Ascent
        ('fa', 'FA'),    # First Ascent
    ]

    remaining_text = fa_string
    for search_type, result_type in ascent_types:
        sections = re.split(rf'{search_type}\W*', remaining_text, maxsplit=1, flags=re.IGNORECASE)
        if len(sections) > 1:
            results.extend(parse_section(sections[1], result_type, date_patterns, year_pattern))
            remaining_text = sections[0]
    
    if remaining_text.strip():
        results.extend(parse_section(remaining_text, 'FA', date_patterns, year_pattern))
    return results

def clean_year(year_str):
    """Clean and standardize year format"""
    if not year_str:
        return None
    
    try:
        # check if it's a decade (ends with 's or s)
        if year_str.lower().endswith('s') or year_str.lower().endswith("'s"):
            # Extract base year
            base_year = re.search(r'(?:18|19|20)?\d{2}|\d{4}', year_str).group()
            if len(base_year) == 2:
                base_year = f"19{base_year}"
            # Return middle of decade (1950s = 1965)
            return str(int(base_year) + 5)
        
        # Handle 4-digit years
        if re.match(r'^\d{4}$', year_str):
            return year_str
        
        # Handle 2-digit years - but prefer full year if available
        full_year_match = re.search(r'(?:18|19|20)\d{2}', year_str)
        if full_year_match:
            return full_year_match.group()
            
        # If only 2 digits, assume 19xx unless specified otherwise
        year_match = re.search(r'\d{2}', year_str)
        if year_match:
            year_num = int(year_match.group())
            return f"20{year_num}" if year_num < 50 else f"19{year_num}"
        
        return None
        
    except Exception as e:
        print(f"Error cleaning year {year_str}: {e}")
        return None

def clean_name(name):
    """Clean and standardize climber names"""
    # Remove leading/trailing punctuation
    name = re.sub(r'^[\W_]+|[\W_]+$', '', name)

    # Remove common noise words and patterns
    noise_patterns = [
        r'\b(?:and|with)\b', 
        r'\b(?:trad|sport|mixed|aid|free|solo|1st|first|then|bolted)\b', 
        r'\b(?:gear|now|retrobolted)\b', 
        r'\b(?:or earlier|or later)\b', 
        r'\b(?:did|the|ascent|first|free|ascent)\b',
        r'\b(?:company|partner|partners)\b',
        r'\b(?:lead|leads|leader|leading|led)\b',
        r'\b(?:original|originally)\b', 
        r'\b(?:1st|first)\b', 
        r'(?:P|p)\d+(?:[-:]|\s+[-:]|\s*[.:])\s*', 
        r'(?:P|p)\d+[-\s]*[-–]\s*(?:P|p)?\d+[-:]?\s*[.:]?\s*', 
        r'(?:^|\s*\.?\s*)(?:P|p)?\d+[-:]?\s*[.:]', 
        r'(?:^|\s*\.?\s*)(?:P|p)?\d+[-\s]*[-–]\s*\d+[-:]?\s*[.:]?',  
        r'(?:^|\s*\.?\s*)(?:P|p)?\d+(?:[-:]|\s+[-:]|\s*[.:])\s*',  
        r'\.\s*\d+[-:]?\s*[.:]',
        r'\d{1,2}[-/]\d{1,2}[-/](?:20)?\d{2}', 
        r'\d{1,2}/\d{1,2}(?:/\d{2,4})?', 
        r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b(?:\s+(?:\d{1,4}|early|late|mid|spring|summer|fall|winter)|\s*$)',
        r'\b(?:jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b(?:\s+(?:\d{1,4}|early|late|mid|spring|summer|fall|winter)|\s*$)',
        r'\b(?:spring|summer|fall|winter)\b', 
        r'\b(?:early|late|mid)\b',  
        r'\b(?:circa|c\.|ca\.|approximately|approx\.)\b', 
        r'\b(?:unknown|various)\b', 
        r'\b(?:et\.? al\.?)\b',  
        r'\b(?:did the first free ascent)\b',  
        r'\b(?:ffa|fa)\b', 
        r'\b(?:on|in|at|by|the)\b', 
        r'\b\d{4}\b',  
        r'\?',  
    ]
    
    for pattern in noise_patterns:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)
    
    # Clean up any remaining artifacts
    name = re.sub(r'\s+', ' ', name) 
    name = name.strip()
    
    # Skip if only numbers/spaces/symbols remain or if it's a generic term
    if (not name or 
        re.match(r'^[\d\s\W]+$', name) or 
        name.lower() in ['company', 'partner', 'partners', 'lead', 'original']): 
        return ""
    
    name = ' '.join(word.capitalize() for word in name.split())
    return name

def process_names(section):
    """Helper function to process names with pairing logic"""
    name_pairs = []
    # Split on commas, forward slashes, and dashes first
    parts = re.split(r'[,/]|-(?!\w)', section)  # Split on /, comma, and standalone dashes
    parts = [p.strip() for p in parts if p.strip()]
    
    for part in parts:
        # If we have "and" or "&", check for shared last name pattern
        if ' and ' in part.lower() or ' & ' in part.lower():
            words = part.split()
            
            # Find the position of 'and' or '&'
            connector_pos = -1
            for i, word in enumerate(words):
                if word.lower() in ['and', '&']:
                    connector_pos = i
                    break
            
            # Check for the shared last name pattern (two first names followed by one last name ie "Jan and Herb Conn")
            if (connector_pos > 0 and 
                connector_pos < len(words) - 1 and 
                len(words) == connector_pos + 3 and 
                # Make sure first parts don't already contain spaces (full names)
                ' ' not in words[0] and 
                ' ' not in words[connector_pos + 1]):
                
                first1 = words[0]
                first2 = words[connector_pos + 1]
                last_name = words[-1]
                
                # Only combine if it's a known shared last name pattern
                if (first1.lower() == 'herb' and first2.lower() == 'jan' and last_name.lower() == 'conn'):
                    name_pairs.append(f"{first1} {last_name}")
                    name_pairs.append(f"{first2} {last_name}")
                    continue
            
            names = re.split(r'\s+(?:and|&)\s+', part, flags=re.IGNORECASE)
            name_pairs.extend(names)
        else:
            name_pairs.append(part)
    
    return [name.strip() for name in name_pairs if name.strip()]