import logging
import re
import time
from functools import wraps
from xml.etree import ElementTree

from Bio import Entrez
from utils.constants import (AUTHOR, AUTHOR_PUBLICATION, FELLOWSHIP, JOURNAL,
                             MEDICAL_SCHOOL, POST_RESIDENCY_CAREER,
                             PUBLICATION, RESIDENCY, RESIDENT, TABLES)
from utils.insert_document import insert_pubmed_full_article
from utils.select_functions import (insert_if_not_exists, select_from_table,
                                    select_with_condition)
from utils.util import (connect_to_db, format_query_string, name_permeatations,
                        retry_on_error)

Entrez.email = "thomas-hayward@outlook.com"  # Replace with your actual email

def clean_name(name):
    return re.sub(r'[\x00-\x1F\x7F]', '', name)

def retry_pubmed_query(query, max_retries=3, base_delay=5):
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                delay = base_delay * (2 ** (attempt - 1))
                logging.info(f"Waiting {delay} seconds before retry {attempt + 1}/{max_retries}")
                time.sleep(delay)

            search_handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=10000,
                usehistory="y"
            )
            search_results = Entrez.read(search_handle)
            search_handle.close()
            id_list = search_results["IdList"]

            if not id_list:
                return []

            fetch_handle = Entrez.efetch(
                db="pubmed",
                id=",".join(id_list),
                rettype="medline",
                retmode="xml"
            )
            fetch_results = fetch_handle.read()
            fetch_handle.close()
            # print the count of articles fetched
            logging.info(f"Fetched {len(id_list)} articles for query: {query}")
            return parse_pubmed_articles(fetch_results)

        except Exception as e:
            logging.error(f"Unexpected error querying PubMed: {str(e)}\nQuery: {query}")
            if attempt == max_retries - 1:
                raise

def parse_pubmed_articles(xml_data):
    articles = []
    root = ElementTree.fromstring(xml_data)
    for article in root.findall(".//PubmedArticle"):
        try:
            article_data = {}

            title_elem = article.find(".//ArticleTitle")
            article_data['title'] = title_elem.text if title_elem is not None else None

            journal_elem = article.find(".//Journal/Title")
            article_data['journal'] = journal_elem.text if journal_elem is not None else None

            date_elem = article.find(".//PubDate")
            if date_elem is not None:
                year_elem = date_elem.find("Year")
                medline_date = date_elem.find("MedlineDate")
                article_data['publication_date'] = year_elem.text if year_elem is not None else (medline_date.text if medline_date is not None else None)

            doi = None
            for id_elem in article.findall(".//ArticleId"):
                if id_elem.attrib.get("IdType") == "doi":
                    doi = id_elem.text
                    break
            article_data['doi'] = doi

            authors = []
            for author in article.findall(".//Author"):
                last = author.find("LastName")
                first = author.find("ForeName")
                if last is not None and first is not None:
                    authors.append(f"{first.text} {last.text}")
            article_data['authors'] = authors

            articles.append(article_data)
            # print(f"Parsed article: {article_data['title']} by {', '.join(article_data['authors'])} in {article_data['journal']} on {article_data['publication_date']}")
        except Exception as e:
            logging.warning(f"Error parsing article: {e}")
            continue

    return articles

def main():
    conn = connect_to_db()
    cursor = conn.cursor()

    residents = select_from_table(cursor, TABLES["RESIDENT"], 
        [f"CONCAT(first_name, ' ', COALESCE(CONCAT(middle_name, ' '), ''), last_name) AS full_name", 
         RESIDENT["ID"], RESIDENT["MATCH_YEAR"], RESIDENT["GRAD_YEAR"], RESIDENT["FIRST_NAME"], RESIDENT["LAST_NAME"]])

    for resident in residents:
        print(f"\nProcessing resident: {resident.full_name}, {resident.id}")

        resident.full_name = clean_name(resident.full_name)
        resident.match_year = f"{resident.match_year}/07/01"

        name_variations = name_permeatations(resident.full_name)

        query = format_query_string(name_variations, resident.match_year, 
                                    {
                                        'AUTHOR': lambda name: f"{name}[AUTHOR]",
                                        'YEAR': lambda match_year: f"{match_year}:3000[Date - Publication]"
                                    })

        try:
            results = retry_pubmed_query(query)
            time.sleep(2)
        except Exception as e:
            logging.error(f"Failed to query PubMed for resident {resident.full_name}: {str(e)}")
            continue
        # print the count of articles fetched
        print(f"Fetched {len(results)} articles for resident: {resident.full_name}")
        for idx, article_data in enumerate(results, 1):
            required_fields = ['title', 'publication_date', 'authors', 'journal', 'doi']
            if not all(article_data.get(field) for field in required_fields):
                continue

            # try:
            #     retry_on_error()(insert_pubmed_full_article)(
            #         cursor=cursor,
            #         article=article_data,
            #         resident=resident,
            #         database='pubmed'
            #     )
            # except Exception as e:
            #     logging.error(f"Failed to insert article {idx}: {str(e)}")
            #     continue

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
