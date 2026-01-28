from datetime import datetime

import pandas as pd
import pyodbc

# Connect to the database
conn = pyodbc.connect('DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE=integrated_resident_project;UID=admin;')

# Query to get journals by year
query = """
SELECT
    YEAR(p.date_published) AS year,
    j.name AS journal_name,
    COUNT(*) AS publication_count
FROM publication p
    JOIN journal j ON p.journal_id = j.id
GROUP BY
    YEAR(p.date_published),
    j.name
ORDER BY year DESC, publication_count DESC;
"""

# Read the query into a dataframe
df = pd.read_sql_query(query, conn)
conn.close()

# Create Excel writer
output_file = 'journals_by_year.xlsx'
writer = pd.ExcelWriter(output_file, engine='openpyxl')

# Group by year and write each year to a separate sheet
for year, group_df in df.groupby('year'):
    # Remove the year column from the group since it's the sheet name
    sheet_df = group_df[['journal_name', 'publication_count']].reset_index(drop=True)
    
    # Write to sheet named after the year
    sheet_name = str(int(year))
    sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

writer.close()

print(f"Export complete! File saved as '{output_file}'")
print(f"Total years: {df['year'].nunique()}")
print(f"Total journals: {df['journal_name'].nunique()}")
print(f"Total publications: {df['publication_count'].sum()}")
