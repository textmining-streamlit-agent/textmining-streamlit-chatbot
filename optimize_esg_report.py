from pathlib import Path
import streamlit as st
import os
from pdf_context import get_pdf_context
from agents.gemini_agent import chat_with_gemini
from esg_analysis import clean_chinese_markdown_spacing 
from db_utils.esg_report_db_utils import get_all_esg_reports
import fitz

def load_benchmark_texts_from_db(industry, max_items=5): 
    try:
        df = get_all_esg_reports()
        df = df[df["industry"].str.lower() == industry.lower()].sort_values("year", ascending=False)
        df = df.head(max_items)
        texts = []
        for _, row in df.iterrows():
            label = f"{row['company']} ({row['year']})"
            content = row['content']
            if content:
                texts.append(f"📘 {label}:\n{content.strip()}")
        return "\n\n".join(texts)
    except Exception as e:
        st.error(f"❌ Error loading benchmark from DB: {e}")
        return ""

def optimize_esg_report(compare=True):
    pdf_text = get_pdf_context(page="all")
    lang_setting = st.session_state.get("lang_setting", "English")

    if not pdf_text:
        return "⚠️ Please upload an ESG report PDF or load an example report first."
    
    pdf_info = st.session_state.get("pdf_info", {})
    industry = pdf_info.get("industry", "unknown")
    company = pdf_info.get("company_name", "Uploaded Company")

    if industry == "unknown":
        st.warning("⚠️ Industry could not be identified from the uploaded report. Please confirm manually.")
        print("🪪 [DEBUG] No industry matched. Skipping benchmark comparison.")

    prompt = f"""
    You are a professional ESG reporting advisor.

    Your task is to analyze and optimize the ESG report submitted by **{company}**, which belongs to the **{industry}** industry.

    ⚠️ Regardless of the original report’s language, please **respond in {lang_setting}**.
    📄 The uploaded ESG report content is as follows:
    ====
    {pdf_text}
    ====
    """
    
    benchmark_text = ""
    if compare and industry != "unknown":
        benchmark_text = load_benchmark_texts_from_db(industry)

    if benchmark_text:
        prompt += f"\n\n==== 🏢 Benchmark ESG Reports (Same Industry) ====\n{benchmark_text}\n"

        prompt += """
        Now generate a structured and insightful markdown response with the following two parts:

        ### 1️⃣ Improvement Suggestions for the Uploaded Report
        - Categorize suggestions into the following ESG pillars using these headings:
            - 🌿 **Environmental (E)**
            - 🤝 **Social (S)**
            - 🏛 **Governance (G)**

        - For each ESG pillar (E, S, G), use the following structure:
            - 🎯 **What’s missing or weak?**: Clear summary of gaps or underdeveloped areas.
            - ✅ **What to add or revise?**: Action-oriented and realistic improvements.
            - 📌 **Reference from benchmark** _(optional)_: e.g., “Nestlé includes a dedicated DEI strategy and tracks KPIs.”
        
        - 🔚 **Summary Recommendation**: At the end of this section, include a short paragraph summarizing the 2–3 most important or urgent improvements the company should focus on.
        
        📌 Use markdown headings and emojis to organize content.
        ⚠️ Avoid long paragraphs or vague suggestions. Prioritize clarity, structure, and actionability.

        ### 2️⃣ Best Practices Observed in Benchmark Reports
        - Summarize ESG strategies/actions seen in the benchmark reports.
        - Categorize into:
            - 🌿 **Environmental (E)**
            - 🤝 **Social (S)**
            - 🏛 **Governance (G)**
        - Format each entry as:
            - **Action** – Mention the company name in parentheses (e.g., **Carbon Disclosure** _(Company XYZ)_)
        - Keep content clean, concise, and scannable (use bullet points and bold keywords).
        """    

    else:
        prompt += f"""
        Now generate a well-structured, markdown-formatted response with the following content:

        ### ✨ Improvement Suggestions for the Uploaded Report

        For each ESG pillar — **Environmental (E), Social (S), Governance (G)** — respond in three bullet sections:

        - 🎯 **What’s missing or weak?**
        - Summarize clearly what is underdeveloped or missing in the uploaded report.

        - ✅ **What to add or revise?**
        - Provide **realistic, actionable suggestions** based on international ESG reporting standards such as:
            - GRI (Global Reporting Initiative)
            - TCFD (Task Force on Climate-related Financial Disclosures)
            - SASB (Sustainability Accounting Standards Board)
        - Avoid vague suggestions and focus on what the company can practically improve.

        - 📌 **Reference global standards (not company-specific)**
        - You may cite relevant reporting frameworks, e.g.:
            - GRI 305: Emissions
            - GRI 403: Occupational Health & Safety
            - SASB Food & Beverage (if applicable)
            - TCFD for climate risk disclosures

        📌 Output must be in markdown format and optimized for readability.
        ⚠️ Do **not fabricate company names or benchmarks** since no benchmark data is available.
        """

    with st.spinner("🛠 Gemini is optimizing your ESG report..."):
        result = chat_with_gemini(prompt, restrict=False)

    if lang_setting == "繁體中文":
        result = clean_chinese_markdown_spacing(result)

    return result
