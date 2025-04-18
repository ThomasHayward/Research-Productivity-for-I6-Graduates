import pandas as pd
import pyodbc

# Connect to the MySQL database
try:
    conn = pyodbc.connect('DRIVER={MySQL ODBC 9.2 ANSI Driver};SERVER=localhost;DATABASE={integrated_resident_project};UID=admin;')
except pyodbc.Error as e:
    print(f"Error connecting to MySQL: {e}")
    exit(1)

# Read the Excel file
sheet = pd.read_excel('I6 Cleaned Graduated Data.xlsx', sheet_name='Graduated publications 2025')

# Iterate through each row in the DataFrame
for index, row in sheet.iterrows():
    # Access each field for the current person and trim string values
    residency = row['Residency'].strip() if pd.notna(row['Residency']) else None
    match_year = row['Match_year']
    grad_year = row['Grad_year']
    first_name = row['First_Name'].strip() if pd.notna(row['First_Name']) else None
    middle_name = row['Middle_Name'].strip() if pd.notna(row['Middle_Name']) else None
    last_name = row['Last_Name'].strip() if pd.notna(row['Last_Name']) else None
    medical_school = row['Medical_School'].strip() if pd.notna(row['Medical_School']) else None
    career_res = row['Career']
    fellowship = row['Fellowship'].strip() if pd.notna(row['Fellowship']) else None
    post_residency_career = row['Post_Residency_Career'].strip() if pd.notna(row['Post_Residency_Career']) else None

    # Handle residency insertion
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM residency WHERE name = ?", (residency,))
        count = cursor.fetchone()[0]
        
        if count == 0:
            cursor.execute("INSERT INTO residency (name) VALUES (?)", (residency,))
            cursor.commit()
            print(f"Inserted new institution: {residency}")
    except pyodbc.Error as e:
        print(f"Error with residency operation: {e}")
    finally:
        cursor.close()

    # Handle medical school insertion
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM medical_school WHERE name = ?", (medical_school,))
        count = cursor.fetchone()[0]
        
        if count == 0:
            cursor.execute("INSERT INTO medical_school (name) VALUES (?)", (medical_school,))
            cursor.commit()
            print(f"Inserted new medical school: {medical_school}")
    except pyodbc.Error as e:
        print(f"Error with medical school operation: {e}")
    finally:
        cursor.close()

    # Handle fellowship insertion
    if pd.notna(fellowship):  # Only insert if fellowship is not NaN
        try:
            fellowshipString = fellowship.split('@')
            print(fellowshipString, fellowship)
            fellowshipName = fellowshipString[0].strip()
            fellowshipInstitution = fellowshipString[1].strip()

            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM fellowship WHERE name = ? AND institution_name = ?", (fellowshipName, fellowshipInstitution))
            count = cursor.fetchone()[0]
            
            if count == 0:
                cursor.execute("INSERT INTO fellowship (name, institution_name) VALUES (?, ?)", (fellowshipName, fellowshipInstitution))
                cursor.commit()
                print(f"Inserted new fellowship: {fellowship}")
        except pyodbc.Error as e:
            print(f"Error with fellowship operation: {e}")
        finally:
            cursor.close()

    # Handle post-graduation career insertion
    try:
        cursor = conn.cursor()
        # Determine career type based on career_res
        career_type = None
        if pd.notna(career_res):
            if career_res == 0:
                career_type = 'Private'
            elif career_res == 1:
                career_type = 'Academic'
            elif career_res == 2:
                career_type = 'Fellowship'

        if pd.notna(post_residency_career):
            cursor.execute("""
                SELECT COUNT(*) FROM post_residency_career 
                WHERE name = ? AND type = ?
            """, (post_residency_career, career_type))
            count = cursor.fetchone()[0]
            
            if count == 0:
                cursor.execute("""
                    INSERT INTO post_residency_career (name, type) 
                    VALUES (?, ?)
                """, (post_residency_career, career_type))
                cursor.commit()
                print(f"Inserted new post-residency career: {post_residency_career} ({career_type})")
    except pyodbc.Error as e:
        print(f"Error with post-residency career operation: {e}")
    finally:
        cursor.close()

    # Handle resident insertion
    try:
        cursor = conn.cursor()
        # Check if resident already exists based on names
        cursor.execute("""
            SELECT COUNT(*) FROM resident 
            WHERE first_name = ? AND 
                  (middle_name = ? OR (middle_name IS NULL AND ? IS NULL)) AND 
                  last_name = ?
        """, (first_name, middle_name, middle_name, last_name))
        count = cursor.fetchone()[0]
        
        if count == 0:
            # Get IDs for foreign keys
            cursor.execute("SELECT id FROM residency WHERE name = ?", (residency,))
            residency_id = cursor.fetchone()[0]
            
            cursor.execute("SELECT id FROM medical_school WHERE name = ?", (medical_school,))
            medical_school_id = cursor.fetchone()[0]
            
            # Get fellowship ID if it exists
            fellowship_id = None
            if pd.notna(fellowship):
                cursor.execute("SELECT id FROM fellowship WHERE name = ?", (fellowship,))
                fellowship_result = cursor.fetchone()
                if fellowship_result:
                    fellowship_id = fellowship_result[0]

            # Get post_residency_career_id if it exists
            post_residency_career_id = None
            if pd.notna(post_residency_career):
                cursor.execute("""
                    SELECT id FROM post_residency_career 
                    WHERE name = ? AND type = ?
                """, (post_residency_career, career_type))
                career_result = cursor.fetchone()
                if career_result:
                    post_residency_career_id = career_result[0]

            duration = grad_year - match_year

            medical_school_research_years = duration - 6

            residency_research_years = (medical_school_research_years - 1 if medical_school_research_years > 1 else 0)
            # Insert the resident
            cursor.execute("""
                INSERT INTO resident (
                    first_name, middle_name, last_name, 
                    match_year, grad_year, 
                    residency_id, medical_school_id, fellowship_id,
                    post_residency_career_id, duration, medical_school_research_years, residency_research_years
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                first_name, middle_name, last_name,
                match_year, grad_year,
                residency_id, medical_school_id, fellowship_id,
                post_residency_career_id, duration, medical_school_research_years, residency_research_years
            ))
            cursor.commit()
            print(f"Inserted new resident: {first_name} {last_name}")
    except pyodbc.Error as e:
        print(f"Error with resident operation: {e}")
    finally:
        cursor.close()