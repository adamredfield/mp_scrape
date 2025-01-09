import pandas as pd

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


def get_pitch_preference_lengths(pitch_preference):
    """Returns the appropriate length calculation based on pitch preference"""
    if pitch_preference != 'partial':
        return "coalesce(r.length_ft, el.estimated_length)"
    else:
        return """
            coalesce(r.length_ft, el.estimated_length) *
            CASE
                WHEN t.pitches_climbed IS NOT NULL
                    AND r.pitches IS NOT NULL
                    AND t.pitches_climbed <= r.pitches THEN
                    (t.pitches_climbed::float / r.pitches)
                ELSE
                    1
            END"""


def get_deduped_ticks_cte(user_id=None, year_start=2000, year_end=2100):
    deduped_ticks_cte = f"""
        WITH deduped_ticks_base AS(
                SELECT *,
                ROW_NUMBER() OVER (PARTITION BY route_id ORDER BY date DESC) as rn
                FROM routes.Ticks t
                {year_filter(year_range=(year_start, year_end), use_where=True)}
                {add_user_filter(user_id)}
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
    if not year and not year_range:
        return ''

    prefix = 'WHERE' if use_where else 'AND'

    if year_range:
        start_year, end_year = year_range
        return f"{prefix} EXTRACT(YEAR FROM {table_alias}.date) BETWEEN {start_year} AND {end_year}"
    else:
        return f"{prefix} EXTRACT(YEAR FROM {table_alias}.date) = {year}"


def add_user_filter(user_id, table_alias='t'):
    return f"AND {table_alias}.user_id = '{user_id}'"


def add_fa_name_filter(fa_name, use_where=False, table_alias='fa'):
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


def available_years(conn, user_id):
    years_query = f"""
    SELECT DISTINCT EXTRACT(YEAR FROM date)::int as year
    FROM routes.Ticks
    WHERE user_id = '{user_id}'
    and length(EXTRACT(YEAR FROM date)::text) = 4
    ORDER BY year
    """
    available_years_df = conn.query(years_query)
    years_df = pd.DataFrame({'date': pd.to_datetime(
        available_years_df['year'], format='%Y')})
    return years_df


def add_grade_filter(grade_system, grade_range):
    if not grade_system or not grade_range:
        return ""

    min_grade, max_grade = grade_range
    grade_column = {
        'YDS': 'r.yds_rating',
        'Boulder': 'r.hueco_rating',
        'Aid': 'r.aid_rating'
    }.get(grade_system)

    return f"""
    AND {grade_column} IS NOT NULL
    AND {grade_column} BETWEEN '{min_grade}' AND '{max_grade}'
    """


def fa_year_filter(fa_year_start, fa_year_end):
    if fa_year_start is None and fa_year_end is None:
        return ""  # No year filter, return all routes including NULL years

    if fa_year_start and fa_year_end:
        return f"""
            AND fa.year BETWEEN {fa_year_start} AND {fa_year_end}
        """
    elif fa_year_start:
        return f"""
            AND fa.year >= {fa_year_start}
        """
    elif fa_year_end:
        return f"""
            AND fa.year <= {fa_year_end}
        """

    return ""
