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
    Handles multiple middle names and last names with forward slash.
    """
    names = name.split()
    
    # Handle different name lengths
    if len(names) == 1:
        firstName = names[0]
        middleNames = []
        lastName = ''
    elif len(names) == 2:
        firstName = names[0]
        middleNames = []
        lastName = names[1]
    else:
        firstName = names[0]
        lastName = names[-1]
        middleNames = names[1:-1]  # All names between first and last are middle names
    
    # Create middle name variations
    middleInitials = ''.join(name[0] for name in middleNames) if middleNames else ''
    middleName = ' '.join(middleNames) if middleNames else ''

    # Handle multiple last names separated by forward slash
    lastNames = lastName.split('/')
    permutations = []

    for last in lastNames:
        permutations.extend([
            f"{last} {firstName[0]}", # Doe J
            f"{last}, {firstName[0]}.", # Doe, J.
            f"{firstName} {last}", # Jane Doe
            f"{firstName[0]}. {last}", # J. Doe
            f"{last}, {firstName}", # Doe, Jane
            f"{firstName[0]}{last}" # JDoe
        ])

        if middleNames:
            permutations.extend([
                f"{last} {firstName[0]}{middleInitials}", # Doe JMK
                f"{last}, {firstName[0]}.{'.'.join(mi + '.' for mi in middleInitials)}", # Doe, J.M.K.
                f"{firstName} {middleName} {last}", # Jane Marie Kate Doe
                f"{firstName} {'.'.join(mi + '.' for mi in middleInitials)} {last}", # Jane M.K. Doe
                f"{firstName[0]}.{'.'.join(mi + '.' for mi in middleInitials)} {last}", # J.M.K. Doe
                f"{last}, {firstName} {middleName}" # Doe, Jane Marie Kate
            ])

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
def format_query_string(names, match_year, format=dict):
    AUTHOR = "AUTHOR"
    YEAR = "YEAR"
    queryString = ""

    for name in names:
    #     # Use the format dictionary to create the query string
        queryString += f"({format['AUTHOR'](name)}) AND ({format['YEAR'](match_year)}) OR "

    # Remove the last " OR "
    queryString = queryString[:-4]
    return queryString

def format_query_string_raw(author_string, year_string):
    queryString = ""
    queryString += f"({author_string}) AND ({year_string}) OR "
    # Remove the last " OR "
    queryString = queryString[:-4]
    return queryString