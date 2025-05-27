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
) -> str:
    content = get_pdf_context(page=page) + "##ALL DONE##"
    # return content
    return {
            "output": content  # ✅ Gemini + AutoGen 相容格式
        }

def esg_analysis():
    from esg_analysis import analyze_esg_from_pdf
    content = analyze_esg_from_pdf() + "##ALL DONE##"

    # return content
    return {
            "output": content  # ✅ Gemini + AutoGen 相容格式
        }
