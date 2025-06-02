import json
import streamlit as st
from pdf_context import *
from agents.gemini_agent import chat_with_gemini, extract_json_from_gemini_output
from db_utils.esg_report_db_utils import get_all_companies, get_all_industries, get_industry_by_company

def extract_esg_info_from_pdf(top_n_pages=[1, 2, 3, 4, 5]):
    """
    Extracts company_name, industry, and report_year from an ESG report PDF using Gemini.

    Args:
        top_n_pages (list): List of page numbers to extract from.

    Returns:
        dict | None: Extracted fields or None if failed/incomplete.
    """
    contents = ""
    for p in top_n_pages:
        contents += get_pdf_context(page=p)

    pdf_language = st.session_state["pdf_language"]
    prompt = (
        f"You are a JSON data extractor. Read the following ESG report text (from pages {top_n_pages}):\n\n"
        f"{contents}\n\n"
        "Please extract the following fields:\n"
        "- `company_name`\n"
        "- `industry`\n"
        "- `report_year`\n\n"
        "⚠️ Only return pure JSON with no explanation, no markdown formatting, and no extra text.\n"
        f"⚠️ Please output in {pdf_language}\n"
        "✅ The JSON format should look exactly like:\n"
        "{\"company_name\": \"\", \"industry\": \"\", \"report_year\": \"\"}\n"
        "⚠️ If the report text does not seem to be an ESG report, return an empty JSON object: {}\n"
    )

    with st.spinner("🤖 Gemini is extracting ESG report information..."):
        result = chat_with_gemini(prompt, restrict=False)

    try:
        cleaned = extract_json_from_gemini_output(result)
        response = json.loads(cleaned)

        required_fields = ["company_name", "industry", "report_year"]
        missing_or_empty = [
            key for key in required_fields
            if key not in response or not response[key].strip()
        ]

        company_name, industry = verify_esg_company_industry(
            company_name=response['company_name'],
            industry=response['industry']
        )
        response['company_name'] = company_name
        response['industry'] = industry
        print(f"Matched company: {company_name}, industry: {industry}")

        if int(response['report_year']) < 1900:
            response['report_year'] = int(response['report_year']) + 1911

        if not missing_or_empty:
            st.session_state["pdf_info"] = response
            st.info(
                f"✅ ESG report info extracted:\n\n"
                f"📌 **Company Name:** {response['company_name']}\n\n"
                f"🏭 **Industry:** {response['industry']}\n\n"
                f"📅 **Report Year:** {response['report_year']}"
            )
            return response
        else:
            st.warning(
                f"⚠️ Gemini returned incomplete or empty fields: {', '.join(missing_or_empty)}.\n\n"
                f"📄 Please check whether the uploaded PDF is a valid **ESG report** containing identifiable company, industry, and year information."
            )
            return None

    except Exception as e:
        st.warning(f"⚠️ Failed to parse Gemini output as JSON: {e}")
        st.code(result)
        return None

def verify_esg_company_industry(company_name: str, industry: str, soft_matched: bool = True):
    """
    Verifies and matches ESG report info (company name and industry) with TWSE lists using Gemini.

    Args:
        company_name (str): Extracted company name from ESG report.
        industry (str): Extracted industry name from ESG report.

    Returns:
        dict: {"matched_company": str, "matched_industry": str}
    """
    pdf_language = st.session_state["pdf_language"]

    companies_df = get_all_companies()
    industries_df = get_all_industries()
    if pdf_language == "chinese":
        companies = companies_df['company_name_zh'].tolist()
        industries = industries_df['industry_name_zh'].tolist()
    elif pdf_language == "english":
        companies = companies_df['company_name_en'].tolist()
        industries = industries_df['industry_name_en'].tolist()

    company_prompt = (
        f"You are a strict matcher. Given the extracted company name: \"{company_name}\", "
        f"find the closest match **only from this list of official companies**:\n\n"
        f"{companies}\n\n"
        "⚠️ Only return pure JSON, no explanation, no formatting. "
        f"⚠️ Please output in {pdf_language}\n"
        "✅ Return format:\n"
        "{\"matched_company\": \"(must be one of the names in the list)\"}"
    )

    with st.spinner("🤖 Gemini is verifying company name from TWSE company list..."):
        company_raw = chat_with_gemini(company_prompt, restrict=False)

    # industry_prompt = (
    #     f"You are a strict matcher. Given the extracted industry name: \"{industry}\", "
    #     f"find the closest match **only from this list of official industries**:\n\n"
    #     f"{industries}\n\n"
    #     "⚠️ Only return pure JSON, no explanation, no formatting. "
    #     f"⚠️ Please output in {pdf_language}\n"
    #     "✅ Return format:\n"
    #     "{\"matched_industry\": \"(must be one of the names in the list)\"}"
    # )

    # with st.spinner("🤖 Gemini is verifying industry name from TWSE industry list..."):
    #     industry_raw = chat_with_gemini(industry_prompt, restrict=False)

    try:
        matched_company = json.loads(extract_json_from_gemini_output(company_raw))["matched_company"]
    except Exception as e:
        st.warning(f"❌ Failed to parse matched company: {e}")
        st.code(company_raw)
        matched_company = None

    # try:
    #     matched_industry = json.loads(extract_json_from_gemini_output(industry_raw))["matched_industry"]
    # except Exception as e:
    #     st.warning(f"❌ Failed to parse matched industry: {e}")
    #     st.code(industry_raw)
    #     matched_industry = None

    if soft_matched or matched_industry is None:
        matched_industry_name = get_industry_by_company(company_name = matched_company)
        if pdf_language == "chinese":
            matched_industry = matched_industry_name["industry_name_zh"]
        else:
            matched_industry = matched_industry_name["industry_name_en"]
    return matched_company, matched_industry

def verify_esg_industry(industry: str):
    """
    Verifies and matches an ambiguous industry name with TWSE lists using Gemini.

    Args:
        industry (str): e.g., "Food and Beverage", "食品業"

    Returns:
        matched_industry" (str): e.g., "Food"
    """
    language = st.session_state["lang_setting"]

    industries_df = get_all_industries()
    if language in ["chinese", "Chinese", "繁體中文"]:
        industries = industries_df['industry_name_zh'].tolist()
    elif language in ["english", "English"]:
        industries = industries_df['industry_name_en'].tolist()

    industry_prompt = (
        f"You are a strict matcher. Given the extracted industry name: \"{industry}\", "
        f"find the closest match **only from this list of official industries**:\n\n"
        f"{industries}\n\n"
        "⚠️ Only return pure JSON, no explanation, no formatting. "
        f"⚠️ Please output in {language}\n"
        "✅ Return format:\n"
        "{\"matched_industry\": \"(must be one of the names in the list)\"}"
    )

    with st.spinner("🤖 Gemini is verifying industry name from TWSE industry list..."):
        industry_raw = chat_with_gemini(industry_prompt, restrict=False)

    try:
        matched_industry = json.loads(extract_json_from_gemini_output(industry_raw))["matched_industry"]
    except Exception as e:
        st.warning(f"❌ Failed to parse matched industry: {e}")
        st.code(industry_raw)
        matched_industry = None

    return matched_industry
