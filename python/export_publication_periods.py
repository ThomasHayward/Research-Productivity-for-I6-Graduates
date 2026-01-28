import os
from datetime import date

import pandas as pd
from utils.util import connect_to_db


def read_sql_file(filename):
    """Read SQL queries from a file"""
    with open(filename, 'r') as f:
        queries = [q.strip() for q in f.read().split(';') if q.strip()]
    return queries

def main():
    conn = connect_to_db()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    sql_path = os.path.join(script_dir, '..', 'SQL', 'publication_counts_by_period.sql')
    queries = read_sql_file(sql_path)
    
    try:
        during_df = pd.read_sql_query(queries[0], conn)
        post_df = pd.read_sql_query(queries[1], conn)

        def years_between(start_date: date, end_date: date) -> float:
            return (end_date - start_date).days / 365.25

        today = date.today()

        if not post_df.empty:
            resident_ids = tuple(post_df['resident_id'].unique().tolist())
            if len(resident_ids) == 1:
                resident_ids_sql = f"({resident_ids[0]})"
            else:
                resident_ids_sql = str(resident_ids)

            grad_query = f"""
                SELECT id AS resident_id, grad_year
                FROM resident
                WHERE id IN {resident_ids_sql}
            """
            grad_df = pd.read_sql_query(grad_query, conn)
            post_df = post_df.merge(grad_df, on='resident_id', how='left')

            def compute_years_post(gr):
                try:
                    gy = int(gr)
                    start = date(gy, 6, 30)
                    return max(years_between(start, today), 0.0)
                except Exception:
                    return 0.0

            post_df['years_post_graduation'] = post_df['grad_year'].apply(compute_years_post)
            post_df['publications_per_year'] = post_df.apply(
                lambda row: row['total_publications'] / row['years_post_graduation']
                if row['years_post_graduation'] and row['years_post_graduation'] > 0 else 0.0,
                axis=1
            )

        if not during_df.empty:
            resident_ids_during = tuple(during_df['resident_id'].unique().tolist())
            if len(resident_ids_during) == 1:
                resident_ids_sql_d = f"({resident_ids_during[0]})"
            else:
                resident_ids_sql_d = str(resident_ids_during)

            dur_query = f"""
                SELECT id AS resident_id, match_year, grad_year, duration
                FROM resident
                WHERE id IN {resident_ids_sql_d}
            """
            dur_df = pd.read_sql_query(dur_query, conn)
            during_df = during_df.merge(dur_df, on='resident_id', how='left')

            def compute_residency_years(row):
                try:
                    if pd.notna(row.get('duration')) and int(row['duration']) > 0:
                        return float(int(row['duration']))
                    my = int(row['match_year']) if pd.notna(row.get('match_year')) else None
                    gy = int(row['grad_year']) if pd.notna(row.get('grad_year')) else None
                    if my is not None and gy is not None and gy >= my:
                        return float(gy - my)
                except Exception:
                    pass
                return None

            during_df['years_during_residency'] = during_df.apply(compute_residency_years, axis=1)
            during_df['publications_per_year'] = during_df.apply(
                lambda row: row['total_publications'] / row['years_during_residency']
                if pd.notna(row['years_during_residency']) and row['years_during_residency'] > 0 else None,
                axis=1
            )
        
        output_dir = os.path.join(script_dir, '..', 'Data Analysis')
        os.makedirs(output_dir, exist_ok=True)
        
        during_df.to_csv(os.path.join(output_dir, 'new_during_residency.csv'), index=False)
        post_df.to_csv(os.path.join(output_dir, 'new_post_residency.csv'), index=False)
        
        print(f"Successfully saved data files:")
        print(f"During residency data: {len(during_df)} records (with rate column: {'publications_per_year' in during_df.columns})")
        print(f"Post residency data: {len(post_df)} records (with rate and years columns: {'publications_per_year' in post_df.columns and 'years_post_graduation' in post_df.columns})")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
