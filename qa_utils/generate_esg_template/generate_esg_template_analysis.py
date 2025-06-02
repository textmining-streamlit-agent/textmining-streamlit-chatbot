import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import fitz  # PyMuPDF
from collections import Counter
import nltk
nltk.download('punkt')
nltk.download('stopwords')

# 自定義模組
from agents.gemini_agent import chat_with_gemini
from db_utils.esg_report_db_utils import get_all_esg_reports
from pdf_context import preprocess_english_text, preprocess_chinese_text, detect_pdf_language

# 語言設定（English / 繁體中文）
try:
    import streamlit as st
    lang_setting = st.session_state.get("lang_setting", "English")
except:
    lang_setting = "繁體中文"  # 預設繁體中文


# -------------------------------
# 擷取產業的 top 50 關鍵字
# -------------------------------
def get_top_keywords_by_industry(industry_en, top_k=50):
    all_reports = get_all_esg_reports()
    subset = (
        all_reports[all_reports['industry'] == industry_en]
        .sort_values(by=['company', 'year'], ascending=[True, False])
        .drop_duplicates(subset='company', keep='first')
        .head(3)
    )
    all_texts = subset['content'].dropna().tolist()

    tokens = []
    for text in all_texts:
        lang = detect_pdf_language([type('Dummy', (), {'get_text': lambda: text})()])
        if lang == "chinese":
            tokens += preprocess_chinese_text(text)
        else:
            tokens += preprocess_english_text(text)

    freq = Counter(tokens)
    keywords = [word for word, _ in freq.most_common(top_k)]
    return keywords

# -------------------------------
# 模板路徑與文字處理
# -------------------------------
def load_template_text(template_format, industry):
    template_format = template_format.upper()
    base_path = os.path.join("db", "esg_report_templates", template_format)

    if template_format == "GRI":
        pdf_files = [f for f in os.listdir(base_path) if f.endswith(".pdf")]
        pdf_path = os.path.join(base_path, pdf_files[0])
    elif template_format == "TCFD":
        pdf_path = os.path.join(base_path, "2021-TCFD-Implementing_Guidance.pdf")
    elif template_format == "SASB":
        valid_industries = [name for name in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, name))]
        if industry not in valid_industries:
            raise ValueError(
                "❌ Unsupported industry for SASB.\n"
                f"✅ Available industries are: {', '.join(valid_industries)}"
            )
        industry_path = os.path.join(base_path, industry)
        if not os.path.isdir(industry_path):
            raise ValueError(f"❌ Cannot find the specified SASB industry folder: {industry}")
        pdf_files = [f for f in os.listdir(industry_path) if f.endswith(".pdf")]
        if not pdf_files:
            raise ValueError(f"❌ No PDF template found in: {industry_path}")
        pdf_path = os.path.join(industry_path, pdf_files[0])

    else:
        raise ValueError("❌ Unsupported format")

    print(f"📄 Selected template: {pdf_path}")

    with fitz.open(pdf_path) as doc:
        template_pdf_text = ""
        for page in doc:
            try:
                template_pdf_text += page.get_text()
            except Exception as e:
                print(f"[load_template_text] Error reading page: {e}")
    return template_pdf_text

# -------------------------------
# Gemini 輸出 ESG 模板
# -------------------------------
def generate_industry_esg_template_with_gemini(template_pdf_text, template_format="GRI", industry="", keywords=None):
    format_title = {
        "GRI": "GRI (Global Reporting Initiative)",
        "SASB": "SASB (Sustainability Accounting Standards Board)",
        "TCFD": "TCFD (Task Force on Climate-related Financial Disclosures)"
    }.get(template_format.upper(), "ESG")

    keyword_hint = ", ".join(keywords) if keywords else ""

    prompt = (
        f"You are an ESG consultant. Based solely on the following reference material from the {format_title}, "
        f"please generate a practical, structured ESG report template tailored for the '{industry}' industry.\n\n"
        f"📄 Reference Material:\n{template_pdf_text}\n\n"
    )

    if keyword_hint:
        prompt += (
            f"📌 Also consider these common ESG-related keywords used by top companies in the {industry} industry: {keyword_hint}\n\n"
        )

    prompt += (
        f"✍️ Please output in {lang_setting}, and output a structured ESG report template with:\n"
        f"- Major section titles (e.g., Governance, Environmental, Social)\n"
        f"- Key points companies should address under each section\n"
        f"- Field prompts or placeholders for company-specific data\n"
        f"- Only reference the {format_title}. DO NOT include items from other ESG frameworks.\n"
    )
    return chat_with_gemini(prompt, restrict=False)

def run_esg_template_generation(template_format, industry, compare=False):
    template_pdf_text = load_template_text(template_format, industry)
    keywords = get_top_keywords_by_industry(industry) if compare else None
    result = generate_industry_esg_template_with_gemini(
        template_pdf_text, template_format=template_format, industry=industry, keywords=keywords
    )
    return result
