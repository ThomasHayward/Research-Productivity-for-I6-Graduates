import os
from datetime import datetime

import pandas as pd
import pyodbc

# Connect to the database
conn = pyodbc.connect('DRIVER={MySQL ODBC 9.3 ANSI Driver};SERVER=localhost;DATABASE=integrated_resident_project;UID=admin;')

# Query to get journals by year
query = """
SELECT
    j.name AS journal_name,
    YEAR(p.date_published) AS year,
    COUNT(*) AS publication_count
FROM publication p
    JOIN journal j ON p.journal_id = j.id
GROUP BY
    j.name,
    YEAR(p.date_published)
ORDER BY j.name, year DESC;
"""

# Read the query into a dataframe
df = pd.read_sql_query(query, conn)
conn.close()

# Create Excel writer
output_file = 'journals_by_name.xlsx'
writer = pd.ExcelWriter(output_file, engine='openpyxl')

# Group by journal and write each journal to a separate sheet
for journal_name, group_df in df.groupby('journal_name'):
    # Remove the journal_name column from the group since it's the sheet name
    sheet_df = group_df[['year', 'publication_count']].reset_index(drop=True)
    
    # Sanitize sheet name (Excel has restrictions on sheet names)
    # Max 31 chars, no special characters like : \ / ? * [ ]
    safe_sheet_name = "".join(c for c in journal_name if c not in [':', '\\', '/', '?', '*', '[', ']']).strip()
    safe_sheet_name = safe_sheet_name[:31]  # Excel sheet name limit
    
    # Write to sheet named after the journal
    sheet_df.to_excel(writer, sheet_name=safe_sheet_name, index=False)

writer.close()

print(f"Export complete! File saved as '{output_file}'")
print(f"Total journals: {df['journal_name'].nunique()}")
print(f"Total years: {df['year'].nunique()}")
print(f"Total publications: {df['publication_count'].sum()}")
