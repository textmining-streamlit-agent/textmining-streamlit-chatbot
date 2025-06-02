import streamlit as st
from typing import Annotated
from pdf_context import get_pdf_context

def show_pdf_content():
    pdf_content = st.session_state.get("pdf_text", "")
    content = f"""
            🤖 Here's what I found from the uploaded PDF:\n
            {pdf_content}
            ----------------------------------##ALL DONE##\n
            """
    # return content
    return {
        "output": content  # ✅ Gemini + AutoGen 相容格式
}

def get_pdf_page_content(
    page: Annotated[int, "Page number to retrieve from PDF"]
):
    content = get_pdf_context(page=page) + "##ALL DONE##"
    # return content
    return {
        "output": content  # ✅ Gemini + AutoGen 相容格式
    }

def esg_analysis():
    # import esg_analysis module here to avoid circular import issues
    from esg_analysis import analyze_esg_from_pdf

    content = analyze_esg_from_pdf() + "##ALL DONE##"

    # return content
    return {
        "output": content  # ✅ Gemini + AutoGen 相容格式
    }

def cross_comparison_analysis(
        industry: Annotated[str, "Industry type for analysis"],
        years: Annotated[list[int], "Years for cross-comparison, e.g., [2020, 2021, 2022]"],
):
    # import esg_analysis module here to avoid circular import issues
    from esg_analysis import init_cross_comparison_data, esg_charts, show_wordcloud_controls
    from lib.esg_info_extractor import verify_esg_industry

    """
    Perform ESG cross-comparison analysis for a given industry over specified years.
    This will visualize charts and wordclouds on the dashboard.
    """
    if not industry:
        industry = st.session_state["pdf_info"]["industry"]
    if not years:
        years = [int(st.session_state["pdf_info"]["report_year"])]

    pdf_texts = init_cross_comparison_data(industry, years)
    industry = verify_esg_industry(industry)
    esg_charts(pdf_texts=pdf_texts, industry=industry)
    # show_wordcloud_controls()

    # if not upload any PDF, return a message
    # return {
    #     "output": "⚠️ Please upload a PDF for cross-comparison analysis.##ALL DONE##"
    # }

    return {
        "output": "Cross-comparison analysis is displayed as below interactive page.##ALL DONE##"
    }
