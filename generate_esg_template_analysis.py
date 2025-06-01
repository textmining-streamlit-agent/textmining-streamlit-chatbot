# import argparse
# import os
# import fitz  # PyMuPDF
# from agents.gemini_agent import chat_with_gemini

# # -------------------------------
# # 語言設定（支援 CLI 與 Streamlit 共用）
# # -------------------------------
# try:
#     import streamlit as st
#     lang_setting = st.session_state.get("lang_setting", "English")
# except:
#     lang_setting = "English"

# # -------------------------------
# # 清理中文段落排版
# # -------------------------------
# import re
# def clean_chinese_markdown_spacing(text):
#     text = text.replace("。\n", "。\n\n").replace("。", "。\n")
#     text = re.sub(r"(?<!\n)- ", r"\n- ", text)
#     return text

# # -------------------------------
# # tools：抓取對應 ESG 模板 PDF 路徑
# # -------------------------------
# def transform_template_format(format: str, industry: str = "") -> str:
#     format = format.upper()
#     base_dir = os.path.join("db", "esg_report_templates", format)

#     if not os.path.exists(base_dir):
#         raise FileNotFoundError(f"❌ Directory for format '{format}' not found: {base_dir}")

#     if format == "GRI":
#         pdfs = [f for f in os.listdir(base_dir) if f.endswith(".pdf")]
#         if not pdfs:
#             raise FileNotFoundError("❌ No GRI templates found.")
#         return os.path.join(base_dir, pdfs[0])

#     elif format == "TCFD":
#         file_path = os.path.join(base_dir, "2021-TCFD-Implementing_Guidance.pdf")
#         if not os.path.exists(file_path):
#             raise FileNotFoundError(f"❌ TCFD template not found at: {file_path}")
#         return file_path

#     elif format == "SASB":
#         if not industry:
#             raise ValueError(f"❗️Format '{format}' requires an industry name.")
#         filename = f"{industry.lower().replace(' ', '-')}-standard_en-gb.pdf"
#         file_path = os.path.join(base_dir, filename)
#         if not os.path.exists(file_path):
#             raise FileNotFoundError(f"❌ No such template for industry '{industry}': {file_path}")
#         return file_path

#     else:
#         raise ValueError("❌ Unsupported format. Please choose from: GRI, SASB, TCFD")


# # -------------------------------
# # 將 PDF 轉成文字（可指定頁數）
# # -------------------------------
# def extract_text_from_pdf(pdf_path: str, max_pages: int = None) -> str:
#     doc = fitz.open(pdf_path)
#     text_blocks = []

#     for page_number, page in enumerate(doc):
#         if max_pages is not None and page_number >= max_pages:
#             break
#         text = page.get_text().strip().replace("\n", " ")
#         if text:
#             text_blocks.append(f"[Page {page_number + 1}]: {text}")
#     doc.close()
#     return "\n\n".join(text_blocks)


# # -------------------------------
# # 模式一：分析模板內容
# # -------------------------------
# def analyze_esg_with_gemini(pdf_text, industry=""):
#     prompt = (
#         f"You are an ESG domain assistant. Please help analyze the following content.\n\n"
#         f"📌 Target Industry: {industry}\n"
#         f"📄 Below is the raw content extracted from an ESG template PDF:\n\n"
#         f"{pdf_text}\n\n"
#         f"✍️ Please review the content and provide your insights in {lang_setting}. "
#         f"You may summarize, classify, highlight gaps, or generate questions relevant to the '{industry}' sector.\n"
#     )
#     return chat_with_gemini(prompt, restrict=False)


# # -------------------------------
# # 模式二：產出 ESG 擴充撰寫範本
# # -------------------------------
# def generate_industry_esg_template_with_gemini(pdf_text, format="GRI", industry=""):
#     format = format.upper()
#     format_title = {
#         "GRI": "GRI (Global Reporting Initiative)",
#         "SASB": "SASB (Sustainability Accounting Standards Board)",
#         "TCFD": "TCFD (Task Force on Climate-related Financial Disclosures)"
#     }.get(format, "ESG")

#     prompt = (
#         f"You are an ESG consultant. Based solely on the following reference material from the {format_title}, "
#         f"please generate a practical, structured ESG report template tailored for the '{industry}' industry.\n\n"
#         f"📄 Reference Material:\n{pdf_text}\n\n"
#         f"✍️ In {lang_setting}, output a structured ESG report template with:\n"
#         f"- Major section titles (e.g., Governance, Environmental, Social)\n"
#         f"- Key points companies should address under each section\n"
#         f"- Field prompts or placeholders for company-specific data\n"
#         f"- Only reference the {format_title}. DO NOT include items from other ESG frameworks.\n\n"
#         f"The output should look like a clean, professional template that companies can directly fill in.\n"
#     )
#     return chat_with_gemini(prompt, restrict=False)


# # -------------------------------
# # 主程式
# # -------------------------------
# def main():
#     parser = argparse.ArgumentParser(description="Generate ESG template analysis or drafting aid")
#     parser.add_argument("--format", required=True, help="Template format: GRI / SASB / TCFD")
#     parser.add_argument("--industry", default="", help="Industry name (SASB or TCFD only)")
#     parser.add_argument("--max-pages", type=int, default=None, help="Number of pages to extract from PDF (default: all)")
#     parser.add_argument("--mode", default="analysis", choices=["analysis", "template"],
#                         help="Mode: 'analysis' to review ESG content, 'template' to generate ESG draft")
#     args = parser.parse_args()

#     try:
#         # Step 1: 抓模板路徑
#         pdf_path = transform_template_format(args.format, args.industry)
#         print(f"📄 Selected template: {pdf_path}")

#         # Step 2: 取得 PDF 文字
#         pdf_text = extract_text_from_pdf(pdf_path, max_pages=args.max_pages)

#         # Step 3: Gemini 分析 / 產出 ESG 撰寫範本
#         print("🤖 Processing with Gemini...\n")
#         if args.mode == "template":
#             result = generate_industry_esg_template_with_gemini(
#                 pdf_text, format=args.format, industry=args.industry
#             )
#         else:
#             result = analyze_esg_with_gemini(
#                 pdf_text, industry=args.industry
#             )

#         if lang_setting == "繁體中文":
#             result = clean_chinese_markdown_spacing(result)

#         print("\u2705 Gemini Output:\n")
#         print(result)

#     except Exception as e:
#         print(f"❌ Error occurred: {e}")


# # -------------------------------
# # CLI entry point
# # -------------------------------
# if __name__ == "__main__":
#     main()
# generate_esg_template_analysis.py (支援 compare 模式)

import argparse
import os
import fitz  # PyMuPDF
from agents.gemini_agent import chat_with_gemini
from db_utils.esg_report_db_utils import get_all_esg_reports
from pdf_context import preprocess_english_text, preprocess_chinese_text, detect_pdf_language
from collections import Counter
import re
import nltk
nltk.download('punkt')
nltk.download('stopwords')

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# 語言設定（ English / 繁體中文）
try:
    import streamlit as st
    lang_setting = st.session_state.get("lang_setting", "English")
except:
    lang_setting = "English"


# -------------------------------
# 擷取 PDF 文字內容
# -------------------------------
def extract_text_from_pdf(pdf_path: str, max_pages: int = None) -> str:
    doc = fitz.open(pdf_path)
    text_blocks = []

    for page_number, page in enumerate(doc):
        if max_pages is not None and page_number >= max_pages:
            break
        text = page.get_text().strip().replace("\n", " ")
        if text:
            text_blocks.append(f"[Page {page_number + 1}]: {text}")
    doc.close()
    return "\n\n".join(text_blocks)

extract_text_by_page 
# -------------------------------
# 取得該產業的 top 50 keywords
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

    # all_text = " ".join(subset['content'].dropna().tolist())
    # lang = detect_pdf_language([type('Dummy', (), {'get_text': lambda: all_text})()])

    # if lang == "chinese":
    #     tokens = preprocess_chinese_text(all_text)
    # else:
    #     tokens = preprocess_english_text(all_text)

    freq = Counter(tokens)
    keywords = [word for word, _ in freq.most_common(top_k)]
    return keywords

# -------------------------------
# 模板生成模式
# -------------------------------
def generate_industry_esg_template_with_gemini(pdf_text, format="GRI", industry="", keywords=None):
    format_title = {
        "GRI": "GRI (Global Reporting Initiative)",
        "SASB": "SASB (Sustainability Accounting Standards Board)",
        "TCFD": "TCFD (Task Force on Climate-related Financial Disclosures)"
    }.get(format.upper(), "ESG")

    keyword_hint = ", ".join(keywords) if keywords else ""

    prompt = (
        f"You are an ESG consultant. Based solely on the following reference material from the {format_title}, "
        f"please generate a practical, structured ESG report template tailored for the '{industry}' industry.\n\n"
        f"📄 Reference Material:\n{pdf_text}\n\n"
    )

    if keyword_hint:
        prompt += f"📌 Also consider these common ESG-related keywords used by top companies in the {industry} industry: {keyword_hint}\n\n"

    prompt += (
        f"✍️ In {lang_setting}, output a structured ESG report template with:\n"
        f"- Major section titles (e.g., Governance, Environmental, Social)\n"
        f"- Key points companies should address under each section\n"
        f"- Field prompts or placeholders for company-specific data\n"
        f"- Only reference the {format_title}. DO NOT include items from other ESG frameworks.\n"
    )
    return chat_with_gemini(prompt, restrict=False)


# -------------------------------
# CLI 主程式
# -------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate ESG template analysis or drafting aid")
    parser.add_argument("--format", required=True, help="Template format: GRI / SASB / TCFD")
    parser.add_argument("--industry", default="", help="Industry name (English, required for keyword match)")
    parser.add_argument("--max-pages", type=int, default=None, help="Max pages to extract from PDF")
    parser.add_argument("--mode", default="template", choices=["template"], help="Only 'template' mode supported here")
    parser.add_argument("--compare", action="store_true", help="Enable keyword comparison from top 3 reports")
    args = parser.parse_args()

    try:
        pdf_path = os.path.join("db", "esg_report_templates", args.format.upper())
        if args.format.upper() == "GRI":
            pdf_files = [f for f in os.listdir(pdf_path) if f.endswith(".pdf")]
            pdf_path = os.path.join(pdf_path, pdf_files[0])
        elif args.format.upper() == "TCFD":
            pdf_path = os.path.join(pdf_path, "2021-TCFD-Implementing_Guidance.pdf")
        elif args.format.upper() == "SASB":
            pdf_path = os.path.join(pdf_path, f"{args.industry.lower().replace(' ', '-')}-standard_en-gb.pdf")

        print(f"📄 Selected template: {pdf_path}")
        pdf_text = extract_text_from_pdf(pdf_path, max_pages=args.max_pages)

        print("🤖 Processing with Gemini...\n")
        if args.compare:
            keywords = get_top_keywords_by_industry(args.industry)
        else:
            keywords = None

        result = generate_industry_esg_template_with_gemini(
            pdf_text, format=args.format, industry=args.industry, keywords=keywords
        )

        print("\u2705 Gemini Output:\n")
        print(result)

    except Exception as e:
        print(f"❌ Error occurred: {e}")


if __name__ == "__main__":
    main()
