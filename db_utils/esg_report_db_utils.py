import sqlite3
import os
import pandas as pd

ESG_DB_PATH = "db/esg_reports.db"

def init_esg_report_db():
    os.makedirs("db", exist_ok=True)
    with sqlite3.connect(ESG_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Industry (
            industry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            industry_name_zh TEXT UNIQUE,
            industry_name_en TEXT
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Company (
            company_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name_zh TEXT UNIQUE,
            company_name_en TEXT,
            industry_id INTEGER,
            FOREIGN KEY (industry_id) REFERENCES Industry(industry_id)
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ESG_Report (
            report_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            report_year INTEGER,
            content TEXT,
            FOREIGN KEY (company_id) REFERENCES Company(company_id)
        );
        """)
        conn.commit()

def insert_industry(industry_name_zh=None, industry_name_en=None):
    with sqlite3.connect(ESG_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO Industry (industry_name_zh, industry_name_en)
            VALUES (?, ?)
        """, (industry_name_zh, industry_name_en))
        conn.commit()

def insert_company(company_name_zh=None, industry_name_zh=None, company_name_en=None, industry_name_en=None):
    with sqlite3.connect(ESG_DB_PATH) as conn:
        cursor = conn.cursor()

        # Try zh first, then fallback to en
        if industry_name_zh:
            cursor.execute("SELECT industry_id FROM Industry WHERE industry_name_zh = ?", (industry_name_zh,))
        elif industry_name_en:
            cursor.execute("SELECT industry_id FROM Industry WHERE industry_name_en = ?", (industry_name_en,))
        else:
            raise ValueError("Either industry_name_zh or industry_name_en must be provided.")

        row = cursor.fetchone()

        if not row:
            insert_industry(industry_name_zh or industry_name_en, industry_name_en)
            if industry_name_zh:
                cursor.execute("SELECT industry_id FROM Industry WHERE industry_name_zh = ?", (industry_name_zh,))
            else:
                cursor.execute("SELECT industry_id FROM Industry WHERE industry_name_en = ?", (industry_name_en,))
            row = cursor.fetchone()

        industry_id = row[0]
        cursor.execute("""
            INSERT OR IGNORE INTO Company (company_name_zh, company_name_en, industry_id)
            VALUES (?, ?, ?)
        """, (company_name_zh, company_name_en, industry_id))
        conn.commit()

def insert_esg_report_by_id(company_id, report_year, content, overwrite=False):
    with sqlite3.connect("db/esg_reports.db") as conn:
        cursor = conn.cursor()

        if overwrite:
            cursor.execute("""
                DELETE FROM ESG_Report
                WHERE company_id = ? AND report_year = ?
            """, (company_id, report_year))
            print(f"🧹 Overwritten ESG report: company_id={company_id}, year={report_year}")
        else:
            cursor.execute("""
                SELECT 1 FROM ESG_Report
                WHERE company_id = ? AND report_year = ?
            """, (company_id, report_year))
            if cursor.fetchone():
                print("⚠️ Report already exists. Skipping insert.")
                return

        cursor.execute("""
            INSERT INTO ESG_Report (company_id, report_year, content)
            VALUES (?, ?, ?)
        """, (company_id, report_year, content))
        conn.commit()


def get_all_esg_reports():
    with sqlite3.connect(ESG_DB_PATH) as conn:
        df = pd.read_sql_query("""
            SELECT ESG_Report.report_id,
                   Company.company_name_en AS company,
                   Company.company_name_zh AS company_zh,
                   Industry.industry_name_en AS industry,
                   Industry.industry_name_zh AS industry_zh,
                   ESG_Report.report_year AS year,
                   ESG_Report.content
            FROM ESG_Report
            JOIN Company ON ESG_Report.company_id = Company.company_id
            JOIN Industry ON Company.industry_id = Industry.industry_id
            ORDER BY ESG_Report.report_year DESC
        """, conn)
    return df

def get_all_companies():
    with sqlite3.connect(ESG_DB_PATH) as conn:
        df = pd.read_sql_query("""
            SELECT company_name_en, company_name_zh
            FROM Company
            WHERE company_name_en IS NOT NULL
            GROUP BY company_name_en
            ORDER BY company_name_en
        """, conn)
    return df

def get_all_industries():
    with sqlite3.connect(ESG_DB_PATH) as conn:
        df = pd.read_sql_query("""
            SELECT industry_name_en, industry_name_zh
            FROM Industry
            WHERE industry_name_en IS NOT NULL
            GROUP BY industry_name_en
            ORDER BY industry_name_en
        """, conn)
    return df
