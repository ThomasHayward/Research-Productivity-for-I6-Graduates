import os
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

# Create a folder for exports if it doesn't exist
output_folder = 'journals_by_year_export'
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Export each year to a separate CSV file
for year, group_df in df.groupby('year'):
    # Remove the year column from the group since it's the filename
    sheet_df = group_df[['journal_name', 'publication_count']].reset_index(drop=True)
    
    # Write to CSV named after the year
    csv_filename = os.path.join(output_folder, f'{int(year)}.csv')
    sheet_df.to_csv(csv_filename, index=False)

# Also export all data to a single CSV
all_data_file = os.path.join(output_folder, 'all_journals_by_year.csv')
df.to_csv(all_data_file, index=False)

print(f"Export complete! Files saved in '{output_folder}/' folder")
print(f"Total years: {df['year'].nunique()}")
print(f"Total journals: {df['journal_name'].nunique()}")
print(f"Total publications: {df['publication_count'].sum()}")
print(f"\nCreated:")
print(f"  - {all_data_file} (all data in one file)")
for year in sorted(df['year'].unique(), reverse=True):
    print(f"  - {os.path.join(output_folder, f'{int(year)}.csv')}")
