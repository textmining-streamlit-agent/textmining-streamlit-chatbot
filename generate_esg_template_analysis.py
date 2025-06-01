import argparse
import os
import fitz  # PyMuPDF
from agents.gemini_agent import chat_with_gemini


# -------------------------------
# 工具函數：抓取對應 ESG 模板 PDF 路徑
# -------------------------------
def transform_template_format(format: str, industry: str = "") -> str:
    format = format.upper()
    base_dir = os.path.join("db", "esg_report_templates", format)

    if not os.path.exists(base_dir):
        raise FileNotFoundError(f"❌ Directory for format '{format}' not found: {base_dir}")

    if format == "GRI":
        pdfs = [f for f in os.listdir(base_dir) if f.endswith(".pdf")]
        if not pdfs:
            raise FileNotFoundError("❌ No GRI templates found.")
        return os.path.join(base_dir, pdfs[0])

    elif format == "TCFD":
        file_path = os.path.join(base_dir, "2021-TCFD-Implementing_Guidance.pdf")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ TCFD template not found at: {file_path}")
        return file_path

    elif format == "SASB":
        if not industry:
            raise ValueError(f"❗️Format '{format}' requires an industry name.")
        filename = f"{industry.lower().replace(' ', '-')}-standard_en-gb.pdf"
        file_path = os.path.join(base_dir, filename)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ No such template for industry '{industry}': {file_path}")
        return file_path

    else:
        raise ValueError("❌ Unsupported format. Please choose from: GRI, SASB, TCFD")


# -------------------------------
# 將 PDF 轉為文字（可指定頁數）
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


# -------------------------------
# 模式一：分析模板內容
# -------------------------------
def analyze_esg_with_gemini(pdf_text, industry="", lang="English"):
    prompt = (
        f"You are an ESG domain assistant. Please help analyze the following content.\n\n"
        f"📌 Target Industry: {industry}\n"
        f"📄 Below is the raw content extracted from an ESG template PDF:\n\n"
        f"{pdf_text}\n\n"
        f"✍️ Please review the content and provide your insights in {lang}. "
        f"You may summarize, classify, highlight gaps, or generate questions relevant to the '{industry}' sector.\n"
    )
    return chat_with_gemini(prompt, restrict=False)


# -------------------------------
# 模式二：產出 ESG 撰寫範本
# -------------------------------
def generate_industry_esg_template_with_gemini(pdf_text, industry="", lang="English"):
    prompt = (
        f"You are an ESG consultant. Based on the following reference content from an ESG reporting standard, "
        f"please generate a practical, structured ESG report template tailored for the '{industry}' industry.\n\n"
        f"📄 Reference Material:\n{pdf_text}\n\n"
        f"✍️ In {lang}, output a structured ESG report template with:\n"
        f"- Major section titles (e.g., Governance, Environmental, Social)\n"
        f"- Key points companies should address under each section\n"
        f"- Field prompts or placeholders for company-specific data\n"
        f"- Optional references to GRI / SASB / TCFD if relevant\n\n"
        f"The output should look like a clean template that companies can fill in."
    )
    return chat_with_gemini(prompt, restrict=False)


# -------------------------------
# 主程式
# -------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate ESG template analysis or drafting aid")
    parser.add_argument("--format", required=True, help="Template format: GRI / SASB / TCFD")
    parser.add_argument("--industry", default="", help="Industry name (SASB or TCFD only)")
    parser.add_argument("--lang", default="English", help="Output language (English or 繁體中文)")
    parser.add_argument("--max-pages", type=int, default=None, help="Number of pages to extract from PDF (default: all)")
    parser.add_argument("--mode", default="analysis", choices=["analysis", "template"],
                        help="Mode: 'analysis' to review ESG content, 'template' to generate ESG draft")

    args = parser.parse_args()

    try:
        # Step 1: 抓模板路徑
        pdf_path = transform_template_format(args.format, args.industry)
        print(f"📄 Selected template: {pdf_path}")

        # Step 2: 抽取 PDF 文字
        pdf_text = extract_text_from_pdf(pdf_path, max_pages=args.max_pages)

        # Step 3: 執行分析或產生撰寫範本
        print("🤖 Processing with Gemini...\n")
        if args.mode == "template":
            result = generate_industry_esg_template_with_gemini(pdf_text, industry=args.industry, lang=args.lang)
        else:
            result = analyze_esg_with_gemini(pdf_text, industry=args.industry, lang=args.lang)

        print("✅ Gemini Output:\n")
        print(result)

    except Exception as e:
        print(f"❌ Error occurred: {e}")


# -------------------------------
# CLI 進入點
# -------------------------------
if __name__ == "__main__":
    main()
