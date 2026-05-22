import duckdb
import pandas as pd
from pathlib import Path

_HERE = Path(__file__).parent.resolve()
PARQUET_PATH = str(_HERE / "data" / "ma_firearms.parquet")

print(f"[load_data] PARQUET_PATH resolved to: {PARQUET_PATH}")

if not Path(PARQUET_PATH).exists():
    raise FileNotFoundError(
        f"[load_data] Parquet file not found at: {PARQUET_PATH}\n"
        f"  __file__ = {__file__}\n"
        f"  _HERE    = {_HERE}"
    )

def get_connection():
    con = duckdb.connect()
    con.execute(f"CREATE VIEW applications AS SELECT * FROM read_parquet('{PARQUET_PATH}')")
    return con

def _build_filters(app_types, municipality, zip_code):
    """Return (filter_clause, extra_params) for the common optional filters."""
    clauses = []
    params = []
    if municipality:
        clauses.append("AND licensing_authority = ?")
        params.append(municipality)
    if zip_code:
        clauses.append("AND applicant_zip = ?")
        params.append(zip_code)
    return " ".join(clauses), params

def get_yearly_counts(year_min, year_max, app_types, municipality=None, zip_code=None):
    con = get_connection()
    extra_filter, extra_params = _build_filters(app_types, municipality, zip_code)
    params = [year_min, year_max] + app_types + extra_params
    query = f"""
        SELECT year, COUNT(*) as applications
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        {extra_filter}
        GROUP BY year
        ORDER BY year
    """
    result = con.execute(query, params).df()
    con.close()
    return result

def get_type_counts(year_min, year_max, app_types, municipality=None, zip_code=None):
    con = get_connection()
    extra_filter, extra_params = _build_filters(app_types, municipality, zip_code)
    params = [year_min, year_max] + app_types + extra_params
    query = f"""
        SELECT year, application_type, COUNT(*) as applications
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        {extra_filter}
        GROUP BY year, application_type
        ORDER BY year
    """
    result = con.execute(query, params).df()
    con.close()
    return result

def get_processing_days(year_min, year_max, app_types, municipality=None, zip_code=None):
    con = get_connection()
    extra_filter, extra_params = _build_filters(app_types, municipality, zip_code)
    params = [year_min, year_max] + app_types + extra_params
    query = f"""
        SELECT year, MEDIAN(processing_days) as processing_days
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        AND processing_days > 0
        {extra_filter}
        GROUP BY year
        ORDER BY year
    """
    result = con.execute(query, params).df()
    con.close()
    return result

def get_zip_counts(year_min, year_max, app_types, municipality=None, zip_code=None):
    con = get_connection()
    extra_filter, extra_params = _build_filters(app_types, municipality, zip_code)
    params = [year_min, year_max] + app_types + extra_params
    query = f"""
        SELECT applicant_zip, COUNT(*) as applications
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        AND applicant_zip IS NOT NULL
        {extra_filter}
        GROUP BY applicant_zip
        ORDER BY applications DESC
    """
    result = con.execute(query, params).df()
    con.close()
    return result

def get_summary_stats(year_min, year_max, app_types, municipality=None, zip_code=None):
    con = get_connection()
    extra_filter, extra_params = _build_filters(app_types, municipality, zip_code)
    params = [year_min, year_max] + app_types + extra_params
    query = f"""
        SELECT
            COUNT(*) as total,
            COUNT(DISTINCT licensing_authority) as municipalities,
            MEDIAN(processing_days) as median_days
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        AND processing_days > 0
        {extra_filter}
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

def get_raw_data(year_min, year_max, app_types, municipality=None, zip_code=None, limit=10000):
    con = get_connection()
    extra_filter, extra_params = _build_filters(app_types, municipality, zip_code)
    params = [year_min, year_max] + app_types + extra_params
    query = f"""
        SELECT application_date, licensing_authority, applicant_city,
               license_type, application_type, sex, status, processing_days,
               applicant_zip
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        {extra_filter}
        LIMIT {limit}
    """
    result = con.execute(query, params).df()
    con.close()
    return result

def get_full_filtered_data(year_min, year_max, app_types, municipality=None, zip_code=None):
    con = get_connection()
    extra_filter, extra_params = _build_filters(app_types, municipality, zip_code)
    params = [year_min, year_max] + app_types + extra_params
    query = f"""
        SELECT *
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        {extra_filter}
    """
    result = con.execute(query, params).df()
    con.close()
    return result

def get_female_pct(year_min, year_max, app_types, municipality=None, zip_code=None):
    con = get_connection()
    extra_filter, extra_params = _build_filters(app_types, municipality, zip_code)
    params = [year_min, year_max] + app_types + extra_params
    query = f"""
        SELECT
            ROUND(
                COUNT(*) FILTER (WHERE sex = 'FEMALE') * 100.0
                / NULLIF(COUNT(*) FILTER (WHERE sex IN ('MALE', 'FEMALE')), 0),
            1) as female_pct
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        {extra_filter}
    """
    result = con.execute(query, params).fetchone()
    con.close()
    return result[0]

def get_yoy_change(year_min, year_max, app_types, municipality=None, zip_code=None):
    con = get_connection()
    extra_filter, extra_params = _build_filters(app_types, municipality, zip_code)
    params = [year_min, year_max] + app_types + extra_params
    query = f"""
        WITH yearly AS (
            SELECT year, COUNT(*) as applications
            FROM applications
            WHERE year >= ? AND year <= ?
            AND application_type IN ({','.join(['?']*len(app_types))})
            {extra_filter}
            GROUP BY year
            ORDER BY year
        )
        SELECT
            year,
            applications,
            ROUND(
                (applications - LAG(applications) OVER (ORDER BY year)) * 100.0
                / LAG(applications) OVER (ORDER BY year),
            1) as yoy_pct
        FROM yearly
        ORDER BY year
    """
    result = con.execute(query, params).df()
    con.close()
    return result.dropna(subset=["yoy_pct"])

def get_sex_counts(year_min, year_max, app_types, municipality=None, zip_code=None):
    con = get_connection()
    extra_filter, extra_params = _build_filters(app_types, municipality, zip_code)
    params = [year_min, year_max] + app_types + extra_params
    query = f"""
        SELECT year, sex, COUNT(*) as applications
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        AND sex IN ('MALE', 'FEMALE')
        {extra_filter}
        GROUP BY year, sex
        ORDER BY year
    """
    result = con.execute(query, params).df()
    con.close()
    return result

POPULATION_PATH = str(Path(__file__).parent / "data" / "raw" / "ma_population.csv")

_SUFFIX_STRIP = [
    " POLICE DEPARTMENT",
    " POLICE DEPT",
    " POLICE",
    " PD",
]

_MANUAL_MAP = {
    "ATTLEBOROUGH": "ATTLEBORO",
    "MANCHESTER": "MANCHESTER-BY-THE-SEA",
}

_EXCLUDE = {"CRIMINAL HISTORY SYSTEMS BOARD", "MASS STATE POLICE"}

def _normalize_authority(name):
    upper = name.upper().strip()
    for suffix in _SUFFIX_STRIP:
        if upper.endswith(suffix):
            upper = upper[: -len(suffix)].strip()
            break
    return _MANUAL_MAP.get(upper, upper)

def get_licenses_per_capita(year_min, year_max, app_types, municipality=None):
    pop = pd.read_csv(POPULATION_PATH)
    pop = pop[
        pop["towns"].notna() &
        pop["population"].notna() &
        ~pop["towns"].str.contains("BY POPULATION", na=False) &
        ~pop["towns"].str.contains("COMMUNITY", na=False)
    ].drop_duplicates(subset="towns").copy()
    pop["join_key"] = pop["towns"].str.upper().str.strip()

    con = get_connection()
    muni_filter = "AND licensing_authority = ?" if municipality else ""
    params = [year_min, year_max] + app_types
    if municipality:
        params.append(municipality)
    query = f"""
        SELECT licensing_authority, COUNT(*) as applications
        FROM applications
        WHERE year >= ? AND year <= ?
        AND application_type IN ({','.join(['?']*len(app_types))})
        AND licensing_authority IS NOT NULL
        {muni_filter}
        GROUP BY licensing_authority
        ORDER BY applications DESC
    """
    apps = con.execute(query, params).df()
    con.close()

    apps = apps[~apps["licensing_authority"].isin(_EXCLUDE)].copy()
    apps["join_key"] = apps["licensing_authority"].apply(_normalize_authority)

    merged = apps.merge(pop[["join_key", "population"]], on="join_key", how="inner")
    merged["applications_per_1000"] = (
        (merged["applications"] / merged["population"] * 1000).round(1)
    )
    return merged.sort_values("applications_per_1000", ascending=False).reset_index(drop=True)
