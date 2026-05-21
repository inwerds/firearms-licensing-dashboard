import pandas as pd
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "ma_firearms.parquet"

def load_data():
    return pd.read_parquet(DATA_PATH)

if __name__ == "__main__":
    df = load_data()
    print(f"Loaded {len(df):,} rows")
    print("\nColumns:", df.columns.tolist())
    print("\nYear breakdown:")
    print(df["year"].value_counts().sort_index())
    print("\nApplication types:")
    print(df["application_type"].value_counts())
    print("\nSample processing days (median by year):")
    print(df.groupby("year")["processing_days"].median().round(1))
    print("\nZip sample:")
    print(df["applicant_zip"].sample(10).tolist())