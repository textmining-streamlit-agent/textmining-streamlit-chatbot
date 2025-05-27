import sqlite3
import pandas as pd

conn = sqlite3.connect("db/esg_reports.db")

for table in ["Industry", "Company", "ESG_Report"]:
    print(f"\n📄 {table} Table:")
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    print(df)

conn.close()
