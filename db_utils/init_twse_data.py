# 在 terminal 下 python init_twse_data.py 就會執行爬蟲把 TWSE 的產業別和公司名稱存入 DB
from tools.twse_webscraper import write_twse_example_to_db
import sqlite3
import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.twse_webscraper import write_twse_example_to_db


# Step 1: 呼叫寫入函式（已內建判斷是否已有資料）
write_twse_example_to_db()

# Step 2: 顯示資料表內容
db_path = "db/esg_reports.db"
with sqlite3.connect(db_path) as conn:
    print("\n📦 Industry Table:")
    industry_df = pd.read_sql_query("SELECT * FROM Industry LIMIT 10", conn)
    print(industry_df)

    print("\n🏢 Company Table:")
    company_df = pd.read_sql_query("""
        SELECT Company.company_id, company_name_zh, company_name_en, Industry.industry_name_en
        FROM Company
        JOIN Industry ON Company.industry_id = Industry.industry_id
        LIMIT 10
    """, conn)
    print(company_df)