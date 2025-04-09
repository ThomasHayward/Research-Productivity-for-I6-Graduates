import pyodbc


def clean_database():
    try:
        # Connect to the database
        conn = pyodbc.connect('DRIVER={MySQL ODBC 9.2 ANSI Driver};SERVER=localhost;DATABASE={integrated_resident_project};UID=admin;')
        cursor = conn.cursor()

        # Delete in reverse order of dependencies
        tables = [
            'resident',              # Delete residents first (they depend on everything)
            'post_residency_career', # Then delete the reference tables
            'fellowship',
            'medical_school',
            'residency'
        ]

        for table in tables:
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
    response = input("This will delete ALL data from the database. Are you sure? (yes/no): ")
    if response.lower() == 'yes':
        clean_database()
    else:
        print("Database cleanup cancelled")
