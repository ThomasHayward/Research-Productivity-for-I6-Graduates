import pandas as pd
import pyodbc
from utils.constants import (FELLOWSHIP, MEDICAL_SCHOOL, POST_RESIDENCY_CAREER,
                             RESIDENCY, RESIDENT, TABLES)
from utils.select_functions import (insert_if_not_exists, insert_into_table,
                                    select_with_condition)


def connect_to_db():
    try:
        return pyodbc.connect('DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE={integrated_resident_project};UID=admin;')
    except pyodbc.Error as e:
        print(f"Error connecting to MySQL: {e}")
        exit(1)

def process_row(conn, row):
    # Clean and prepare data
    residency = row['Residency'].strip() if pd.notna(row['Residency']) else None
    medical_school = row['Medical_School'].strip() if pd.notna(row['Medical_School']) else None
    fellowship = row['Fellowship'].strip() if pd.notna(row['Fellowship']) else None
    post_residency_career = row['Post_Residency_Career'].strip() if pd.notna(row['Post_Residency_Career']) else None
    career_res = row['Career']

    cursor = conn.cursor()
    try:
        # Insert residency
        if residency:
            insert_if_not_exists(cursor, TABLES["RESIDENCY"], 
                               {RESIDENCY["NAME"]: residency})

        # Insert medical school
        if medical_school:
            insert_if_not_exists(cursor, TABLES["MEDICAL_SCHOOL"], 
                               {MEDICAL_SCHOOL["NAME"]: medical_school})

        # Handle fellowship
        fellowship_id = None
        if fellowship:
            fellowship_parts = fellowship.split('@')
            fellowship_name = fellowship_parts[0].strip()
            fellowship_institution = fellowship_parts[1].strip()
            
            insert_if_not_exists(cursor, TABLES["FELLOWSHIP"], 
                               {FELLOWSHIP["NAME"]: fellowship_name,
                                FELLOWSHIP["INSTITUTION_NAME"]: fellowship_institution})
            
            fellowship_result = select_with_condition(cursor, TABLES["FELLOWSHIP"], conditions={FELLOWSHIP["NAME"]: fellowship_name})
            fellowship_id = fellowship_result[0][0] if fellowship_result else None

        # Handle post-residency career
        post_residency_career_id = None
        if post_residency_career:
            career_type = None
            if pd.notna(career_res):
                career_type = {0: 'Private', 1: 'Academic', 2: 'Fellowship'}.get(career_res)
            
            if career_type:
                insert_if_not_exists(cursor, TABLES["POST_RESIDENCY_CAREER"],
                                   {POST_RESIDENCY_CAREER["NAME"]: post_residency_career,
                                    POST_RESIDENCY_CAREER["TYPE"]: career_type})
            
            post_residency_career_result = select_with_condition(cursor, TABLES["POST_RESIDENCY_CAREER"], conditions={POST_RESIDENCY_CAREER["NAME"]: post_residency_career})
            post_residency_career_id = post_residency_career_result[0][0] if post_residency_career_result else None        # Handle resident insertion
        # Remove commas from year values and convert to int
        grad_year = int(str(row['Grad_year']).replace(',', ''))
        match_year = int(str(row['Match_year']).replace(',', ''))
        duration = grad_year - match_year
        med_school_research = 0
        residency_research = duration - 6
        sex = row['Sex']

        # Get required IDs using select_with_condition which now returns results directly
        residency_result = select_with_condition(cursor, TABLES["RESIDENCY"], conditions={RESIDENCY["NAME"]: residency})
        residency_id = residency_result[0][0] if residency_result else None

        medical_school_result = select_with_condition(cursor, TABLES["MEDICAL_SCHOOL"], conditions={MEDICAL_SCHOOL["NAME"]: medical_school})
        medical_school_id = medical_school_result[0][0] if medical_school_result else None
        
        resident_data = {
            RESIDENT["FIRST_NAME"]: row['First_Name'].strip(),
            RESIDENT["MIDDLE_NAME"]: row['Middle_Name'].strip() if pd.notna(row['Middle_Name']) else None,
            RESIDENT["LAST_NAME"]: row['Last_Name'].strip(),
            RESIDENT["MATCH_YEAR"]: match_year,  # Use cleaned version without comma
            RESIDENT["GRAD_YEAR"]: grad_year,    # Use cleaned version without comma
            RESIDENT["SEX"]: sex,
            RESIDENT["DURATION"]: duration,
            RESIDENT["MEDICAL_SCHOOL_RESEARCH_YEARS"]: med_school_research,
            RESIDENT["RESIDENCY_RESEARCH_YEARS"]: residency_research,
            RESIDENT["MEDICAL_SCHOOL_ID"]: medical_school_id,
            RESIDENT["RESIDENCY_ID"]: residency_id,
            RESIDENT["FELLOWSHIP_ID"]: fellowship_id,
            RESIDENT["POST_RESIDENCY_CAREER_ID"]: post_residency_career_id,
        }
        # Create check_fields for existence check
        check_fields = {
            RESIDENT["FIRST_NAME"]: resident_data[RESIDENT["FIRST_NAME"]],
            RESIDENT["LAST_NAME"]: resident_data[RESIDENT["LAST_NAME"]]
        }
        
        if resident_data[RESIDENT["MIDDLE_NAME"]] is not None:
            check_fields[RESIDENT["MIDDLE_NAME"]] = resident_data[RESIDENT["MIDDLE_NAME"]]

        # Insert resident using insert_if_not_exists which now handles cursor operations
        insert_if_not_exists(cursor, TABLES["RESIDENT"], check_fields, insert_fields=resident_data)

    except pyodbc.Error as e:
        print(f"Error processing row: {e}")
    finally:
        cursor.close()

def main():
    conn = connect_to_db()
    sheet = pd.read_excel('I6 Cleaned Graduated Data.xlsx', sheet_name='Graduated publications 2025')
    
    for _, row in sheet.iterrows():
        process_row(conn, row)
    
    conn.close()

if __name__ == "__main__":
    main()
