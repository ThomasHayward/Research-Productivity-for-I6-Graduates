"""
Compute average journal impact factor per resident.

Outputs:
- Console summary (top/bottom residents by average IF)
- CSV file: resident_avg_if.csv with resident name, publications counted, average IF

Requirements:
- Journals should have avg_impact_factor populated (see update_journal_impact_factors.py)
"""

import csv
from pathlib import Path

import pyodbc

CONN_STR = 'DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE=integrated_resident_project;UID=admin;'

OUTPUT_CSV = Path(__file__).parent / 'resident_avg_if.csv'


def fetch_resident_if(cursor):
    query = '''
        SELECT r.id,
               r.first_name,
               r.last_name,
               COUNT(p.id) AS total_pubs,
               COUNT(CASE 
                   WHEN j.avg_impact_factor IS NOT NULL 
                   AND j.avg_impact_factor != '' 
                   AND j.avg_impact_factor REGEXP '^[0-9]+\\.?[0-9]*$'
                   THEN 1 END) AS pubs_with_valid_if,
               COUNT(CASE 
                   WHEN j.avg_impact_factor IN ('N/A', 'N/F', '')
                   OR j.avg_impact_factor IS NULL
                   THEN 1 END) AS pubs_without_if,
               AVG(CASE 
                   WHEN j.avg_impact_factor REGEXP '^[0-9]+\\.?[0-9]*$'
                   THEN CAST(j.avg_impact_factor AS DECIMAL(10,2))
                   ELSE NULL 
               END) AS avg_if
        FROM resident r
        JOIN author a ON a.resident_id = r.id
        JOIN author_publication ap ON ap.author_id = a.id
        JOIN publication p ON p.id = ap.publication_id
        LEFT JOIN journal j ON j.id = p.journal_id
        GROUP BY r.id, r.first_name, r.last_name
        HAVING total_pubs > 0
        ORDER BY avg_if DESC;
    '''
    cursor.execute(query)
    rows = cursor.fetchall()
    results = []
    for row in rows:
        resident_id, first_name, last_name, total_pubs, pubs_with_valid_if, pubs_without_if, avg_if = row
        results.append({
            'resident_id': resident_id,
            'name': f"{first_name} {last_name}",
            'total_pubs': int(total_pubs),
            'pubs_with_valid_if': int(pubs_with_valid_if),
            'pubs_without_if': int(pubs_without_if),
            'avg_if': float(avg_if) if avg_if is not None else None,
        })
    return results


def write_csv(data):
    with OUTPUT_CSV.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['resident_id', 'name', 'total_pubs', 'pubs_with_valid_if', 'pubs_without_if', 'avg_if'])
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def print_summary(data, top_n=5):
    if not data:
        print("No residents with publications found.")
        return
    
    # Separate data
    data_with_if = [r for r in data if r['avg_if'] is not None]
    data_without_if = [r for r in data if r['avg_if'] is None]
    
    print("=" * 80)
    print("RESIDENT AVERAGE IMPACT FACTORS")
    print("=" * 80)
    print(f"Total residents with publications: {len(data)}")
    print(f"Residents with valid IF data: {len(data_with_if)}")
    print(f"Residents with NO valid IF data: {len(data_without_if)}\n")
    
    if len(data_with_if) == 0:
        print("No residents with valid impact factors found.")
        return
    
    # Overall average across residents (mean of resident averages)
    overall_avg = sum(r['avg_if'] for r in data_with_if) / len(data_with_if)
    print(f"Mean of resident averages: {overall_avg:.2f}\n")
    
    # Calculate summary stats
    total_pubs = sum(r['total_pubs'] for r in data)
    total_valid_if = sum(r['pubs_with_valid_if'] for r in data)
    total_without_if = sum(r['pubs_without_if'] for r in data)
    print(f"Total publications: {total_pubs}")
    print(f"Publications with valid IF: {total_valid_if} ({100*total_valid_if/total_pubs:.1f}%)")
    print(f"Publications without valid IF: {total_without_if} ({100*total_without_if/total_pubs:.1f}%)\n")
    
    print(f"Top {min(top_n, len(data_with_if))} by average IF:")
    for row in data_with_if[:top_n]:
        print(f"  {row['name']}: avg IF={row['avg_if']:.2f} ({row['pubs_with_valid_if']}/{row['total_pubs']} pubs with IF)")
    
    print(f"\nBottom {min(top_n, len(data_with_if))} by average IF:")
    for row in reversed(data_with_if[-top_n:]):
        print(f"  {row['name']}: avg IF={row['avg_if']:.2f} ({row['pubs_with_valid_if']}/{row['total_pubs']} pubs with IF)")

    if data_without_if:
        print(f"\nResidents with publications but NO valid impact factors ({len(data_without_if)}):")
        for row in data_without_if[:10]:  # Show first 10
            print(f"  {row['name']}: {row['total_pubs']} pubs, all without valid IF")


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
