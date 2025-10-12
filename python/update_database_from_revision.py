from collections import defaultdict

import pandas as pd
import pyodbc
from openpyxl import Workbook, load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from utils.constants import (AUTHOR, AUTHOR_PUBLICATION, FELLOWSHIP, JOURNAL,
                             MEDICAL_SCHOOL, POST_RESIDENCY_CAREER,
                             PUBLICATION, RESIDENCY, RESIDENT, TABLES)
from utils.delete_document import (delete_publication,
                                   delete_resident_publications)
from utils.insert_document import (find_author_in_authors_list,
                                   insert_pubmed_full_article)
from utils.select_functions import (insert_if_not_exists, select_from_table,
                                    select_with_condition)
from utils.util import (connect_to_db, format_query_string, name_permeatations,
                        retry_on_error)


def parse_publications_from_json(json_data):
    publications = []
    for author, data in json_data.items():
        for action_obj in data['actions']:
            action = action_obj['action']
            for paper in action_obj['papers']:
                publications.append({
                    'author': author,
                    'title': paper['title'],
                    'journal': paper['journal'],
                    'action': action
                })
    return publications

def group_by_author(publications):
    author_pubs = defaultdict(list)
    for pub in publications:
        author_pubs[pub['author']].append(pub)
    return author_pubs

def process_author_publications(cursor, resident, publications):
    # First, organize publications by action type
    publications_by_action = {
        'KEEP': [],
        'DELETE': [],
        'ADD': []
    }
    
    for pub in publications:
        if pub['action'] in publications_by_action:
            publications_by_action[pub['action']].append(pub)

    # Process DELETE publications first if there are no KEEP actions
    if not publications_by_action['KEEP'] and publications_by_action['DELETE']:
        print(f"Deleting specific publications for {resident.full_name}:")
        for pub in publications_by_action['DELETE']:
            print(f"  - {pub['title']}")
            delete_publication(cursor, resident.id, pub['title'], pub['journal'])
            
    # If there are KEEP publications, we want to keep only those and delete everything else
    elif publications_by_action['KEEP']:
        keep_titles = [pub['title'] for pub in publications_by_action['KEEP']]
        print(f"Keeping only these publications for {resident.full_name}:")
        for title in keep_titles:
            print(f"  - {title}")
          # First make sure these publications still exist
        found_titles = []
        for pub in publications_by_action['KEEP']:
            # Find publications matching the title using direct SQL for now
            cursor.execute(f"""
                SELECT p.id 
                FROM {TABLES['PUBLICATION']} p
                INNER JOIN {TABLES['AUTHOR_PUBLICATION']} ap ON p.id = ap.publication_id
                INNER JOIN {TABLES['AUTHOR']} a ON ap.author_id = a.id
                WHERE a.resident_id = ? AND p.topic = ?
            """, (resident.id, pub['title']))
            
            if cursor.fetchall():
                found_titles.append(pub['title'])
            else:
                print(f"Warning: Publication to keep not found: {pub['title']}")
        
        if not found_titles:
            print("Warning: None of the publications to keep were found!")
            return
            
        # Then delete everything else that's not in found_titles
        delete_resident_publications(cursor, resident.id, found_titles)
    
    # Process any ADD publications
    for pub in publications_by_action['ADD']:
        try:
            insert_pubmed_full_article(cursor, pub['title'], pub['journal'], resident.id)
        except Exception as e:
            print(f"Error adding publication for {resident.full_name}: {pub['title']}")
            print(f"Error: {e}")
            continue

def main():
    conn = connect_to_db()
    cursor = conn.cursor()

    # Read revised publications from JSON
    import json
    with open('t:\\Thomas\'s Stuff\\Code Projects\\Riya\\Documents\\publications_by_resident.json', 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    # Parse and group publications
    publications = parse_publications_from_json(json_data)
    author_publications = group_by_author(publications)

    # Get all residents (for matching)
    residents = select_from_table(cursor, TABLES["RESIDENT"], 
        [f"CONCAT(first_name, ' ', COALESCE(CONCAT(middle_name, ' '), ''), last_name) AS full_name", 
         "id",
         RESIDENT["FIRST_NAME"], 
         RESIDENT["LAST_NAME"], 
         RESIDENT["MIDDLE_NAME"],
         RESIDENT["ID"]])

    # Only process residents/authors that have actions in the txt file
    for author_name, pubs in author_publications.items():
        # Find the resident by full name
        resident = None
        for res in residents:
            if res.full_name.strip().lower() == author_name.strip().lower():
                resident = res
                break
        if not resident:
            print(f"Resident not found for author: {author_name}")
            continue

        # Only process if there is at least one action (KEEP, DELETE, ADD)
        has_action = any(pub['action'] in ('KEEP', 'DELETE', 'ADD') for pub in pubs)
        if not has_action:
            continue

        print(f"Processing publications for {author_name}")
        process_author_publications(cursor, resident, pubs)
        conn.commit()

    conn.close()

if __name__ == "__main__":
    main()
