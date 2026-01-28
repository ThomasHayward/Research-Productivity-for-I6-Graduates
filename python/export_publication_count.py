import pandas as pd
import pyodbc
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows


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

    with open('SQL/resident_publication_counts.sql') as f:
        residents_sql = f.read()


    residents_df = fetch_query(cursor, residents_sql)

    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"

    def write_table(title, df):
        ws.append([title])
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        ws.append([])

    write_table("Residents Info", residents_df)

    wb.save("./Exports/resident_publication_report.xlsx")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
    main()
