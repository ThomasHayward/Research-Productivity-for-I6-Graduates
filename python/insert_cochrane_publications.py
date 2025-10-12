import pandas as pd
import pyodbc
from crossref.restful import Works
from utils.constants import RESIDENT, TABLES
from utils.select_functions import (insert_if_not_exists, select_from_table,
                                    select_with_condition)
from utils.util import (connect_to_db, format_query_string, name_permeatations,
                        retry_on_error)

works = Works()


# get all residents
def main():
    conn = connect_to_db()
    cursor = conn.cursor()
    
    # Query the database for residents
    residents = select_from_table(cursor, TABLES["RESIDENT"], 
        [f"CONCAT(first_name, ' ', COALESCE(CONCAT(middle_name, ' '), ''), last_name) AS full_name", 
         RESIDENT["ID"], RESIDENT["MATCH_YEAR"], RESIDENT["GRAD_YEAR"], 
         RESIDENT["FIRST_NAME"], RESIDENT["LAST_NAME"]])

    for resident in residents:
        print(f"\nProcessing resident: {resident.full_name}, {resident.id}")
        resident.match_year = f"{resident.match_year}/07/01"
        
        name_variations = name_permeatations(resident.full_name)
        
        w1 = works.query(author=resident.full_name)

        for article in w1:
            # print the artcile
            # print(f"Processing article: {article}")
            try:
                # Check if the author is in the article
                if not is_resident_author(resident, article):
                    # print(f"Skipping article - resident {resident.full_name} not found in author list")
                    continue
                # print success
                print(f"Resident {resident.full_name} found in article: {article['title']}")
                # retry_on_error()(insert_if_not_exists)(
                #     cursor=cursor, 
                #     article=article, 
                #     resident=resident, 
                #     database='crossref'
                # )
            except Exception as e:
                print(f"Failed to insert article: {str(e)}")
                continue

    cursor.close()
    conn.close()

def is_resident_author(resident, article):
    """Check if resident is in the article's author list by matching first and last names."""
    if 'author' not in article:
        return False
        
    for author in article['author']:
        # Get given (first) and family (last) names from author data
        given = author.get('given', '').lower()
        family = author.get('family', '').lower()
        
        # Compare with resident's names
        if (resident.first_name.lower() in given and 
            resident.last_name.lower() == family):
            return True
    return False

if __name__ == "__main__":
    main()
