"""
Lab test repository — fetch reference ranges from DB.
Ported from features/lab_test/repository.py.
"""

from core.database import get_psycopg2_connection


def get_pcos_tests() -> list[dict]:
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT test_name, normal_range, pcos_indication, flag_threshold, flag_condition, abnormal_reason "
        "FROM pcos_tests;"
    )
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows


def get_pregnancy_tests() -> list[dict]:
    conn = get_psycopg2_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT hormone_name, pregnancy_role, flag_value, flag_condition, reason_for_change "
        "FROM pregnancy_tests;"
    )
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows
