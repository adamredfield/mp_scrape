import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(project_root)

from src.analysis.filters_ctes import add_user_filter, add_fa_name_filter, get_deduped_ticks_cte

def get_top_first_ascensionists(conn, user_id=None, year_start=None, year_end=None):
    f"""
    Get the most prolific first ascensionists
    Returns: List of (name, count) tuples
    """
    query = f"""
    {get_deduped_ticks_cte(user_id, year_start=year_start, year_end=year_end)}
    SELECT fa_name, COUNT(*) as fa_count
    FROM analysis.fa
    JOIN deduped_ticks t on t.route_id = fa.route_id
    WHERE fa_type IN ('FA', 'FFA', 'FCA')
    {add_user_filter(user_id)}
    GROUP BY fa_name
    ORDER BY fa_count desc
    LIMIT 10
    """
    result = conn.query(query)
    return result.values.tolist()

def get_first_ascensionist_by_decade(conn, name, user_id=None, year_start=None, year_end=None):
    """
    Get a first ascensionist's activity by decade
    Returns: List of (decade, count) tuples
    """
    query = f"""
    {get_deduped_ticks_cte(user_id, year_start=year_start, year_end=year_end)}
    SELECT 
        CONCAT(FLOOR(fa.year::int/10)*10, 's') as decade,
        COUNT(*) as fa_count
    FROM analysis.fa fa
    JOIN deduped_ticks t on t.route_id = fa.route_id
    WHERE fa_type IN ('FA', 'FFA', 'FCA')
    AND fa.year IS NOT null and length(fa.year::text) = 4
    {add_fa_name_filter(name, use_where=False)}
    {add_user_filter(user_id)}
    GROUP BY FLOOR(fa.year::int/10)*10
    ORDER BY decade
    """
    result = conn.query(query)
    return result.values.tolist()

def get_first_ascensionist_areas(conn, name, user_id=None, year_start=None, year_end=None):
    """
    Get the areas where a first ascensionist was most active
    Returns: List of (area_name, count) tuples
    """
    query = f"""
    {get_deduped_ticks_cte(user_id, year_start=year_start, year_end=year_end)}
    SELECT 
        r.main_area as area_name,
        COUNT(*) as fa_count
    FROM analysis.fa fa
    JOIN routes.routes r ON fa.route_id = r.id
    JOIN deduped_ticks t on t.route_id = fa.route_id
    WHERE fa_type IN ('FA', 'FFA', 'FCA')
    {add_fa_name_filter(name, use_where=False)}
    {add_user_filter(user_id)}
    GROUP BY r.main_area
    ORDER BY fa_count DESC
    LIMIT 10
    """
    result = conn.query(query)
    return result.values.tolist()

def get_first_ascensionist_grades(conn, name, user_id=None, year_start=None, year_end=None):
    """
    Get distribution of grades for a first ascensionist
    Returns: List of (grade, count) tuples
    """
    query = f"""
    {get_deduped_ticks_cte(user_id, year_start=year_start, year_end=year_end)}
    SELECT 
        r.yds_rating,
        COUNT(*) as route_count
    FROM analysis.fa fa
    JOIN routes.routes r ON fa.route_id = r.id
    JOIN deduped_ticks t on t.route_id = fa.route_id
    WHERE fa_type IN ('FA', 'FFA', 'FCA')
    {add_fa_name_filter(name, use_where=False)}
    {add_user_filter(user_id)}
    AND r.yds_rating IS NOT NULL
    GROUP BY r.yds_rating
    ORDER BY count(*) desc
    """
    result = conn.query(query)
    return result.values.tolist()

def get_collaborative_ascensionists(conn, name, user_id=None, year_start=None, year_end=None):
    """
    Find climbers who frequently did first ascents with given climber
    Returns: List of (partner_name, count) tuples
    """
    if name == "All FAs":
        # Query for most frequent partnerships overall
        query = f"""
        {get_deduped_ticks_cte(user_id, year_start=year_start, year_end=year_end)},
        partnerships AS (
            SELECT 
                LEAST(a1.fa_name, a2.fa_name) as climber1,
                GREATEST(a1.fa_name, a2.fa_name) as climber2,
                a1.route_id
            FROM analysis.fa a1
            JOIN analysis.fa a2 ON a1.route_id = a2.route_id 
                AND a1.fa_type = a2.fa_type
                AND a1.fa_name != a2.fa_name
            JOIN deduped_ticks t on t.route_id = a1.route_id
            WHERE a1.fa_type IN ('FA', 'FFA', 'FCA')
            {add_user_filter(user_id)}
        )
        SELECT 
            CONCAT(climber1, ' & ', climber2) as partnership,
            COUNT(DISTINCT route_id) as partnership_count
        FROM partnerships
        GROUP BY climber1, climber2
        HAVING COUNT(DISTINCT route_id) > 1
        ORDER BY partnership_count DESC
        LIMIT 10;
        """
    else:
        query = f"""
        WITH same_routes AS (
            SELECT DISTINCT a1.route_id, a2.fa_name as partner_name
            FROM analysis.fa a1
            JOIN analysis.fa a2 ON a1.route_id = a2.route_id 
                AND a1.fa_type = a2.fa_type
                AND a1.fa_name != a2.fa_name
            JOIN routes.ticks t on t.route_id = a1.route_id
            WHERE a1.fa_type IN ('FA', 'FFA', 'FCA')
            {add_fa_name_filter(name, use_where=False, table_alias='a1')}
            {add_user_filter(user_id)}
        )
        SELECT 
            partner_name,
            COUNT(*) as partnership_count
        FROM same_routes
        GROUP BY partner_name
        HAVING COUNT(*) > 1
        ORDER BY partnership_count DESC
        LIMIT 10;
        """
    result = conn.query(query)
    return result.values.tolist()


def get_fa_routes(conn, fa_name, user_id, year_start=None, year_end=None):
    """Get all routes where person was FA."""
    query = f"""
    {get_deduped_ticks_cte(user_id, year_start=year_start, year_end=year_end)}
    SELECT CONCAT_WS(' ~ ',
        r.route_name,
        CONCAT_WS(' > ',
            r.main_area
        ),
        TRIM(NULLIF(CONCAT_WS(' ',
            r.yds_rating,
            r.hueco_rating,
            r.aid_rating,
            r.danger_rating,
            r.commitment_grade
        ), ''))
) as route_display
    FROM analysis.fa
    JOIN routes.routes r on r.id = fa.route_id
    JOIN deduped_ticks t on t.route_id = fa.route_id
    {add_fa_name_filter(fa_name, use_where=True)}
    {add_user_filter(user_id, table_alias = 't')}
    ORDER BY r.avg_stars DESC
    """
    result = conn.query(query)
    return result.values.tolist()


def get_partnership_routes(conn, fa_name, partner_name, user_id, year_start=None, year_end=None):
    """
    Get routes where both climbers were FAs together.
    
    Args:
        conn: Database connection
        fa_name: Name of the primary FA
        partner_name: Name of the partner FA
        user_id: User ID for filtering
    
    Returns:
        List of routes done together
    """
    query = f"""
    {get_deduped_ticks_cte(user_id, year_start=year_start, year_end=year_end)}
    SELECT
        CONCAT_WS(' ~ ',
            r.route_name,
            CONCAT_WS(' > ',
                r.main_area
            ),
            TRIM(NULLIF(CONCAT_WS(' ',
                r.yds_rating,
                r.hueco_rating,
                r.aid_rating,
                r.danger_rating,
                r.commitment_grade
            ), ''))
        ) as route_display
    FROM routes.routes r
    JOIN analysis.fa fa1 ON r.id = fa1.route_id
    JOIN analysis.fa fa2 ON r.id = fa2.route_id
    JOIN deduped_ticks t on t.route_id = r.id
    WHERE fa1.fa_name = '{fa_name.replace("'", "''")}'
    AND fa2.fa_name = '{partner_name.replace("'", "''")}'
    AND fa1.fa_type = fa2.fa_type
    AND t.user_id = '{user_id}'
    ORDER BY r.avg_stars DESC
    """
    return conn.query(query).values.tolist()