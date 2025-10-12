import logging
import re
import time
from functools import wraps
from gettext import find

import requests
from pymed import PubMed
from utils.constants import (AUTHOR, AUTHOR_PUBLICATION, FELLOWSHIP, JOURNAL,
                             MEDICAL_SCHOOL, POST_RESIDENCY_CAREER,
                             PUBLICATION, RESIDENCY, RESIDENT, TABLES)
from utils.insert_document import insert_pubmed_full_article
from utils.pubmed_helper import (PubMedQueryError, debug_pubmed_query,
                                 retry_pubmed_query)
from utils.select_functions import (insert_if_not_exists, select_from_table,
                                    select_with_condition)
from utils.util import (connect_to_db, format_query_string, name_permeatations,
                        retry_on_error)

pubmed = PubMed(tool="Integrated resident project", email="thomas-hayward@outlook.com")

conn = connect_to_db()
# Query the database to receive all resident names and match year
cursor = conn.cursor()
residents = select_from_table(cursor, TABLES["RESIDENT"], 
    [f"CONCAT(first_name, ' ', COALESCE(CONCAT(middle_name, ' '), ''), last_name) AS full_name", 
     RESIDENT["ID"], RESIDENT["MATCH_YEAR"], RESIDENT["GRAD_YEAR"], RESIDENT["FIRST_NAME"], RESIDENT["LAST_NAME"]])

# Process each resident
for resident in residents:
    # Check if resident already has publications by checking author and author_publication tables
    author = select_with_condition(cursor, TABLES["AUTHOR"], 
                                 conditions={AUTHOR["RESIDENT_ID"]: resident.id},
                                 fields=[AUTHOR["ID"]])  # Explicitly select the ID column
    if author:  # If we found an author record
        author_id = author[0][0]  # Get the ID from the first column
        print(author_id)
        # Check if this author has any publications
        existing_publications = select_with_condition(cursor, TABLES["AUTHOR_PUBLICATION"], 
                                                   {AUTHOR_PUBLICATION["AUTHOR_ID"]: author_id})
        if existing_publications:  # If we found any publications
            print(f"\nSkipping resident {resident.full_name} - already has publications")
            continue

    print(f"\nProcessing resident: {resident.full_name}, {resident.id}")
    resident.match_year = f"{resident.match_year}/07/01"
    
    # Get all name permutations for the resident
    name_variations = name_permeatations(resident.full_name)
    
    # Create and execute PubMed query
    query = format_query_string(name_variations, resident.match_year, 
                                {
                                    'AUTHOR': lambda name: f"{name}[AUTHOR]",
                                    'YEAR': lambda match_year: f"{match_year}:3000[Date - Publication]"
                                })

    try:
        results = retry_pubmed_query(pubmed, query, resident.full_name)
        time.sleep(2)
    except Exception as e:
        logging.error(f"Failed to query PubMed for resident {resident.full_name}: {str(e)}")
        continue

    for idx, article in enumerate(results, 1):
        # Safely check fields using getattr first
        journal = getattr(article, 'journal', None)
        title = getattr(article, 'title', None)
        publication_date = getattr(article, 'publication_date', None)
        authors = getattr(article, 'authors', None)
        doi = getattr(article, 'doi', None)

        required_fields = {
            'title': title,
            'publication_date': publication_date,
            'authors': authors,
            'journal': journal,
            'doi': doi
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value]
        
        if missing_fields:
            # logging.warning(f"Skipping article {idx} due to missing fields: {missing_fields}")
            continue

        try:
            retry_on_error()(insert_pubmed_full_article)(cursor=cursor, article=article, resident=resident, database='pubmed')
        except Exception as e:
            logging.error(f"Failed to insert article {idx}: {str(e)}")
            continue

cursor.close()
conn.close()

