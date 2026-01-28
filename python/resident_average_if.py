"""
Compute average journal impact factor per resident.

Outputs:
- Console summary (top/bottom residents by average IF)
- CSV file: resident_avg_if.csv with resident name, publications counted, average IF

Requirements:
- Journals should have avg_impact_factor populated (see update_journal_impact_factors.py)
"""

import csv
import pyodbc
from pathlib import Path

CONN_STR = 'DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE=integrated_resident_project;UID=admin;'

OUTPUT_CSV = Path(__file__).parent / 'resident_avg_if.csv'


def fetch_resident_if(cursor):
    query = '''
        SELECT r.id,
               r.first_name,
               r.last_name,
               COUNT(j.avg_impact_factor) AS pub_count,
               AVG(j.avg_impact_factor) AS avg_if
        FROM resident r
        JOIN author a ON a.resident_id = r.id
        JOIN author_publication ap ON ap.author_id = a.id
        JOIN publication p ON p.id = ap.publication_id
        JOIN journal j ON j.id = p.journal_id
        WHERE j.avg_impact_factor IS NOT NULL
        GROUP BY r.id, r.first_name, r.last_name
        HAVING pub_count > 0
        ORDER BY avg_if DESC;
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    results = []
    for row in rows:
        resident_id, first_name, last_name, pub_count, avg_if = row
        results.append({
            'resident_id': resident_id,
            'name': f"{first_name} {last_name}",
            'pub_count': int(pub_count),
            'avg_if': float(avg_if) if avg_if is not None else None,
        })
    return results


def write_csv(data):
    with OUTPUT_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['resident_id', 'name', 'pub_count', 'avg_if'])
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def print_summary(data, top_n=5):
    if not data:
        print("No residents with impact factors found.")
        return
    
    print("=" * 80)
    print("RESIDENT AVERAGE IMPACT FACTORS")
    print("=" * 80)
    print(f"Residents with IF data: {len(data)}")
    
    # Overall average across residents (mean of resident averages)
    overall_avg = sum(r['avg_if'] for r in data if r['avg_if'] is not None) / len(data)
    print(f"Mean of resident averages: {overall_avg:.2f}\n")
    
    print(f"Top {min(top_n, len(data))} by average IF:")
    for row in data[:top_n]:
        print(f"  {row['name']}: avg IF={row['avg_if']:.2f} (n={row['pub_count']})")
    
    print(f"\nBottom {min(top_n, len(data))} by average IF:")
    for row in reversed(data[-top_n:]):
        print(f"  {row['name']}: avg IF={row['avg_if']:.2f} (n={row['pub_count']})")


def main():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    data = fetch_resident_if(cursor)
    write_csv(data)
    print_summary(data)
    conn.close()
    print(f"\nCSV saved to: {OUTPUT_CSV}")


if __name__ == '__main__':
    main()
