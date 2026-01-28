"""
Merge resident average impact factors into during and post-residency datasets.

Inputs (Data Analysis/):
- new_post_residency.csv
- new_during_residency.csv
- resident_avg_if.csv (columns: resident_id, name, pub_count, avg_if)

Outputs:
- new_post_residency_with_if.csv
- new_during_residency_with_if.csv
"""

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent

POST_FILE = BASE_DIR / "new_post_residency.csv"
DURING_FILE = BASE_DIR / "new_during_residency.csv"
IF_FILE = BASE_DIR / "resident_avg_if.csv"
POST_OUT = BASE_DIR / "new_post_residency_with_if.csv"
DURING_OUT = BASE_DIR / "new_during_residency_with_if.csv"


def merge_if(src_path: Path, if_df: pd.DataFrame, out_path: Path) -> pd.DataFrame:
    df = pd.read_csv(src_path)
    merged = df.merge(if_df[['resident_id', 'avg_if', 'pub_count']], on='resident_id', how='left')
    merged.to_csv(out_path, index=False)
    return merged


def main():
    if_df = pd.read_csv(IF_FILE)
    # Ensure resident_id is numeric for join robustness
    if_df['resident_id'] = pd.to_numeric(if_df['resident_id'], errors='coerce').astype('Int64')

    post = merge_if(POST_FILE, if_df, POST_OUT)
    during = merge_if(DURING_FILE, if_df, DURING_OUT)

    print("Merge complete")
    print(f"Post-residency rows: {len(post)}, with IF: {post['avg_if'].notna().sum()}")
    print(f"During-residency rows: {len(during)}, with IF: {during['avg_if'].notna().sum()}")
    print(f"Saved: {POST_OUT}")
    print(f"Saved: {DURING_OUT}")


if __name__ == "__main__":
    main()
