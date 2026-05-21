import pandas as pd
from pathlib import Path

# Path to your raw data folder
DATA_DIR = Path("data/raw")

FILES = [
    "Applications 01.01.06-12.31.14.csv",
    "Applications 01.01.15-12.31.21.csv",
    "Applications 01.01.22-12.31.22.csv",
    "Applications 01.01.23-12.31.23.csv",
    "Applications 01.01.24-12.31.24.csv",
]

def load_data():
    dfs = []
    for f in FILES:
        df = pd.read_csv(DATA_DIR / f, low_memory=False)
        dfs.append(df)
        print(f"  Loaded {f}: {len(df):,} rows")

    combined = pd.concat(dfs, ignore_index=True)
    print(f"\nCombined: {len(combined):,} total rows")

    # Normalize column names
    combined.columns = [
        c.strip().lower().replace(" ", "_") for c in combined.columns
    ]

    # Fix the typo: 'license_type' not 'license_type' with capital I
    combined = combined.rename(columns={"license_type": "license_type"})

    # Parse dates
    for col in ["application_date", "issue_date", "expiration_date", "denial_date"]:
        combined[col] = pd.to_datetime(combined[col], errors="coerce")

    # Derive useful columns
    combined["year"] = combined["application_date"].dt.year
    combined["month"] = combined["application_date"].dt.month
    combined["processing_days"] = (
        combined["issue_date"] - combined["application_date"]
    ).dt.days

    # Drop junk rows
    combined = combined[
        ~combined["license_type"].str.contains("Resi\ufffd", na=False)
    ]
    combined = combined[
        combined["application_type"].isin(["Renewal", "New", "Replacement"])
    ]

   # Fix date parsing warning
    for col in ["application_date", "issue_date", "expiration_date", "denial_date"]:
        combined[col] = pd.to_datetime(combined[col], format="mixed", errors="coerce")

    # Normalize zip codes to 5-digit strings
    combined["applicant_zip"] = (
        combined["applicant_zip"]
        .astype(str)           # convert everything to string first
        .str.strip()           # remove whitespace
        .str.replace(r'\.0$', '', regex=True)  # remove trailing .0 from floats
        .str.zfill(5)          # pad with leading zeros
        .where(combined["applicant_zip"].notna(), other=None)  # restore NaNs
    )    

    return combined


if __name__ == "__main__":
    df = load_data()
    print("\nColumn names:", df.columns.tolist())
    print("\nYear breakdown:")
    print(df["year"].value_counts().sort_index())
    print("\nLicense types:")
    print(df["license_type"].value_counts())
    print("\nApplication types:")
    print(df["application_type"].value_counts())
    print("\nSample processing days (median by year):")
    print(df.groupby("year")["processing_days"].median().round(1))

    # --- Add these lines ---
    print("\nZip sample after fix:")
    print(df["applicant_zip"].sample(10).tolist())
    print("Any still missing leading zero:", (df["applicant_zip"].str.len() < 5).sum())