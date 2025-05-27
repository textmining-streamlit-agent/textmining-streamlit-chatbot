import requests
from bs4 import BeautifulSoup
import pandas as pd
from time import sleep
from db_utils.esg_report_db_utils import init_esg_report_db, insert_company
import sqlite3 

def fetch_twse_company_list(url, lang="zh"):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    result = []

    for code in range(1, 39):
        payload = {
            "market": "1",  # TWSE Listed
            "industry_code": f"{code:02d}",
            "Page": "1",
            "chklike": "Y"
        }

        res = requests.post(url, headers=headers, data=payload)
        res.encoding = "big5"

        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.find_all("table")
        if len(tables) < 2:
            continue
        rows = tables[1].find_all("tr")[1:]
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cols) >= 8:
                result.append({
                    "company_name": cols[3],
                    "industry": cols[6]
                })
        sleep(0.5)
    
    return pd.DataFrame(result)

def get_bilingual_twse_company_industry():
    zh_url = "https://isin.twse.com.tw/isin/class_main.jsp"
    en_url = "https://isin.twse.com.tw/isin/e_class_main.jsp"

    zh_df = fetch_twse_company_list(zh_url, lang="zh")
    en_df = fetch_twse_company_list(en_url, lang="en")

    merged = pd.DataFrame({
        "產業別中文": zh_df["industry"],
        "產業別英文": en_df["industry"],
        "公司名稱中文": zh_df["company_name"],
        "公司名稱英文": en_df["company_name"]
    })

    return merged

def write_twse_example_to_db():
    # ✅ 先建立資料表
    init_esg_report_db()
    # 檢查 DB 是否已經有資料
    with sqlite3.connect("db/esg_reports.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Company")
        company_count = cursor.fetchone()[0]
        if company_count > 0:
            print("✅ Company table already has data. Skipping insert.")
            return

    df = get_bilingual_twse_company_industry()

    # 移除重複公司（用公司名稱中文）
    df = df.drop_duplicates(subset=["公司名稱中文"]).reset_index(drop=True)

    init_esg_report_db()

    for _, row in df.iterrows():
        company_zh = row["公司名稱中文"]
        company_en = row["公司名稱英文"]
        industry_zh = row["產業別中文"]
        industry_en = row["產業別英文"]

        try:
            insert_company(
                company_name_zh=company_zh,
                industry_name_zh=industry_zh,
                company_name_en=company_en,
                industry_name_en=industry_en
            )
        except Exception as e:
            print(f"❌ Failed to insert: {company_zh} - {industry_zh} — {e}")


