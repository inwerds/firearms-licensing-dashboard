import duckdb
import pandas as pd
from pathlib import Path

DB_PATH = str(Path(__file__).parent / "data" / "ma_firearms.db")

def get_connection():
    return duckdb.connect(DB_PATH, read_only=True)

def get_yearly_counts(year_min, year_max, app_types, municipality=None):
    con = get_connection()
    muni_filter = "AND licensing_authority = ?" if municipality else ""
    params = [year_min, year_max] + app_types
    if municipality:
        params.append(municipality)
    query = f"""
        SELECT year, COUNT(*) as applications
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        {muni_filter}
        GROUP BY year
        ORDER BY year
    """
    result = con.execute(query, params).df()
    con.close()
    return result

def get_type_counts(year_min, year_max, app_types, municipality=None):
    con = get_connection()
    muni_filter = "AND licensing_authority = ?" if municipality else ""
    params = [year_min, year_max] + app_types
    if municipality:
        params.append(municipality)
    query = f"""
        SELECT year, application_type, COUNT(*) as applications
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        {muni_filter}
        GROUP BY year, application_type
        ORDER BY year
    """
    result = con.execute(query, params).df()
    con.close()
    return result

def get_processing_days(year_min, year_max, app_types, municipality=None):
    con = get_connection()
    muni_filter = "AND licensing_authority = ?" if municipality else ""
    params = [year_min, year_max] + app_types
    if municipality:
        params.append(municipality)
    query = f"""
        SELECT year, MEDIAN(processing_days) as processing_days
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        AND processing_days > 0
        {muni_filter}
        GROUP BY year
        ORDER BY year
    """
    result = con.execute(query, params).df()
    con.close()
    return result

def get_zip_counts(year_min, year_max, app_types, municipality=None):
    con = get_connection()
    muni_filter = "AND licensing_authority = ?" if municipality else ""
    params = [year_min, year_max] + app_types
    if municipality:
        params.append(municipality)
    query = f"""
        SELECT applicant_zip, COUNT(*) as applications
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        AND applicant_zip IS NOT NULL
        {muni_filter}
        GROUP BY applicant_zip
        ORDER BY applications DESC
    """
    result = con.execute(query, params).df()
    con.close()
    return result

def get_summary_stats(year_min, year_max, app_types, municipality=None):
    con = get_connection()
    muni_filter = "AND licensing_authority = ?" if municipality else ""
    params = [year_min, year_max] + app_types
    if municipality:
        params.append(municipality)
    query = f"""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT licensing_authority) as municipalities,
            MEDIAN(processing_days) as median_days
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        AND processing_days > 0
        {muni_filter}
    """
    result = con.execute(query, params).fetchone()
    con.close()
    return {"total": result[0], "municipalities": result[1], "median_days": result[2]}

def get_municipalities():
    con = get_connection()
    result = con.execute("""
        SELECT DISTINCT licensing_authority 
        FROM applications 
        WHERE licensing_authority IS NOT NULL
        ORDER BY licensing_authority
    """).df()
    con.close()
    return result["licensing_authority"].tolist()

def get_raw_data(year_min, year_max, app_types, municipality=None, limit=10000):
    con = get_connection()
    muni_filter = "AND licensing_authority = ?" if municipality else ""
    params = [year_min, year_max] + app_types
    if municipality:
        params.append(municipality)
    query = f"""
        SELECT application_date, licensing_authority, applicant_city,
               license_type, application_type, sex, status, processing_days,
               applicant_zip
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        {muni_filter}
        LIMIT {limit}
    """
    result = con.execute(query, params).df()
    con.close()
    return result

def get_full_filtered_data(year_min, year_max, app_types, municipality=None):
    con = get_connection()
    muni_filter = "AND licensing_authority = ?" if municipality else ""
    params = [year_min, year_max] + app_types
    if municipality:
        params.append(municipality)
    query = f"""
        SELECT *
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        {muni_filter}
    """
    result = con.execute(query, params).df()
    con.close()
    return result

def get_sex_counts(year_min, year_max, app_types, municipality=None):
    con = get_connection()
    muni_filter = "AND licensing_authority = ?" if municipality else ""
    params = [year_min, year_max] + app_types
    if municipality:
        params.append(municipality)
    query = f"""
        SELECT year, sex, COUNT(*) as applications
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        AND sex IN ('MALE', 'FEMALE')
        {muni_filter}
        GROUP BY year, sex
        ORDER BY year
    """
    result = con.execute(query, params).df()
    con.close()
    return result