import logging
import time
from functools import wraps
from gettext import find

import requests
from pymed import PubMed
from utils.constants import (AUTHOR, AUTHOR_PUBLICATION, FELLOWSHIP, JOURNAL,
                             MEDICAL_SCHOOL, POST_RESIDENCY_CAREER,
                             PUBLICATION, RESIDENCY, RESIDENT, TABLES)
from utils.insert_document import insert_pubmed_full_article
from utils.select_functions import (insert_if_not_exists, select_from_table,
                                    select_with_condition)
from utils.util import (connect_to_db, format_query_string, name_permeatations,
                        retry_on_error)

pubmed = PubMed(tool="Integrated resident project", email="thomas-hayward@outlook.com")

def retry_pubmed_query(pubmed, query, max_retries=3, base_delay=5):
    for attempt in range(max_retries):
        try:
            # Exponential backoff delay
            if attempt > 0:
                delay = base_delay * (2 ** (attempt - 1))
                logging.info(f"Waiting {delay} seconds before retry {attempt + 1}/{max_retries}")
                time.sleep(delay)
            
            return pubmed.query(query, max_results=10000)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logging.warning(f"Rate limit hit, attempt {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    logging.error("Max retries reached for rate limit")
                    raise
                continue
            raise
        except Exception as e:
            logging.error(f"Unexpected error querying PubMed: {str(e)}")
            raise

conn = connect_to_db()
# Query the database to receive all resident names and match year
cursor = conn.cursor()
residents = select_from_table(cursor, TABLES["RESIDENT"], 
    [f"CONCAT(first_name, ' ', COALESCE(CONCAT(middle_name, ' '), ''), last_name) AS full_name", 
     RESIDENT["ID"], RESIDENT["MATCH_YEAR"], RESIDENT["GRAD_YEAR"], RESIDENT["FIRST_NAME"], RESIDENT["LAST_NAME"]])

# Process each resident
for resident in residents:
    # print resident
    print(f"\nProcessing resident: {resident.full_name}, {resident.match_year}, {resident.grad_year}, {resident.id}")
    resident.match_year = f"{resident.match_year}/01/01"
    
    # Get all name permutations for the resident
    name_variations = name_permeatations(resident.full_name)
    
    # Create and execute PubMed query
    query = format_query_string(resident.full_name, resident.match_year, resident.grad_year, 
                                {
                                    'AUTHOR': lambda name: f"{name}[AUTHOR]",
                                    'YEAR': lambda match_year, grad_year: f"{match_year}:{grad_year}[Date - Publication]"
                                })
    try:
        results = retry_pubmed_query(pubmed, query)
        # Add a small delay between different residents to avoid rate limits
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

