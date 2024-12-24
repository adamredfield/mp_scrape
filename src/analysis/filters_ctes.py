estimated_lengths_cte = f"""
        WITH estimated_lengths AS (
        SELECT  id,
                CASE WHEN route_type ILIKE '%trad%' AND length_ft IS NULL AND pitches IS NULL -- trad single-pitch
                    THEN (SELECT avg(length_ft) FROM routes.Routes r WHERE route_type ILIKE '%trad%'AND length_ft IS NOT NULL and pitches IS NULL AND length_ft < 230) -- avg single-pitch trad pitch length
                    WHEN route_type ILIKE '%trad%' AND length_ft IS NULL AND pitches IS NOT NULL -- trad multipitch
                    THEN (SELECT avg(length_ft/ pitches) FROM routes.Routes r WHERE route_type ILIKE '%trad%' AND length_ft IS NOT NULL and pitches IS NOT NULL) * pitches
                    WHEN route_type ILIKE '%sport%' AND length_ft IS NULL AND pitches IS NOT NULL -- sport single-pitch
                    THEN (SELECT avg(length_ft) FROM routes.Routes r WHERE route_type ILIKE '%sport%'AND length_ft IS NOT NULL and pitches IS NULL AND length_ft < 230) -- avg single-pitch sport pitch length
                    WHEN route_type ILIKE '%sport%' AND length_ft IS NULL AND pitches IS NOT NULL -- sport multipitch
                    THEN (SELECT avg(length_ft/ pitches) FROM routes.Routes r WHERE route_type ILIKE '%sport%' AND length_ft IS NOT NULL and pitches IS NOT NULL) * pitches
                    WHEN route_type ILIKE '%boulder%' AND length_ft IS NULL
                    THEN (SELECT avg(length_ft) FROM routes.Routes r WHERE route_type ILIKE '%boulder%' AND length_ft IS NOT NULL) -- boulder
                    WHEN route_type ILIKE '%aid%' AND length_ft IS NULL AND pitches IS NOT NULL -- aid multipitch
                    THEN (SELECT avg(length_ft/ pitches) FROM routes.Routes r WHERE route_type ILIKE '%aid%' AND length_ft IS NOT NULL and pitches IS NOT NULL) * pitches
                    ELSE (SELECT avg(length_ft) FROM routes.Routes r WHERE route_type ILIKE '%trad%'AND length_ft IS NOT NULL and pitches IS NULL AND length_ft < 230)
                END AS estimated_length
        FROM routes.Routes
        )
        """

def get_deduped_ticks_cte(user_id=None, year='2024'):
    """
    Creates a CTE for deduped ticks with optional user and year filtering
    
    Args:
        user_id: Optional user ID to filter by
        year: Optional year to filter ticks by
    Returns:
        str: SQL CTE for deduped ticks
    """

    conditions = []
    
    if year:
        conditions.append(f"EXTRACT(YEAR FROM t.date) = {year}")
    
    if user_id:
        conditions.append(f"t.user_id = '{user_id}'")
    
    # Combine conditions with WHERE if any exist, otherwise omit WHERE
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    deduped_ticks_cte = f"""
        WITH deduped_ticks_base AS(
                SELECT *,
                ROW_NUMBER() OVER (PARTITION BY route_id ORDER BY date DESC) as rn
                FROM routes.Ticks t
                {where_clause}
            ),
        deduped_ticks AS (  
            SELECT * FROM deduped_ticks_base
            WHERE rn = 1
        )
    """
    return deduped_ticks_cte

def route_type_filter(route_types):
    if route_types:
        type_conditions = []
        for route_type in route_types:
            type_conditions.append(f"r.route_type ILIKE '%{route_type}%'")
        type_filter = f"AND ({' OR '.join(type_conditions)})"
    else:
        type_filter = ''
    return type_filter

def year_filter(year=None, year_range=None, use_where=True, table_alias='t'):
    """Generate SQL clause for year filtering
    
    Args:
        year: Optional single year to filter by
        year_range: Optional tuple of (start_year, end_year) to filter between
        use_where: If True, starts with WHERE, otherwise starts with AND (default True)
        table_alias: Table alias to use (default 't')
    
    Returns:
        str: SQL filter clause
    """
    if not year and not year_range:
        return ''
        
    prefix = 'WHERE' if use_where else 'AND'
    
    if year_range:
        start_year, end_year = year_range
        return f"{prefix} EXTRACT(YEAR FROM {table_alias}.date) BETWEEN {start_year} AND {end_year}"
    else:
        return f"{prefix} EXTRACT(YEAR FROM {table_alias}.date) = {year}"

def add_user_filter(user_id, table_alias='t'):
    """
    Add user filtering to a query
    Args:
        query: SQL query string (can be empty)
        user_id: User ID to filter by
        table_alias: Alias of the Ticks table in the query (default 't')
    """
    return f"AND {table_alias}.user_id = '{user_id}'"

def add_fa_name_filter(fa_name, use_where=False, table_alias='fa'):
    """
    Add first ascensionist filtering to a query
    Args:
        fa_name: First ascensionist name or partnership to filter by
        table_alias: Alias of the FA table in the query (default 'fa')
    Returns:
        SQL filter string
    """
    if not fa_name or fa_name == "All FAs":
        return ""

    prefix = 'WHERE' if use_where else 'AND'
    
    if " & " in str(fa_name):
        climber1, climber2 = fa_name.split(" & ")
        # Escape single quotes in names
        climber1 = climber1.replace("'", "''")
        climber2 = climber2.replace("'", "''")
        return f"""
        {prefix} {table_alias}.route_id IN (
            SELECT a1.route_id
            FROM analysis.fa a1
            JOIN analysis.fa a2 ON a1.route_id = a2.route_id 
            WHERE a1.fa_type = a2.fa_type
            AND a1.fa_name = '{climber1}'
            AND a2.fa_name = '{climber2}'
        )
        """
    fa_name = fa_name.replace("'", "''")
    return f"{prefix} {table_alias}.fa_name = '{fa_name}'"