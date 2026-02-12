"""
Update journal table with 5-year impact factors from journal_metrics_results.json

This script:
1. Loads journal metrics from the JSON file
2. Updates the avg_impact_factor column with the 5-year impact factor using journal_id
"""

import json
from pathlib import Path

import pyodbc


def get_connection():
    conn_str = 'DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE=integrated_resident_project;UID=admin;'
    return pyodbc.connect(conn_str)

def parse_impact_factor(if_str):
    """Validate and clean impact factor string."""
    if not if_str or if_str.strip() == '':
        return None
    
    # Keep the string as-is, just clean it up
    return if_str.strip()

def main():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Load journal metrics
    metrics_path = Path(__file__).parent / "journal_metrics_results.json"
    with open(metrics_path, 'r', encoding='utf-8') as f:
        metrics_data = json.load(f)
    
    print("=" * 80)
    print("UPDATING JOURNAL IMPACT FACTORS")
    print("=" * 80)
    print(f"\nLoaded {len(metrics_data)} journal metrics from JSON\n")
    
    stats = {
        'updated': 0,
        'skipped_no_if': 0,
        'skipped_no_id': 0,
        'failed': 0
    }
    
    for entry in metrics_data:
        journal_id = entry.get('journal_id')
        requested_name = entry.get('requested_name')
        if_5year_str = entry.get('if_5year')
        
        if not journal_id:
            stats['skipped_no_id'] += 1
            print(f"- {requested_name}: No journal_id")
            continue
        
        # Validate impact factor
        if_5year = parse_impact_factor(if_5year_str)
        if if_5year is None:
            stats['skipped_no_if'] += 1
            print(f"- {requested_name}: No valid 5-year IF ({if_5year_str})")
            continue
        
        # Update database
        try:
            cursor.execute(
                'UPDATE journal SET avg_impact_factor = ? WHERE id = ?',
                (if_5year, journal_id)
            )
            conn.commit()
            stats['updated'] += 1
            print(f"✓ {requested_name} (ID: {journal_id}): IF = {if_5year}")
            
        except Exception as e:
            stats['failed'] += 1
            print(f"! {requested_name} (ID: {journal_id}): Failed - {e}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Updated: {stats['updated']}")
    print(f"Skipped (no valid IF): {stats['skipped_no_if']}")
    print(f"Skipped (no journal_id): {stats['skipped_no_id']}")
    print(f"Failed: {stats['failed']}")
    
if __name__ == '__main__':
    main()