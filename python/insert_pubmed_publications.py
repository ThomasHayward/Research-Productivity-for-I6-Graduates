import logging
import time
from functools import wraps
from gettext import find

import pyodbc
import requests
from pymed import PubMed
from utils.constants import (AUTHOR, AUTHOR_PUBLICATION, FELLOWSHIP, JOURNAL,
                             MEDICAL_SCHOOL, POST_RESIDENCY_CAREER,
                             PUBLICATION, RESIDENCY, RESIDENT, TABLES)
from utils.insert_document import insert_pubmed_full_article
from utils.select_functions import (insert_if_not_exists, select_from_table,
                                    select_with_condition)

# Connect to the MySQL database
try:
    conn = pyodbc.connect('DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE={integrated_resident_project};UID=admin;')
except pyodbc.Error as e:
    print(f"Error connecting to MySQL: {e}")
    exit(1)

pubmed = PubMed(tool="Integrated resident project", email="thomas-hayward@outlook.com")

def retry_on_error(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except pyodbc.Error as e:
                    retries += 1
                    if retries == max_retries:
                        logging.error(f"Failed after {max_retries} attempts: {str(e)}")
                        raise
                    logging.warning(f"Database error, attempt {retries}/{max_retries}: {str(e)}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

def retry_pubmed_query(pubmed, query, max_retries=3, base_delay=5):
    for attempt in range(max_retries):
        try:
            # Exponential backoff delay
            if attempt > 0:
                delay = base_delay * (2 ** (attempt - 1))
                logging.info(f"Waiting {delay} seconds before retry {attempt + 1}/{max_retries}")
                time.sleep(delay)
            
            return pubmed.query(query, max_results=5000)
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

def namePermeatations(name):
    """
    Given a name, return all possible permutations of the name.
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
    
    # Create a list of all possible permutations of the names using the guide above
    permutations = []

    permutations.append(f"{lastName} {firstName[0]}") # Doe J
    permutations.append(f"{lastName}, {firstName[0]}.") # Doe, J.
    permutations.append(f"{firstName} {lastName}") # Jane Doe
    permutations.append(f"{firstName[0]}. {lastName}") # J. Doe
    permutations.append(f"{lastName}, {firstName}") # Doe, Jane
    permutations.append(f"{firstName[0]}{lastName}") # JDoe

    if middleName:
        permutations.append(f"{lastName} {firstName[0]}{middleName[0]}") # Doe JM
        permutations.append(f"{lastName}, {firstName[0]}.{middleName[0]}.") # Doe, J.M.
        permutations.append(f"{firstName} {middleName} {lastName}") # Jane Marie Doe
        permutations.append(f"{firstName} {middleName}. {lastName}") # Jane M. Doe
        permutations.append(f"{firstName[0]}.{middleName[0]}. {lastName}") # J.M. Doe
        permutations.append(f"{firstName[0]}. {middleName[0]}. {lastName}") # J. M. Doe
        permutations.append(f"{lastName}, {firstName} {middleName}") # Doe, Jane Marie        

    return permutations

def createQueryString(names, match_year, grad_year):
    """
    Given a list of names, return a query string for PubMed.
    """
    queryString = ""
    for name in names:
        # Add the name to the query string with correct date range syntax
        queryString += f"({name}[Author] AND {match_year}:{grad_year}[Date - Publication]) OR "
    # Remove the last " OR "
    queryString = queryString[:-4]
    
    return queryString

# Query the database to receive all resident names and match year
cursor = conn.cursor()
results = select_from_table(cursor, TABLES["RESIDENT"], 
    [f"CONCAT(first_name, ' ', COALESCE(CONCAT(middle_name, ' '), ''), last_name) AS full_name", 
     RESIDENT["ID"], RESIDENT["MATCH_YEAR"], RESIDENT["GRAD_YEAR"], RESIDENT["FIRST_NAME"], RESIDENT["LAST_NAME"]])
residents = results

# Process each resident
for resident in residents:
    # print resident
    print(f"\nProcessing resident: {resident.full_name}, {resident.match_year}, {resident.grad_year}, {resident.id}")
    resident.match_year = f"{resident.match_year}/01/01"
    
    # Get all name permutations for the resident
    name_variations = namePermeatations(resident.full_name)
    
    # Create and execute PubMed query
    query = createQueryString(name_variations, resident.match_year, resident.grad_year)
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

