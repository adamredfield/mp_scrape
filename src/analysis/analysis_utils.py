def get_grade_group(grade:str, level:str = 'base') -> str:

    if not grade:
        return None

    if grade[:2] == '5.':
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
        
    return grade 

    