import streamlit as st
import re
import os
import nltk
from nltk import word_tokenize
import time
from qa_utils.ckip_word_segmenter_local import LocalCkipWordSegmenter

# --- 統一 NLTK 資料目錄為 Cloud 可用路徑 ---
nltk_data_path = "/home/appuser/nltk_data"
os.makedirs(nltk_data_path, exist_ok=True)
nltk.data.path.append(nltk_data_path)

# --- 確保 nltk 必要資源 ---
nltk_packages = ['punkt', 'punkt_tab', 'stopwords', 'averaged_perceptron_tagger', 'averaged_perceptron_tagger_eng']
for pkg in nltk_packages:
    try:
        nltk.data.find(pkg)
    except LookupError:
        print(f"Downloading NLTK resource: {pkg}")
        nltk.download(pkg, download_dir=nltk_data_path, quiet=True)

# --- 本地載入 CKIP word segmenter (延遲初始化) ---
def lazy_init_ckip_ws_driver(local=False):
    if "ckip_ws_driver" not in st.session_state:
        if local:
            with st.spinner("🔄 Loading local CKIP word segmenter..."):

                # from ckip_transformers.nlp import CkipWordSegmenter, CkipPosTagger, CkipNerChunker
                # st.session_state.ckip_ws_driver = CkipWordSegmenter(model="bert-base")

                # 使用本地模型載入 CKIP Word Segmenter
                st.session_state.ckip_ws_driver = LocalCkipWordSegmenter(model_path="models/ckip-models/bert-base")

                # Debug message
                # ws_driver = st.session_state.ckip_ws_driver
                # # 印 tokenizer 資訊
                # print(f"Tokenizer vocab size: {len(ws_driver.tokenizer.vocab)}")
                # print(f"Tokenizer special tokens: {ws_driver.tokenizer.special_tokens_map}")

                # # 印 model 資訊
                # print(f"Model architecture: {ws_driver.model.config.architectures}")
                # print(f"Model hidden size: {ws_driver.model.config.hidden_size}")
                # print(f"Model num_labels: {ws_driver.model.config.num_labels}")

                st.success("✅ Local CKIP WS loaded successfully!")
        else:
            with st.spinner("🔄 Loading Huggging Face CKIP model..."):
                st.session_state.ckip_ws_driver = LocalCkipWordSegmenter(model_path="ckiplab/bert-base-chinese-ws")
                st.success("✅ Huggingface CKIP WS loaded successfully!")

# --- 停用詞表 (自定義 ESG report) ---
def load_pdf_stopwords():
    pdf_stopwords = ["None", None, "n", "Col", "Table"]
    stopwords = set()
    for word in pdf_stopwords:
        if isinstance(word, str):
            stopwords.add(word.lower())
        else:
            stopwords.add(word)

    return stopwords

# --- 停用詞表（繁體中文） ---
def load_chinese_stopwords(filepath='lib/chinese_stopwords.txt'):
    try:
        with open(filepath, encoding='utf-8') as f:
            stopwords = set(line.strip() for line in f if line.strip())
    except:
        stopwords = set()
    return stopwords

# --- 停用詞表 (English) ---
def load_english_stopwords():
    # --- 讀取英文停用詞 ---
    from nltk.corpus import stopwords
    english_stopwords = set(stopwords.words('english'))
    return english_stopwords

# --- 基礎清理 ---
def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'-\s+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

# --- 檢測語言 (中文/英文) ---
def detect_pdf_language(doc, max_pages=10):
    if not doc:
        return "unknown"

    sample_text = ""
    for page_number, page in enumerate(doc):
        if page_number >= max_pages:
            break
        try:
            sample_text += page.get_text()
        except:
            continue

    chinese_chars = sum(1 for c in sample_text if '\u4e00' <= c <= '\u9fff')
    english_chars = sum(1 for c in sample_text if c.isascii() and c.isalpha())

    if chinese_chars > english_chars:
        return "chinese"
    elif english_chars > chinese_chars:
        return "english"
    else:
        return "unknown"

# --- 中文專用 Preprocessing ---
def preprocess_chinese_text(text):
    lazy_init_ckip_ws_driver()
    ws_driver = st.session_state.ckip_ws_driver

    start_time = time.time()

    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[^\u4e00-\u9fffA-Za-z]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    ws = ws_driver([text])[0]
    ws = [re.sub(r'\s+', '', w) for w in ws if w.strip()]

    # 加強版中文停用詞
    pdf_stopwords = load_pdf_stopwords()
    self_defined_stopwords = [
        "中", "年", "完成", "共好", "月", "董事", "董事會", "集團", "公司", "目標", "委員會", "兩", "高",
        "主題", "機制", "持續", "提", "提名", "發展", "職場", "參與", "經濟", "核心", "中央", "社會",
        "管理", "相關", "確保", "台灣", "海納", "次", "員工", "全球", "評估", "稽核", "年度", "幸福",
        "共贏", "包容", "單位", "至少", "客戶"
    ]
    chinese_stopwords = load_chinese_stopwords()
    all_stopwords = set(list(chinese_stopwords) + list(pdf_stopwords) + self_defined_stopwords)
    # for w in ws:
    #     for word in pdf_stopwords:
    #         if word == None:
    #             continue
    #         elif word.lower() in w.lower():
    #             all_stopwords.add(w)
    ws_filtered = [w for w in ws if w not in all_stopwords]

    elapsed_time = time.time() - start_time
    # print(f"Preprocess Chinese text completed in {elapsed_time:.2f} seconds.")
    return ws_filtered

# --- 英文專用 Preprocessing ---
def preprocess_english_text(text):
    start_time = time.time()

    # --- 基本清理 ---
    text = re.sub(r'<[^>]+>', '', text)  # 移除 HTML tag
    text = re.sub(r'[^\u0041-\u007A]', ' ', text)  # 移除非英文字母（保留空格）
    text = re.sub(r'\s+', ' ', text).strip().lower()  # 去多餘空白並轉小寫

    # --- 分詞 ---
    tokens = word_tokenize(text)

    # --- 停用詞 ---
    pdf_stopwords = load_pdf_stopwords()
    self_defined_stopwords = [
        "company", "report", "esg", "year", "group", "goal", "committee", "ensure", "management",
        "employee", "global", "evaluate", "sustainability", "development", "responsibility",
        "stakeholder", "board", "data", "information", "page", "section"
    ]
    english_stopwords = load_english_stopwords()

    all_stopwords = set(list(english_stopwords) + list(pdf_stopwords) + self_defined_stopwords)

    # --- 過濾停用詞 ---
    filtered_tokens = [w for w in tokens if w.isalpha() and w not in all_stopwords]

    elapsed_time = time.time() - start_time
    # print(f"Preprocess English text completed in {elapsed_time:.2f} seconds.")

    return filtered_tokens

# --- 擷取每頁內容 ---
def extract_text_by_page(doc, max_pages=40, skip_pages=[]):
    formatted_full_text = []
    total_items = len(doc)
    total_pages = min(total_items, max_pages)

    progress_bar = st.progress(0)
    status_text = st.empty()

    for page_number, page in enumerate(doc):
        if page_number >= max_pages:
            break
        if page_number + 1 in skip_pages:
            msg = f"⏭️ Skip page {page_number + 1}"
            print(msg)
            status_text.info(msg)
            continue

        try:
            text = clean_text(page.get_text())

            tables = page.find_tables()
            for table in tables:
                df = table.to_pandas()
                text += "\nTable:\n" + df.to_string() + "\n"

            print(f"Text length in page {page_number+1}: {len(text)}")

            formatted_full_text.append({
                "page": page_number + 1,
                "content": text
            })

            progress = (page_number + 1) / total_pages
            msg = f"Progress: {round(progress*100)}% | Processing {page_number+1}/{total_pages} pages"
            print(msg)
            progress_bar.progress(progress)
            status_text.info(msg)

        except Exception as e:
            error_msg = f"(extract_text_by_page) Error processing page {page_number+1}: {e}"
            print(error_msg)
            st.error(error_msg)

    print("Processing complete!")
    progress_bar.progress(1.0)
    status_text.success("✅ PDF processing complete!")

    # 自動偵測語言
    language = detect_pdf_language(doc)
    st.session_state["pdf_language"] = language
    st.info(f"🌏 Detected PDF language: **{language.upper()}**")

    return formatted_full_text

# --- 取得 PDF 內容 ---
def get_pdf_context(page="all") -> str:
    if "pdf_text" not in st.session_state:
        return ""

    # 取得 PDF 指定頁數
    if page != "all":
        for p in st.session_state["pdf_text"]:
            if p["page"] == page:
                content = p["content"]
                if p["content"] in ["", None, "None", "none"]:
                    content = "No contents have been extracted."
                return f"[Page {p['page']}]: {content}"
        return f"Page {page} not found."

    # 取得 PDF 全文
    result = []
    for p in st.session_state["pdf_text"]:
        content = p["content"]
        if content in ["", None, "None", "none"]:
            content = "No contents have been extracted."
        else:
            content = content  # 顯式寫出來供閱讀
        result.append(f"[Page {p['page']}]: {content}")

    return "\n\n".join(result)

# --- PDF預處理（自動分中文/英文）---
def preprocess_pdf_sentences(raw_text, tokenize=True):
    if not raw_text or not isinstance(raw_text, str):
        return []

    language = st.session_state.get("pdf_language", "auto")
    results = []

    page_paragraphs = raw_text.split("\n\n")

    for paragraph in page_paragraphs:
        cleaned = re.sub(r"\[Page\s*\d+\]:\s*", "", paragraph).strip()
        if not cleaned:
            continue

        if language == "chinese":
            tokens = preprocess_chinese_text(cleaned)
            if tokens:
                results.append(" ".join(tokens))
        else:
            if tokenize:
                # split_sentences = nltk.sent_tokenize(cleaned)
                # results.extend([s for s in split_sentences if s.strip()])
                tokens = preprocess_english_text(cleaned)
                results.append(" ".join(tokens))
            else:
                results.append(cleaned)

    return results
