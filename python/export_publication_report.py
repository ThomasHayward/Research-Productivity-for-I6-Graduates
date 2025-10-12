import pandas as pd
import pyodbc
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from utils.constants import RESIDENT, TABLES


def connect_to_db():
    return pyodbc.connect('DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE={integrated_resident_project};UID=admin;')

def fetch_query(cursor, sql):
    cursor.execute(sql)
    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()
    rows = [list(row) for row in rows]
    df = pd.DataFrame(rows, columns=columns)
    return df

def main():
    conn = connect_to_db()
    cursor = conn.cursor()

    # Load SQL queries from files
    with open('SQL/residency_publication_counts.sql') as f:
        residency_sql = f.read()
    with open('SQL/residents_info_query.sql') as f:
        residents_sql = f.read()
    with open('SQL/medical_school_publication_counts.sql') as f:
        medschool_sql = f.read()
    with open('SQL/publications_from_author.sql') as f:
        pubs_sql = f.read()
    with open('SQL/publications_by_sex.sql') as f:
        sex_sql = f.read()
    with open('SQL/publications_by_fellowship.sql') as f:
        fellowship_sql = f.read()

    # Fetch dataframes
    residency_df = fetch_query(cursor, residency_sql)
    residents_df = fetch_query(cursor, residents_sql)
    medschool_df = fetch_query(cursor, medschool_sql)
    pubs_df = fetch_query(cursor, pubs_sql)
    sex_df = fetch_query(cursor, sex_sql)
    fellowship_df = fetch_query(cursor, fellowship_sql)
    # Print the shape of each dataframe
    print("Residency DataFrame shape:", residency_df.shape)
    print("Residents DataFrame shape:", residents_df.shape)
    print("Medical School DataFrame shape:", medschool_df.shape)
    print("Publications DataFrame shape:", pubs_df.shape)
    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"

    # Write each table to the summary sheet, separated by a blank row and a title
    def write_table(title, df):
        ws.append([title])
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        ws.append([])

    write_table("Residency Publication Counts", residency_df)
    write_table("Medical School Publication Counts", medschool_df)
    write_table("Publications by Sex", sex_df)
    write_table("Publications by Fellowship", fellowship_df)
    write_table("Residents Info", residents_df)

    # For each resident, create a new sheet with their articles (even if none)
    for full_name in residents_df['full_name']:
        sheet_name = full_name.replace('/', '_')[:31]  # Excel sheet name limit
        ws_res = wb.create_sheet(title=sheet_name)
        
        # Add resident info at the top
        resident_info = residents_df[residents_df['full_name'] == full_name]
        for r in dataframe_to_rows(resident_info, index=False, header=True):
            ws_res.append(r)
        ws_res.append([])
        
        # Add publications list
        ws_res.append([f"Publications for {full_name}"])
        df = pubs_df[pubs_df['full_name'] == full_name]
        if not df.empty:
            for r in dataframe_to_rows(df, index=False, header=True):
                ws_res.append(r)
        else:
            ws_res.append(["No publications found"])

    wb.save("./Exports/publication_report.xlsx")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
