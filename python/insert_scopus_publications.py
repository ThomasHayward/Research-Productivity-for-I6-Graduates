import pandas as pd
import pybliometrics
import pybliometrics.scopus
import pyodbc
from pybliometrics.scopus import AuthorSearch, ScopusSearch
from utils.constants import (FELLOWSHIP, MEDICAL_SCHOOL, POST_RESIDENCY_CAREER,
                             RESIDENCY, RESIDENT, TABLES)
# from utils.insert_document import insert_scopus_full_article
from utils.select_functions import (insert_if_not_exists, insert_into_table,
                                    select_from_table, select_with_condition)
from utils.util import connect_to_db, name_permeatations, retry_on_error

# Connect to the MySQL database
conn = connect_to_db()
cursor = conn.cursor()

pybliometrics.scopus.init(config_dir='../pybliometrics.cfg')

def format_names_for_query(name):
    """
    Format names for Scopus query.
    """
    # Split the name into first and last names
    names = name.split()
    
    # Check if the name has a middle name
    if (len(names) == 1):
        firstName = names[0]
        middleName = ''
        lastName = ''
    elif (len(names) == 2):
        firstName = names[0]
        middleName = ''
        lastName = names[1]
    elif (len(names) == 3):
        firstName = names[0]
        middleName = names[1]
        lastName = names[2]
    elif (len(names) > 3):
        firstName = names[0]
        middleName = ' '.join(names[1:-1])
        lastName = names[-1]

    return {
        'first_name': firstName,
        'middle_name': middleName,
        'last_name': lastName
    }

def format_query_string(name_variations, match_year, grad_year, filters):
    """
    Format the query string for Scopus.
    """
    # Use the correct fields from name_variations
    query = " AND ".join([filters['AUTHOR'](name_variations['first_name'], name_variations['last_name'])])
    print(f"Query: {query}")
    # query += f" AND {filters['YEAR'](match_year, grad_year)}"
    return query

residents = select_from_table(cursor, TABLES["RESIDENT"], 
    [f"CONCAT(first_name, ' ', COALESCE(CONCAT(middle_name, ' '), ''), last_name) AS full_name", 
     RESIDENT["ID"], RESIDENT["MATCH_YEAR"], RESIDENT["GRAD_YEAR"], RESIDENT["FIRST_NAME"], RESIDENT["LAST_NAME"]])

for resident in residents:
    # print resident
    print(f"\nProcessing resident: {resident.full_name}, {resident.match_year}, {resident.grad_year}, {resident.id}")
    
    # Get all name permutations for the resident
    name_variations = format_names_for_query(resident.full_name)
    
    # Create and execute Scopus query
    query = format_query_string(
        name_variations, resident.match_year, resident.grad_year, 
        {
            'AUTHOR': lambda first, last: f"AUTHLASTNAME({last}) AND AUTHFIRST({first})",
            # 'YEAR': lambda match_year, grad_year: f"PUBYEAR >= {match_year} AND PUBYEAR <= {grad_year}"
        }
    )
    try:
        print(f"Querying Scopus with: {query}")
        results = ScopusSearch(query=query, refresh=True, subscriber=False)
        # print(f"Found {len(results.results)} results for {resident.full_name}")
        for result in results.results:
            date_published = getattr(result, 'coverDate', None)

            # Check if the date published is within the range of match_year and grad_year
            if date_published:
                year = int(date_published.split('-')[0])
                if year < int(resident.match_year) or year > int(resident.grad_year):
                    print(f"Skipping article published in {year} for {resident.full_name}")
                    continue

            # Extract fields
            title = getattr(result, 'title', None)
            doi = getattr(result, 'doi', None)


            journal_name = getattr(result, 'publicationName', None)
            aggregation_type = getattr(result, 'aggregationType', None)
            issn = getattr(result, 'issn', None)
            eissn = getattr(result, 'eIssn', None)
            author_names = getattr(result, 'author_names', None)
            creator = getattr(result, 'creator', None)
            affilname = getattr(result, 'affilname', None)

            # print the fields
            print(f"Title: {title}")
            print(f"DOI: {doi}")
            print(f"Date Published: {date_published}")
            print(f"Journal Name: {journal_name}")
            print(f"Aggregation Type: {aggregation_type}")
            print(f"ISSN: {issn}")
            print(f"EISSN: {eissn}")
            print(f"Author Names: {author_names}")
            print(f"Creator: {creator}")
            print(f"Affiliation Name: {affilname}")
            # insert_scopus_full_article(cursor, result)  # Uncomment this line to insert the article into the database
    except Exception as e:
        print(f"Error querying Scopus: {e}")
