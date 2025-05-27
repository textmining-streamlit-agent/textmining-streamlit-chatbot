import streamlit as st
import pandas as pd
import sqlite3
from db_utils.esg_report_db_utils import *
from tools.twse_webscraper import write_twse_example_to_db

def show_esg_report_table():
    if "selected_company" not in st.session_state:
        st.session_state["selected_company"] = "All"
    if "selected_industry" not in st.session_state:
        st.session_state["selected_industry"] = "All"
    if "selected_year" not in st.session_state:
        st.session_state["selected_year"] = "All"
    if "delete_confirm" not in st.session_state:
        st.session_state["delete_confirm"] = False
    if "selected_to_delete" not in st.session_state:
        st.session_state["selected_to_delete"] = []
    if "show_esg_table" not in st.session_state:
        st.session_state["show_esg_table"] = False

    if st.session_state["show_esg_table"]:
        st.markdown("---")
        with st.container():
            col_title, col_close = st.columns([0.95, 0.05])
            with col_title:
                st.subheader("📊 ESG Report Table")
            with col_close:
                if st.button("❌", key=f"close_esg_table_{st.session_state.get('delete_confirm', False)}"):
                    st.session_state["show_esg_table"] = False
                    st.rerun()

            with st.form("update_esg_form", clear_on_submit=False):
                if st.form_submit_button("📥 Update ESG DB from TWSE"):
                    write_twse_example_to_db()
                    st.success("✅ TWSE ESG data inserted.")
                    st.session_state["reload_esg_data"] = True
                    st.rerun()

            with sqlite3.connect("db/esg_reports.db") as conn:
                company_df = get_all_companies()
                industry_df = get_all_industries()
                companies = [f"{row['company_name_en']} ({row['company_name_zh']})" for _, row in company_df.iterrows()]
                industries = [f"{row['industry_name_en']} ({row['industry_name_zh']})" for _, row in industry_df.iterrows()]
                df = get_all_esg_reports()

            with st.expander("🔍 Filter Conditions", expanded=True):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.selectbox("Company", ["All"] + companies, key="selected_company")
                with col2:
                    st.selectbox("Industry", ["All"] + industries, key="selected_industry")
                with col3:
                    years = sorted(df["year"].dropna().astype(str).unique())
                    st.selectbox("Report Year", ["All"] + years, key="selected_year")

            if st.session_state["selected_company"] != "All":
                company_en = st.session_state["selected_company"].split(" (")[0]
                df = df[df["company"] == company_en]
            if st.session_state["selected_industry"] != "All":
                industry_en = st.session_state["selected_industry"].split(" (")[0]
                df = df[df["industry"] == industry_en]
            if st.session_state["selected_year"] != "All":
                df = df[df["year"].astype(str) == st.session_state["selected_year"]]

            st.markdown("#### 📄 ESG Report Table")
            header = st.columns([0.05, 0.25, 0.25, 0.1, 0.35])
            header[0].markdown("**Select**")
            header[1].markdown("**Company**")
            header[2].markdown("**Industry**")
            header[3].markdown("**Year**")
            header[4].markdown("**Content**")

            selected_ids = []
            if df.empty:
                st.info("🔍 No ESG reports found for the selected filters.")
            else:
                for _, row in df.iterrows():
                    cols = st.columns([0.05, 0.25, 0.25, 0.1, 0.35])
                    with cols[0]:
                        if st.checkbox("", key=f"select_{row['report_id']}"):
                            selected_ids.append(row["report_id"])
                    cols[1].write(f"{row['company']} ({row['company_zh']})")
                    cols[2].write(f"{row['industry']} ({row['industry_zh']})")
                    cols[3].write(row["year"])
                    cols[4].write(row["content"][:100] + "...")

            if selected_ids and not st.session_state["delete_confirm"]:
                if st.button("🗑️ Delete Selected"):
                    st.session_state.delete_confirm = True
                    st.session_state.selected_to_delete = selected_ids
                    st.rerun()

            if st.session_state.delete_confirm:
                st.warning("⚠️ This action cannot be undone. Confirm deletion?")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("✅ Confirm"):
                        with sqlite3.connect("db/esg_reports.db") as conn:
                            cursor = conn.cursor()
                            cursor.executemany("DELETE FROM ESG_Report WHERE report_id = ?", [(rid,) for rid in st.session_state.selected_to_delete])
                            conn.commit()
                        st.success(f"Deleted {len(st.session_state.selected_to_delete)} record(s).")
                        st.session_state.delete_confirm = False
                        st.session_state.selected_to_delete = []
                        st.rerun()
                with col_cancel:
                    if st.button("❌ Cancel"):
                        st.info("Deletion cancelled.")
                        st.session_state.delete_confirm = False
