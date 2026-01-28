import os
import sys
from pathlib import Path

import pandas as pd
from utils.util import connect_to_db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def export_sql_to_csv(sql_file_path):
    with open(sql_file_path, 'r') as file:
        query = file.read()
    
    conn = connect_to_db()
    
    try:
        df = pd.read_sql_query(query, conn)
        
        sql_filename = Path(sql_file_path).stem
        export_path = Path(__file__).parent.parent / 'Exports' / f'{sql_filename}.csv'
        
        df.to_csv(export_path, index=False)
        print(f"Results exported to: {export_path}")
        
    except Exception as e:
        print(f"Error executing query: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":    
    export_sql_to_csv(os.path.join(os.path.dirname(__file__), '../SQL/number_publications_per_post_res_type.sql'))