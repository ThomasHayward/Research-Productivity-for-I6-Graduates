import pandas as pd
import pyodbc
from utils.constants import POST_RESIDENCY_CAREER, RESIDENT, TABLES
from utils.select_functions import select_with_condition, update_table


def connect_to_db():
	try:
		return pyodbc.connect('DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE={integrated_resident_project};UID=admin;')
	except pyodbc.Error as e:
		print(f"Error connecting to MySQL: {e}")
		exit(1)

def update_post_residency_career(conn, row):
	cursor = conn.cursor()
	try:
		# Find resident by first, last, and (if available) middle name
		check_fields = {
			RESIDENT["FIRST_NAME"]: row['First_Name'].strip(),
			RESIDENT["LAST_NAME"]: row['Last_Name'].strip()
		}
		if pd.notna(row.get('Middle_Name')):
			check_fields[RESIDENT["MIDDLE_NAME"]] = row['Middle_Name'].strip()

		# Get resident record
		resident_result = select_with_condition(cursor, TABLES["RESIDENT"], conditions=check_fields)
		if not resident_result:
			print(f"Resident not found: {row['First_Name']} {row.get('Middle_Name','')} {row['Last_Name']}")
			return
		resident_id = resident_result[0][0]

		# Get current post_residency_career_id
		desc = [col[0] for col in cursor.description]
		career_id_idx = desc.index(RESIDENT["POST_RESIDENCY_CAREER_ID"])
		current_career_id = resident_result[0][career_id_idx]

		# Get new career type from Excel
		new_career_type = row['Post_Residency_Career'].strip() if pd.notna(row['Post_Residency_Career']) else None
		if not new_career_type:
			print(f"No new career type for resident {resident_id}")
			return

		# Find the correct post_residency_career_id for the new type
		career_result = select_with_condition(cursor, TABLES["POST_RESIDENCY_CAREER"], conditions={POST_RESIDENCY_CAREER["NAME"]: new_career_type})
		if not career_result:
			print(f"Career type not found in DB: {new_career_type}")
			return
		new_career_id = career_result[0][0]

		# Only update if changed
		if current_career_id != new_career_id:
			update_table(cursor, TABLES["RESIDENT"],
						 update_fields={RESIDENT["POST_RESIDENCY_CAREER_ID"]: new_career_id},
						 conditions={RESIDENT["ID"]: resident_id})
			print(f"Updated resident {resident_id} to new career type: {new_career_type}")
		else:
			print(f"No change for resident {resident_id}")
	except pyodbc.Error as e:
		print(f"Error updating resident: {e}")
	finally:
		cursor.close()

def main():
	conn = connect_to_db()
	sheet = pd.read_excel('I6 Cleaned Graduated Data.xlsx', sheet_name='Graduated publications 2025')
	for _, row in sheet.iterrows():
		update_post_residency_career(conn, row)
	conn.commit()
	conn.close()

if __name__ == "__main__":
	main()