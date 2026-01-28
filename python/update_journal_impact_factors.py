"""
Update journal table with 5-year impact factors from journal_metrics_results.json

This script:
1. Loads journal metrics from the JSON file
2. Matches journals in the database by name
3. Updates the avg_impact_factor column with the 5-year impact factor
"""

import json
from difflib import SequenceMatcher
from pathlib import Path

import pyodbc


def get_connection():
    conn_str = 'DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE=integrated_resident_project;UID=admin;'
    return pyodbc.connect(conn_str)

def normalize_name(name):
    """Normalize journal name for matching."""
    return name.lower().strip()

def fuzzy_match_journal(target_name, db_journals, threshold=0.85):
    """Find best matching journal in database."""
    target_norm = normalize_name(target_name)
    best_match_id = None
    best_score = 0
    
    for journal_id, db_name in db_journals.items():
        db_norm = normalize_name(db_name)
        
        # Try exact match first
        if target_norm == db_norm:
            return journal_id, 1.0
        
        # Fuzzy match
        score = SequenceMatcher(None, target_norm, db_norm).ratio()
        if score > best_score:
            best_score = score
            best_match_id = journal_id
    
    return (best_match_id, best_score) if best_score >= threshold else (None, best_score)

def parse_impact_factor(if_str):
    """Parse impact factor string to float."""
    if if_str == 'N/A' or not if_str:
        return None
    
    try:
        # Remove '<' prefix if present
        if_str = if_str.replace('<', '').strip()
        return float(if_str)
    except (ValueError, AttributeError):
        return None

def main():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Load journal metrics
    metrics_path = Path(__file__).parent / "journal_metrics_results.json"
    with open(metrics_path, 'r', encoding='utf-8') as f:
        metrics_data = json.load(f)
    
    # Load database journals
    cursor.execute('SELECT id, name FROM journal')
    db_journals = {row[0]: row[1] for row in cursor.fetchall()}
    
    print("=" * 80)
    print("UPDATING JOURNAL IMPACT FACTORS")
    print("=" * 80)
    print(f"\nLoaded {len(metrics_data)} journal metrics from JSON")
    print(f"Found {len(db_journals)} journals in database\n")
    
    stats = {
        'updated': 0,
        'skipped_no_if': 0,
        'skipped_no_match': 0,
        'failed': 0
    }
    
    for entry in metrics_data:
        requested_name = entry.get('requested_name')
        matched_title = entry.get('matched_title')
        if_5year_str = entry.get('if_5year')
        
        if not requested_name:
            continue
        
        # Parse 5-year impact factor
        if_5year = parse_impact_factor(if_5year_str)
        if if_5year is None:
            stats['skipped_no_if'] += 1
            print(f"- {requested_name}: No valid 5-year IF ({if_5year_str})")
            continue
        
        # Try to match to database journal
        journal_id, match_score = fuzzy_match_journal(requested_name, db_journals)
        
        if journal_id is None:
            stats['skipped_no_match'] += 1
            print(f"X {requested_name}: No match in database (best: {match_score:.1%})")
            continue
        
        # Update database
        try:
            cursor.execute(
                'UPDATE journal SET avg_impact_factor = ? WHERE id = ?',
                (if_5year, journal_id)
            )
            conn.commit()
            stats['updated'] += 1
            
            db_name = db_journals[journal_id]
            match_indicator = "=" if match_score == 1.0 else "~"
            print(f"{match_indicator} {requested_name} -> {db_name}: IF = {if_5year:.1f}")
            
        except Exception as e:
            stats['failed'] += 1
            print(f"! {requested_name}: Failed to update - {e}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Updated: {stats['updated']}")
    print(f"Skipped (no valid IF): {stats['skipped_no_if']}")
    print(f"Skipped (no match): {stats['skipped_no_match']}")
    print(f"Failed: {stats['failed']}")

if __name__ == '__main__':
    main()
if __name__ == '__main__':
    main()
