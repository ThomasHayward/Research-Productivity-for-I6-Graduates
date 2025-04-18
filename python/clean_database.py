import pyodbc
from utils.constants import TABLES


def clean_database():
    try:
        # Connect to the database
        conn = pyodbc.connect('DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE={integrated_resident_project};UID=admin;')
        cursor = conn.cursor()

        # Delete in reverse order of dependencies using TABLES constant
        tables_to_clean = [
            TABLES["RESIDENT"],              # Delete residents first (they depend on everything)
            TABLES["POST_RESIDENCY_CAREER"], # Then delete the reference tables
            TABLES["FELLOWSHIP"],
            TABLES["MEDICAL_SCHOOL"],
            TABLES["RESIDENCY"],
            TABLES["AUTHOR_PUBLICATION"],
            TABLES["AUTHOR"],
            TABLES["PUBLICATION"],
            TABLES["JOURNAL"],
            TABLES["GRANT"],
        ]

        for table in tables_to_clean:
            try:
                cursor.execute(f"DELETE FROM {table}")
                cursor.execute(f"ALTER TABLE {table} AUTO_INCREMENT = 1")
                cursor.commit()
                print(f"Cleaned table: {table}")
            except pyodbc.Error as e:
                print(f"Error cleaning table {table}: {e}")
                conn.rollback()

        print("Database cleanup completed successfully")

    except pyodbc.Error as e:
        print(f"Database connection error: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # response = input("This will delete ALL data from the database. Are you sure? (yes/no): ")
    # if response.lower() == 'yes':
    #     clean_database()
    # else:
    #     print("Database cleanup cancelled")
    clean_database()