import streamlit as st
from typing import Annotated
from lib.pdf_context import generate_cleaned_pdf_pages, get_pdf_context

def show_pdf_content():
    if "cached_cleaned_pages" in st.session_state:
        # If cached cleaned pages exist, use them
        pdf_content = st.session_state["cached_cleaned_pages"]
    else:
        pdf_content = generate_cleaned_pdf_pages()
        # pdf_content = st.session_state.get("pdf_text", "")

    format_content = ""
    for page, content in pdf_content.items():
        if content.strip():
            format_content += f"Page {page}:\n {content.strip()}\n\n"

    content = f"""
            🤖 Here's what I found from the uploaded PDF:\n
            {format_content}
            ----------------------------------\n
            """
    # return content
    return {
        "output": content + "##ALL DONE##" # ✅ Gemini + AutoGen 相容格式
    }

def get_pdf_page_content(
    page: Annotated[int, "Page number to retrieve from PDF"]
):
    # content = get_pdf_context(page=page) + "##ALL DONE##"

    if "cached_cleaned_pages" in st.session_state:
        # If cached cleaned pages exist, use them
        content = st.session_state["cached_cleaned_pages"].get(page, "")
    else:
        content = generate_cleaned_pdf_pages()[page]

    # return content
    return {
        "output": content + "##ALL DONE##"  # ✅ Gemini + AutoGen 相容格式
    }

def esg_analysis():
    # import esg_analysis module here to avoid circular import issues
    from lib.esg_analysis import analyze_esg_from_pdf

    content = analyze_esg_from_pdf() + "##ALL DONE##"

    # return content
    return {
        "output": content  # ✅ Gemini + AutoGen 相容格式
    }

def optimize_esg_report():
    """
    Optimize the ESG report by analyzing the uploaded PDF content.
    If `compare` is True, it will also compare with benchmark reports from the same industry.
    """
    from lib.optimize_esg_report import optimize_esg_report

    content = optimize_esg_report() + "##ALL DONE##"

    # return content
    return {
        "output": content  # ✅ Gemini + AutoGen 相容格式
    }

def cross_comparison_analysis(
        industry: Annotated[str, "Industry type for analysis"],
        years: Annotated[list[int], "Years for cross-comparison, e.g., [2020, 2021, 2022]"],
):
    # import esg_analysis module here to avoid circular import issues
    from lib.esg_analysis import init_cross_comparison_data, esg_charts, show_wordcloud_controls
    from lib.esg_info_extractor import verify_esg_industry

    """
    Perform ESG cross-comparison analysis for a given industry over specified years.
    This will visualize charts and wordclouds on the dashboard.
    """

    if not industry:
        industry = st.session_state["pdf_info"]["industry"]
    if not years:
        years = [int(st.session_state["pdf_info"]["report_year"])]
        # years = None

    # pdf_texts 的結構為 {year: {company: pdf_content}}
    def check_if_all_empty(pdf_texts):
        all_empty = True  # 先假設都是空的

        for year_data in pdf_texts.values():  # 每一年
            for company_text in year_data.values():  # 每個公司
                if company_text and company_text.strip():  # 有非空內容
                    all_empty = False
                    break
            if not all_empty:
                break
        return all_empty

    pdf_texts = init_cross_comparison_data(industry, years)
    # print(f"pdf_texts: {pdf_texts}")  # Debugging line to check the structure of pdf_texts
    if check_if_all_empty(pdf_texts):
        # st.warning(f"❗{industry} 產業中的所有年份中所有公司皆無 ESG 報告書，請確認需交叉分析的產業與年份是否正確。")
        years_str = ", ".join(map(str, years))
        st.warning(f"❗All companies in all selected years for the `{industry}` industry have no available ESG reports. Please verify that the industry and years (`{years_str}`) selected for cross-comparison are correct.")
        return {
            "output": "⚠️ No valid PDF content found for the specified industry and years to cross-comparison. Please specify a valid industry name or a valid year.##ALL DONE##"
        }

    matched_industry = verify_esg_industry(industry)
    if matched_industry is None:
        return {
            "output": f"⚠️ Invalid industry type - `{industry}` provided. Please check the industry name and try again.##ALL DONE##"
        }

    language = st.session_state.get("lang_setting", "english")
    with st.spinner(f"🤖 Gemini is cross-comparing in {matched_industry} industry..."):
        esg_charts(pdf_texts=pdf_texts, industry=matched_industry, language=language)
        # show_wordcloud_controls()

    # if not upload any PDF, return a message
    # return {
    #     "output": "⚠️ Please upload a PDF for cross-comparison analysis.##ALL DONE##"
    # }

    return {
        "output": "Cross-comparison analysis is displayed as below interactive page.##ALL DONE##"
    }

def generate_esg_template_analysis(
    template_format: Annotated[str, "ESG report template format (e.g., GRI, TCFD, SASB)"],
    industry: Annotated[str, "Industry type for SASB template (if applicable)"]
):
    """
    Generate ESG template analysis based on the selected template format and industry.
    """
    from lib.generate_esg_template_analysis import run_esg_template_generation

    content = run_esg_template_generation(template_format, industry) + "##ALL DONE##"

    # return content
    return {
        "output": content  # ✅ Gemini + AutoGen 相容格式
    }
