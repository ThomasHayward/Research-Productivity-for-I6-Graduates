"""
Apply publication actions (ADD/DELETE/KEEP) to the database based on matching report.

Actions:
  - ADD: Insert new publications into database
  - DELETE: Remove publications from database
  - KEEP: Keep only these publications, delete all others for the resident
"""

import json
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import pyodbc


# Database connection
def get_connection():
    conn_str = 'DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE=integrated_resident_project;UID=admin;'
    return pyodbc.connect(conn_str)

def fuzzy_match_resident(doc_name, cursor):
    """Fuzzy match document resident name to database resident ID."""
    cursor.execute('SELECT id, first_name, last_name FROM resident')
    best_match_id = None
    best_score = 0
    
    for row in cursor:
        resident_id, first_name, last_name = row
        db_name = f"{first_name} {last_name}"
        score = SequenceMatcher(None, doc_name.lower(), db_name.lower()).ratio()
        if score > best_score:
            best_score = score
            best_match_id = resident_id
    
    return best_match_id if best_score > 0.80 else None

def get_or_create_author_id(cursor, resident_id):
    """Get or create author record for resident."""
    cursor.execute('SELECT id FROM author WHERE resident_id = ?', resident_id)
    result = cursor.fetchone()
    if result:
        return result[0]
    # Create new author record
    cursor.execute('INSERT INTO author (resident_id, affiliation) VALUES (?, ?)', (resident_id, ''))
    cursor.commit()
    cursor.execute('SELECT id FROM author WHERE resident_id = ?', resident_id)
    return cursor.fetchone()[0]

def get_journal_id(cursor, journal_name):
    """Get or create journal ID."""
    cursor.execute('SELECT id FROM journal WHERE name = ?', journal_name)
    result = cursor.fetchone()
    if result:
        return result[0]
    # Create new journal
    cursor.execute('INSERT INTO journal (name) VALUES (?)', journal_name)
    cursor.commit()
    cursor.execute('SELECT id FROM journal WHERE name = ?', journal_name)
    return cursor.fetchone()[0]

def insert_publication(cursor, resident_id, author_id, journal_id, title, doi=None, pub_date=None):
    """Insert a publication and link to resident."""
    try:
        # Insert publication
        cursor.execute(
            'INSERT INTO publication (journal_id, date_published, doi) VALUES (?, ?, ?)',
            (journal_id, pub_date, doi)
        )
        cursor.commit()
        
        # Get publication ID
        cursor.execute(
            'SELECT LAST_INSERT_ID() as id'
        )
        pub_id = cursor.fetchone()[0]
        
        # Link author (resident) to publication
        cursor.execute(
            'INSERT INTO author_publication (author_id, publication_id) VALUES (?, ?)',
            (author_id, pub_id)
        )
        cursor.commit()
        return True, pub_id
    except Exception as e:
        return False, str(e)

def delete_publication(cursor, author_id, journal_id, title):
    """Delete publication for an author."""
    try:
        # Find publication - first try exact match, then fuzzy
        cursor.execute(
            '''SELECT id FROM publication 
               WHERE journal_id = ?''',
            journal_id
        )
        results = cursor.fetchall()
        
        best_match_id = None
        best_score = 0
        
        for row in results:
            pub_id = row[0]
            cursor.execute('SELECT topic FROM publication WHERE id = ?', pub_id)
            pub_title = cursor.fetchone()[0]
            
            if pub_title.lower().strip() == title.lower().strip():
                best_match_id = pub_id
                best_score = 1.0
                break
            
            score = SequenceMatcher(None, title.lower().strip(), pub_title.lower().strip()).ratio()
            if score > best_score:
                best_score = score
                best_match_id = pub_id
        
        if best_match_id is None or best_score < 0.75:
            return False, f"Publication not found (best score: {best_score:.1%})"
        
        pub_id = best_match_id
        
        # Check if other authors have this publication
        cursor.execute(
            'SELECT COUNT(*) FROM author_publication WHERE publication_id = ?',
            pub_id
        )
        other_authors = cursor.fetchone()[0] - 1
        
        # Remove link from author
        cursor.execute(
            'DELETE FROM author_publication WHERE author_id = ? AND publication_id = ?',
            (author_id, pub_id)
        )
        cursor.commit()
        
        # If no other authors, delete publication
        if other_authors == 0:
            cursor.execute('DELETE FROM publication WHERE id = ?', pub_id)
            cursor.commit()
        
        return True, "Deleted"
    except Exception as e:
        return False, str(e)

def main():
    conn = get_connection()
    cursor = conn.cursor()
    
    report_path = Path(__file__).parent / "publication_matching_report.json"
    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    stats = {
        'ADD': {'success': 0, 'failed': 0},
        'DELETE': {'success': 0, 'failed': 0},
        'KEEP': {'success': 0, 'failed': 0, 'removed': 0}
    }
    
    print("=" * 80)
    print("APPLYING PUBLICATION ACTIONS TO DATABASE")
    print("=" * 80 + "\n")
    
    for resident_name, resident_data in sorted(report['residents'].items()):
        resident_id = fuzzy_match_resident(resident_name, cursor)
        if not resident_id:
            print(f"[WARN] {resident_name}: Resident not found in database")
            continue
        
        author_id = get_or_create_author_id(cursor, resident_id)
        
        keep_pub_ids = set()
        
        # Process ADD and DELETE actions
        for action in ['ADD', 'DELETE']:
            if action not in resident_data['actions']:
                continue
            
            action_data = resident_data['actions'][action]
            for paper in action_data['papers']:
                if paper['status'] != 'FOUND':
                    continue
                
                journal_id = get_journal_id(cursor, paper['journal'])
                
                if action == 'ADD':
                    success, result = insert_publication(
                        cursor, resident_id, author_id, journal_id, paper['title']
                    )
                    if success:
                        stats['ADD']['success'] += 1
                        keep_pub_ids.add(result)
                        print(f"[OK] {resident_name} [ADD] {paper['title'][:60]}...")
                    else:
                        stats['ADD']['failed'] += 1
                        print(f"[FAIL] {resident_name} [ADD] Failed: {result}")
                
                elif action == 'DELETE':
                    success, result = delete_publication(
                        cursor, author_id, journal_id, paper['title']
                    )
                    if success:
                        stats['DELETE']['success'] += 1
                        print(f"[OK] {resident_name} [DELETE] {paper['title'][:60]}...")
                    else:
                        stats['DELETE']['failed'] += 1
                        print(f"[FAIL] {resident_name} [DELETE] Failed: {result}")
        
        # Process KEEP action
        if 'KEEP' in resident_data['actions']:
            action_data = resident_data['actions']['KEEP']
            for paper in action_data['papers']:
                if paper['status'] == 'FOUND':
                    journal_id = get_journal_id(cursor, paper['journal'])
                    # Track which publications to keep
                    cursor.execute(
                        '''SELECT id FROM publication 
                           WHERE journal_id = ? AND topic = ?''',
                        (journal_id, paper['title'])
                    )
                    result = cursor.fetchone()
                    if result:
                        keep_pub_ids.add(result[0])
            
            # Delete all other publications for this author
            cursor.execute(
                '''SELECT publication_id FROM author_publication 
                   WHERE author_id = ?''',
                author_id
            )
            all_pubs = [row[0] for row in cursor.fetchall()]
            
            for pub_id in all_pubs:
                if pub_id not in keep_pub_ids:
                    # Remove link
                    cursor.execute(
                        'DELETE FROM author_publication WHERE author_id = ? AND publication_id = ?',
                        (author_id, pub_id)
                    )
                    
                    # Check if other authors have this publication
                    cursor.execute(
                        'SELECT COUNT(*) FROM author_publication WHERE publication_id = ?',
                        pub_id
                    )
                    other_count = cursor.fetchone()[0]
                    
                    if other_count == 0:
                        cursor.execute('DELETE FROM publication WHERE id = ?', pub_id)
                    
                    stats['KEEP']['removed'] += 1
            
            cursor.commit()
            stats['KEEP']['success'] += 1
            print(f"[OK] {resident_name} [KEEP] Kept {len(keep_pub_ids)} publications, removed {len(all_pubs) - len(keep_pub_ids)}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nADD:")
    print(f"  Success: {stats['ADD']['success']}")
    print(f"  Failed: {stats['ADD']['failed']}")
    print(f"\nDELETE:")
    print(f"  Success: {stats['DELETE']['success']}")
    print(f"  Failed: {stats['DELETE']['failed']}")
    print(f"\nKEEP:")
    print(f"  Success: {stats['KEEP']['success']}")
    print(f"  Removed: {stats['KEEP']['removed']}")

if __name__ == '__main__':
    main()
if __name__ == '__main__':
    main()
