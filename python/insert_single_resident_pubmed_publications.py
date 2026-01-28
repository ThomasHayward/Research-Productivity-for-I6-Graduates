import logging
import time

import requests
from pymed import PubMed
from utils.constants import RESIDENT, TABLES
from utils.insert_document import (find_author_in_authors_list,
                                   insert_pubmed_full_article)
from utils.select_functions import select_with_condition
from utils.util import (connect_to_db, format_query_string, name_permeatations,
                        retry_on_error)

pubmed = PubMed(tool="Integrated resident project", email="thomas-hayward@outlook.com")

def retry_pubmed_query(pubmed, query, max_retries=3, base_delay=5):
    for attempt in range(max_retries):
        try:
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

def write_publications_to_file(resident_name, articles):
    """Write publication details to a file"""
    filename = f"publications_{resident_name.replace(' ', '_')}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Publications for {resident_name}\n")
        f.write("=" * 50 + "\n\n")
        
        for idx, article in enumerate(articles, 1):
            f.write(f"Article {idx}:\n")
            f.write(f"Title: {getattr(article, 'title', 'N/A')}\n")
            f.write(f"Journal: {getattr(article, 'journal', 'N/A')}\n")
            f.write(f"Date: {getattr(article, 'publication_date', 'N/A')}\n")
            f.write(f"DOI: {getattr(article, 'doi', 'N/A')}\n")
            f.write(f"Authors: {', '.join([str(author) for author in getattr(article, 'authors', [])])}\n")
            f.write("-" * 50 + "\n\n")

def main():
    resident_name = input("Enter the full name of the resident: ").strip()
    
    conn = connect_to_db()
    cursor = conn.cursor()
    
    residents = select_with_condition(
        cursor, 
        TABLES["RESIDENT"],
        fields=[
            f"CONCAT(first_name, ' ', COALESCE(CONCAT(middle_name, ' '), ''), last_name) AS full_name", 
            RESIDENT["ID"], 
            RESIDENT["MATCH_YEAR"], 
            RESIDENT["GRAD_YEAR"], 
            RESIDENT["FIRST_NAME"], 
            RESIDENT["LAST_NAME"]
        ],
        conditions={
            "CONCAT(first_name, ' ', COALESCE(CONCAT(middle_name, ' '), ''), last_name)": resident_name
        }
    )
    
    if not residents:
        print(f"No resident found with name: {resident_name}")
        return
    
    resident = residents[0]
    print(f"Found resident: {resident.full_name}")
    resident.match_year = f"{resident.match_year}/07/01"
    
    name_variations = name_permeatations(resident.full_name)
    query = format_query_string(
        name_variations, 
        resident.match_year,
        {
            'AUTHOR': lambda name: f"{name}[AUTHOR]",
            'YEAR': lambda match_year: f"{match_year}:3000[Date - Publication]"
        }
    )
    print(query)
    try:
        results = retry_pubmed_query(pubmed, query)
        valid_articles = []
        
        print("\n" + "=" * 80)
        print("ARTICLE FIELDS AND DATA:")
        print("=" * 80)
        
        for idx, article in enumerate(results, 1):
            print(f"\n--- Article {idx} ---")
            
            # Print all attributes of the article object
            for attr in dir(article):
                if not attr.startswith('_'):  # Skip private attributes
                    try:
                        value = getattr(article, attr)
                        if not callable(value):  # Skip methods
                            print(f"  {attr}: {value}")
                    except:
                        pass
            
            print("-" * 80)
            
            if not all(getattr(article, field, None) for field in ['title', 'publication_date', 'authors', 'journal']):
                print(f"  ⚠️ Missing required fields")
                continue

            author_idx = find_author_in_authors_list(resident, article.authors)
            if author_idx == -1:
                print(f"  ⚠️ Resident not found in author list")
                continue
            
            print(f"  ✓ Valid article - resident found at position {author_idx}")
            valid_articles.append(article)
            
            # COMMENTING OUT DATABASE INSERT FOR TESTING
            # retry_on_error()(insert_pubmed_full_article)(
            #     cursor=cursor, 
            #     article=article, 
            #     resident=resident, 
            #     database='pubmed'
            # )
        
        print("\n" + "=" * 80)
        if valid_articles:
            write_publications_to_file(resident.full_name, valid_articles)
            print(f"Found {len(valid_articles)} valid publications (NOT INSERTED). Results written to publications_{resident.full_name.replace(' ', '_')}.txt")
        else:
            print("No valid publications found for this resident")
            
    except Exception as e:
        print(f"Error processing publications: {str(e)}")
        try:
            results = retry_pubmed_query(pubmed, "${resident.full_name}[Author] AND ${resident.match_year}:3000[Date - Publication]")
            valid_articles = []
            
            print("\n" + "=" * 80)
            print("FALLBACK QUERY - ARTICLE FIELDS AND DATA:")
            print("=" * 80)
            
            for idx, article in enumerate(results, 1):
                print(f"\n--- Article {idx} ---")
                
                # Print all attributes of the article object
                for attr in dir(article):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(article, attr)
                            if not callable(value):
                                print(f"  {attr}: {value}")
                        except:
                            pass
                
                print("-" * 80)
                
                if not all(getattr(article, field, None) for field in ['title', 'publication_date', 'authors', 'journal']):
                    print(f"  ⚠️ Missing required fields")
                    continue

                author_idx = find_author_in_authors_list(resident, article.authors)
                if author_idx == -1:
                    print(f"  ⚠️ Resident not found in author list")
                    continue
                
                print(f"  ✓ Valid article - resident found at position {author_idx}")
                valid_articles.append(article)
                
                # COMMENTING OUT DATABASE INSERT FOR TESTING
                # retry_on_error()(insert_pubmed_full_article)(
                #     cursor=cursor, 
                #     article=article, 
                #     resident=resident, 
                #     database='pubmed'
                # )
            
            print("\n" + "=" * 80)
            if valid_articles:
                write_publications_to_file(resident.full_name, valid_articles)
                print(f"Found {len(valid_articles)} valid publications (NOT INSERTED). Results written to publications_{resident.full_name.replace(' ', '_')}.txt")
            else:
                print("No valid publications found for this resident")
        except Exception as e:
            print(f"Error processing publications: {str(e)}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()


