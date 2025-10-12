import os

import pandas as pd
from utils.util import connect_to_db


def read_sql_file(filename):
    """Read SQL queries from a file"""
    with open(filename, 'r') as f:
        # Split on semicolon and remove empty queries
        queries = [q.strip() for q in f.read().split(';') if q.strip()]
    return queries

def main():
    # Connect to database
    conn = connect_to_db()
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Read SQL queries
    sql_path = os.path.join(script_dir, '..', 'SQL', 'publication_counts_by_period.sql')
    queries = read_sql_file(sql_path)
    
    # Execute queries and save results
    try:
        # During residency query (first query)
        during_df = pd.read_sql_query(queries[0], conn)
        
        # Post residency query (second query)
        post_df = pd.read_sql_query(queries[1], conn)
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(script_dir, '..', 'Data Analysis')
        os.makedirs(output_dir, exist_ok=True)
        
        # Save to CSV files
        during_df.to_csv(os.path.join(output_dir, 'new_during_residency.csv'), index=False)
        post_df.to_csv(os.path.join(output_dir, 'new_post_residency.csv'), index=False)
        
        print(f"Successfully saved data files:")
        print(f"During residency data: {len(during_df)} records")
        print(f"Post residency data: {len(post_df)} records")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
