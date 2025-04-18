from gettext import find

import pyodbc
from pymed import PubMed
from utils.constants import (AUTHOR, AUTHOR_PUBLICATION, FELLOWSHIP, JOURNAL,
                             MEDICAL_SCHOOL, POST_RESIDENCY_CAREER,
                             PUBLICATION, RESIDENCY, RESIDENT, TABLES)
from utils.selectFunctions import (insert_if_not_exists, select_from_table,
                                   select_with_condition)

# Connect to the MySQL database
try:
    conn = pyodbc.connect('DRIVER={MySQL ODBC 9.2 ANSI Driver};SERVER=localhost;DATABASE={integrated_resident_project};UID=admin;')
except pyodbc.Error as e:
    print(f"Error connecting to MySQL: {e}")
    exit(1)

pubmed = PubMed(tool="Integrated resident project", email="thomas-hayward@outlook.com")

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

def find_author_in_authors_list(author, authors):
    """
    Given an author and list of authors, return the index of the author in the list.
    """
    for i, a in enumerate(authors):
        if a["firstname"] == author.first_name and a["lastname"] == author.last_name:
            return i
    return -1


def get_author_ordership_from_list(author, authors):
    """
    Given a list of authors and author, return the order of authorship.
    """
    author_index = find_author_in_authors_list(author, authors)
    if author_index == 1:
        return '1st'
    elif author_index == 2:
        return '2nd'
    elif author_index == authors.__len__() - 1:
        return 'last',
    else:
        return 'mid'
            


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
    print(f"\nProcessing publications for: {resident.full_name}, {resident.match_year}")
    
    # Get all name permutations for the resident
    name_variations = namePermeatations(resident.full_name)
    
    # Create and execute PubMed query
    query = createQueryString(name_variations, resident.match_year, resident.grad_year)
    results = pubmed.query(query, max_results=5000)
    
    print(f"Found publications:")
    for article in results:
        print(f"- {article.title}")
        print(f"  Journal: {article.journal}")
        print(f"  Date: {article.publication_date}")
        print(f"  DOI: {article.doi}")
        print("---")

        # Insert journal and get its ID
        journal_name = article.journal
        insert_if_not_exists(cursor, TABLES["JOURNAL"], {JOURNAL["NAME"]: journal_name})
        journal_results = select_with_condition(cursor, TABLES["JOURNAL"], 
                                             conditions={JOURNAL["NAME"]: journal_name})
        journal_id = journal_results[0][0]

        # Insert publication and get its ID
        publication_data = {
            PUBLICATION["JOURNAL_ID"]: journal_id,
            PUBLICATION["DATE_PUBLISHED"]: article.publication_date,
            PUBLICATION["TOPIC"]: article.title,
            PUBLICATION["DOI"]: article.doi,
        }
        insert_if_not_exists(cursor, TABLES["PUBLICATION"], publication_data)
        publication_results = select_with_condition(cursor, TABLES["PUBLICATION"], 
                                                 conditions={PUBLICATION["TOPIC"]: publication_data[PUBLICATION["TOPIC"]]})
        publication_id = publication_results[0][0]

        # Insert author and get its ID
        author_data = {
            AUTHOR["RESIDENT_ID"]: resident.id,
            AUTHOR["H_INDEX"]: None,
            AUTHOR["AOA_STATUS"]: None,
            AUTHOR["RANK"]: None,
            AUTHOR["PROGRAM_DIRECTOR"]: None,
            AUTHOR["FIRST_ATTENDING_YEAR"]: resident.grad_year,
            # afilliation is article.authors[find_author_in_authors_list(resident, article.authors)][AUTHOR["AFFILIATION"]] or ''
            AUTHOR["AFFILIATION"]: article.authors[find_author_in_authors_list(resident, article.authors)][AUTHOR["AFFILIATION"]] if find_author_in_authors_list(resident, article.authors) != -1 else ''
        }
        # PRINT AUTHOR DATA and affiliation
        print(f"  Author data: {author_data}")
        print(f"  Author affiliation: {article.authors[find_author_in_authors_list(resident, article.authors)][AUTHOR["AFFILIATION"]]}")
        insert_if_not_exists(cursor, TABLES["AUTHOR"], {AUTHOR["RESIDENT_ID"]: author_data[AUTHOR["RESIDENT_ID"]], AUTHOR["FIRST_ATTENDING_YEAR"]: author_data[AUTHOR["FIRST_ATTENDING_YEAR"]], AUTHOR["AFFILIATION"]: author_data[AUTHOR["AFFILIATION"]]})
        author_results = select_with_condition(cursor, TABLES["AUTHOR"], 
                                            conditions={AUTHOR["RESIDENT_ID"]: author_data[AUTHOR["RESIDENT_ID"]]})
        author_id = author_results[0][0]

        # Insert author-publication relationship
        #print full name
        print(f"  Author: {resident.full_name}")
        # print(f"  article authors: {article.authors}")
        author_publication_data = {
            AUTHOR_PUBLICATION["AUTHOR_ID"]: author_id,
            AUTHOR_PUBLICATION["PUBLICATION_ID"]: publication_id,
            AUTHOR_PUBLICATION["ORDER_OF_AUTHORSHIP"]: get_author_ordership_from_list(resident, article.authors)
        }
        insert_if_not_exists(cursor, TABLES["AUTHOR_PUBLICATION"], author_publication_data)

    print(f"- {len(list(results))} results found")    

cursor.close()
conn.close()

