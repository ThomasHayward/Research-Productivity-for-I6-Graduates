import json
from collections import defaultdict

from utils.constants import (AUTHOR, AUTHOR_PUBLICATION, PUBLICATION, RESIDENT,
                             TABLES)
from utils.select_functions import select_from_table
from utils.util import connect_to_db


def parse_publications_from_json(json_data):
    """Parse the JSON and count KEEP vs DELETE actions for each author"""
    author_actions = defaultdict(lambda: {'keep': 0, 'delete': 0})
    
    for author, data in json_data.items():
        for action_obj in data['actions']:
            action = action_obj['action']
            if action in ('KEEP', 'DELETE'):
                count = len(action_obj['papers'])
                if action == 'KEEP':
                    author_actions[author]['keep'] += count
                else:
                    author_actions[author]['delete'] += count
    
    return author_actions

def process_author_publications(cursor, resident, keep_count=None, delete_count=None):
    """
    Process publications based on counts:
    - If keep_count: Keep only the first N publications
    - If delete_count: Delete the first N publications
    """
    # Get all publications for this resident ordered by date
    cursor.execute(f"""
        SELECT p.id, p.topic, p.date_published
        FROM {TABLES['PUBLICATION']} p
        INNER JOIN {TABLES['AUTHOR_PUBLICATION']} ap ON p.id = ap.publication_id
        INNER JOIN {TABLES['AUTHOR']} a ON ap.author_id = a.id
        WHERE a.resident_id = ?
        ORDER BY p.date_published ASC, p.id ASC
    """, (resident.id,))
    
    publications = cursor.fetchall()
    total_pubs = len(publications)
    
    if total_pubs == 0:
        print(f"No publications found for {resident.full_name}")
        return
        
    if keep_count is not None:
        if keep_count >= total_pubs:
            print(f"Keeping all {total_pubs} publications for {resident.full_name}")
            return
            
        # Get IDs of publications to delete (after keep_count)
        pubs_to_delete = publications[keep_count:]
        delete_ids = [pub.id for pub in pubs_to_delete]
        
        print(f"Keeping first {keep_count} of {total_pubs} publications for {resident.full_name}")
        
        # Delete the author_publication entries
        id_list = ','.join(str(id) for id in delete_ids)
        cursor.execute(f"""
            DELETE ap
            FROM {TABLES['AUTHOR_PUBLICATION']} ap
            INNER JOIN {TABLES['AUTHOR']} a ON ap.author_id = a.id
            WHERE a.resident_id = ?
            AND ap.publication_id IN ({id_list})
        """, (resident.id,))
        
    elif delete_count is not None:
        if delete_count >= total_pubs:
            print(f"Would delete all {total_pubs} publications for {resident.full_name}")
            delete_count = total_pubs
            
        # Get IDs of publications to delete (first delete_count)
        pubs_to_delete = publications[:delete_count]
        delete_ids = [pub.id for pub in pubs_to_delete]
        
        print(f"Deleting first {delete_count} of {total_pubs} publications for {resident.full_name}")
        
        # Delete the author_publication entries
        id_list = ','.join(str(id) for id in delete_ids)
        cursor.execute(f"""
            DELETE ap
            FROM {TABLES['AUTHOR_PUBLICATION']} ap
            INNER JOIN {TABLES['AUTHOR']} a ON ap.author_id = a.id
            WHERE a.resident_id = ?
            AND ap.publication_id IN ({id_list})
        """, (resident.id,))
    
    # Clean up orphaned publications
    cursor.execute(f"""
        DELETE p
        FROM {TABLES['PUBLICATION']} p
        LEFT JOIN {TABLES['AUTHOR_PUBLICATION']} ap ON p.id = ap.publication_id
        WHERE ap.publication_id IS NULL
    """)

def main():
    conn = connect_to_db()
    cursor = conn.cursor()

    # Read revised publications from JSON
    with open('t:\\Thomas\'s Stuff\\Code Projects\\Riya\\Documents\\publications_by_resident.json', 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    # Parse and count actions by author
    author_actions = parse_publications_from_json(json_data)

    # Get all residents
    residents = select_from_table(cursor, TABLES["RESIDENT"], 
        [f"CONCAT(first_name, ' ', COALESCE(CONCAT(middle_name, ' '), ''), last_name) AS full_name", 
         "id",
         RESIDENT["FIRST_NAME"], 
         RESIDENT["LAST_NAME"], 
         RESIDENT["MIDDLE_NAME"],
         RESIDENT["ID"]])

    # Process each author's actions
    for author_name, actions in author_actions.items():
        # Find the resident by full name
        resident = None
        for res in residents:
            if res.full_name.strip().lower() == author_name.strip().lower():
                resident = res
                break
        
        if not resident:
            print(f"Resident not found for author: {author_name}")
            continue

        print(f"\nProcessing publications for {author_name}")
        print(f"Actions: Keep={actions['keep']}, Delete={actions['delete']}")
        
        # Calculate net action
        if actions['keep'] > 0 and actions['delete'] > 0:
            # If both keep and delete present, calculate net effect
            net_keep = actions['keep'] - actions['delete']
            if net_keep > 0:
                print(f"Net action: Keep first {net_keep} publications")
                process_author_publications(cursor, resident, keep_count=net_keep)
            elif net_keep < 0:
                print(f"Net action: Delete first {abs(net_keep)} publications")
                process_author_publications(cursor, resident, delete_count=abs(net_keep))
            else:
                print("Net action: No changes needed")
        elif actions['keep'] > 0:
            # Only keep actions
            process_author_publications(cursor, resident, keep_count=actions['keep'])
        elif actions['delete'] > 0:
            # Only delete actions
            process_author_publications(cursor, resident, delete_count=actions['delete'])
        
        conn.commit()

    conn.close()

if __name__ == "__main__":
    main()
