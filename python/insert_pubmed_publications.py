import json
import logging
import time
from pathlib import Path

from pymed import PubMed
from utils.constants import AUTHOR, AUTHOR_PUBLICATION, RESIDENT, TABLES
# from utils.insert_document import insert_pubmed_full_article
from utils.pubmed_helper import retry_pubmed_query
from utils.select_functions import select_from_table, select_with_condition
from utils.util import (connect_to_db, format_query_string, name_permeatations,
                        retry_on_error)

pubmed = PubMed(tool="Integrated resident project", email="thomas-hayward@outlook.com")

conn = connect_to_db()

cursor = conn.cursor()
residents = select_from_table(cursor, TABLES["RESIDENT"], 
    [f"CONCAT(first_name, ' ', COALESCE(CONCAT(middle_name, ' '), ''), last_name) AS full_name", 
     RESIDENT["ID"], RESIDENT["MATCH_YEAR"], RESIDENT["GRAD_YEAR"], RESIDENT["FIRST_NAME"], RESIDENT["LAST_NAME"]])

# Prepare JSON output (incremental, crash-safe)
output_path = Path(__file__).parent / "pubmed_residents_results.json"
def _load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    except Exception:
        return []

all_results = _load_json(output_path)
results_index = {item.get("resident_id"): item for item in all_results if item.get("resident_id")}

# Unresolved (errors or no valid publications)
unresolved_output_path = Path(__file__).parent / "pubmed_residents_unresolved.json"
unresolved_results = _load_json(unresolved_output_path)
unresolved_index = {item.get("resident_id"): item for item in unresolved_results if item.get("resident_id")}

def _flush():
    output_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    unresolved_output_path.write_text(json.dumps(unresolved_results, indent=2), encoding="utf-8")

for resident in residents:
    # Lookup author id (if exists) but do not skip; we are exporting JSON, not inserting
    author = select_with_condition(cursor, TABLES["AUTHOR"], 
                                 conditions={AUTHOR["RESIDENT_ID"]: resident.id},
                                 fields=[AUTHOR["ID"]]) 
    author_id = author[0][0] if author else None

    print(f"\nProcessing resident: {resident.full_name}, {resident.id}")
    resident.match_year = f"{resident.match_year}/07/01"
    
    name_variations = name_permeatations(resident.full_name)
    
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
        # Record unresolved error (do not add to main results)
        entry = {
            "resident_id": resident.id,
            "resident_name": resident.full_name,
            "author_id": author_id,
            "match_year": resident.match_year,
            "grad_year": resident.grad_year,
            "query": query,
            "reason": "query_failed",
            "error": str(e)
        }
        if resident.id not in unresolved_index:
            unresolved_results.append(entry)
            unresolved_index[resident.id] = entry
            _flush()
        continue

    publications = []
    skipped_missing_fields = 0
    for idx, article in enumerate(results, 1):
        journal = getattr(article, 'journal', None)
        title = getattr(article, 'title', None)
        publication_date = getattr(article, 'publication_date', None)
        authors = getattr(article, 'authors', None)
        doi = getattr(article, 'doi', None)
        pubmed_id = getattr(article, 'pubmed_id', None)
        abstract = getattr(article, 'abstract', None)

        required_fields = {
            'title': title,
            'publication_date': publication_date,
            'authors': authors,
            'journal': journal,
            'doi': doi
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            logging.warning(f"Skipping article {idx} due to missing fields: {missing_fields}")
            skipped_missing_fields += 1
            continue

        publications.append({
            "title": title,
            "journal": journal,
            "publication_date": str(publication_date),
            "doi": doi,
            "authors": [str(a) for a in authors] if isinstance(authors, (list, tuple)) else str(authors),
            "pubmed_id": pubmed_id,
            "abstract": abstract
        })

    if len(publications) == 0:
        # Record unresolved case (no valid publications)
        unresolved_entry = {
            "resident_id": resident.id,
            "resident_name": resident.full_name,
            "author_id": author_id,
            "match_year": resident.match_year,
            "grad_year": resident.grad_year,
            "query": query,
            "reason": "no_valid_publications",
            "skipped_missing_fields": skipped_missing_fields
        }
        if resident.id not in unresolved_index:
            unresolved_results.append(unresolved_entry)
            unresolved_index[resident.id] = unresolved_entry
        _flush()
    else:
        # Build resident entry
        entry = {
            "resident_id": resident.id,
            "resident_name": resident.full_name,
            "author_id": author_id,
            "match_year": resident.match_year,
            "grad_year": resident.grad_year,
            "query": query,
            "valid_count": len(publications),
            "skipped_missing_fields": skipped_missing_fields,
            "publications": publications
        }
        # Append if not already present; do not overwrite existing
        if resident.id not in results_index:
            all_results.append(entry)
            results_index[resident.id] = entry
        _flush()

cursor.close()
conn.close()

