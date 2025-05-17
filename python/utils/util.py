import logging
import time
from functools import wraps

import pyodbc


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

def connect_to_db():
    try:
        return pyodbc.connect('DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE={integrated_resident_project};UID=admin;')
    except pyodbc.Error as e:
        logging.error(f"Error connecting to MySQL: {e}")
        exit(1)

def name_permeatations(name):
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

def create_query_string(names, match_year, grad_year):
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


"""
Example format
pubmed: {
    "AUTHOR": lambda name: f"{name}[AUTHOR]",
    "YEAR": lambda match_year, grad_year: f"{match_year}:{grad_year}[Date - Publication]"
}
scopus: {
    "AUTHOR": lambda name: f"AUTHOR({name})",
    "YEAR": lambda match_year, grad_year: f"PUBYEAR >= {match_year} AND PUBYEAR <= {grad_year}"
}
"""
def format_query_string(name, match_year, grad_year, format=dict):
    AUTHOR = "AUTHOR"
    YEAR = "YEAR"
    queryString = ""
    queryString += f"({format['AUTHOR'](name)}) AND ({format['YEAR'](match_year, grad_year)}) OR "

    # for name in names:
    #     # Use the format dictionary to create the query string
    # Remove the last " OR "
    queryString = queryString[:-4]
    return queryString

def format_query_string_raw(author_string, year_string):
    queryString = ""
    queryString += f"({author_string}) AND ({year_string}) OR "
    # Remove the last " OR "
    queryString = queryString[:-4]
    return queryString