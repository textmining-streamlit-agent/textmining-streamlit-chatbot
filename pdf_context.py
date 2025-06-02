import streamlit as st
import re
import os
import pandas as pd
import nltk
from nltk import word_tokenize, ngrams, FreqDist
from nltk.tokenize import MWETokenizer
import time
from collections import Counter
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

# --- 手動 bi-gram list ---
def apply_manual_bigrams(tokens: list, manual_list: list = [], separator: str = "_") -> list:
    """
    將手動指定的詞組合併為 multi-word tokens。

    參數：
        tokens (list): 預處理過的英文 token list。
        manual_list (list): 每個元素為詞組（用空格分開的 string），例如 "carbon footprint"。
        separator (str): 合併後使用的連接符號（預設為 "_"）。

    回傳：
        List[str]: 合併 multi-word expressions 後的新 token list。
    """
    mw_tokenizer = MWETokenizer(separator=separator)

    # 將字串轉成 tuple，供 MWETokenizer 使用
    manual_mwe_list = ["carbon footprint", "net zero", "greenhouse gas", "supply chain"]
    if manual_list:
        manual_mwe_list += manual_list
    for mwe in manual_mwe_list:
        terms = tuple(mwe.strip().lower().split())
        if len(terms) >= 2:
            mw_tokenizer.add_mwe(terms)

    # 合併
    return mw_tokenizer.tokenize(tokens)

# --- 英文專用 bi-gram ---
def extract_important_bigrams(tokens: list, min_freq: int = 8, top_n: int = 50):
    """
    從單詞 tokens 中抽取出高頻 bi-grams，並將其合併為 multi-word tokens。

    參數：
        tokens (list): 已處理過的英文 token list。
        min_freq (int): bi-gram 最低頻率門檻。
        top_n (int): 最多挑選前 N 個高頻 bi-grams。

    回傳：
        List[str]: 包含 uni-gram + 合併 bi-gram 的最終 token list。
    """
    # 建立 bi-gram 清單
    bigrams_list = list(ngrams(tokens, 2))
    if not bigrams_list:
        return tokens

    # 統計 bi-gram 頻率
    fdist = FreqDist(bigrams_list)
    bigram_counter = Counter(fdist)
    sorted_fdist = bigram_counter.most_common()

    # 選出重要 bi-grams：頻率高、最多 top_n 個
    important_bigrams = [(bg, freq) for bg, freq in sorted_fdist if freq >= min_freq][:top_n]
    if not important_bigrams:
        return tokens

    # 初始化 MWETokenizer，加入重要 bi-grams
    mw_tokenizer = MWETokenizer(separator="_")
    for bigram, _ in important_bigrams:
        mw_tokenizer.add_mwe(bigram)

    # 合併 bi-grams（如 "climate" + "change" ➝ "climate_change"）
    final_tokens = mw_tokenizer.tokenize(tokens)

    # Debug message
    # print("\n🔍 Top bi-grams extracted:")
    # for bigram, freq in important_bigrams:
    #     print(f"{' '.join(bigram)}  ➝  freq: {freq}")

    return final_tokens

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
                tokens = extract_important_bigrams(tokens, min_freq=10, top_n=50)
                tokens = apply_manual_bigrams(tokens)
                results.append(" ".join(tokens))
            else:
                results.append(cleaned)

    return results

# --- Bag of Words ---
def get_bag_of_words(sentences: list[str]) -> list[str]:
    """
    從斷詞後的句子中萃取 Bag of Words（包含 unigram 和合併後的 bi-gram）。

    參數:
        sentences (List[str]): 每句為經過斷詞 + bigram 合併的句子（以空格分開）

    回傳:
        List[str]: 所有出現過的詞項（無重複），適用於 Trend Plot 下拉選單
    """
    word_set = set()
    for line in sentences:
        for token in line.strip().split():
            if token:
                word_set.add(token)

    return sorted(list(word_set))

def generate_cleaned_pdf_pages() -> dict:
    """
    回傳 Dict，每一頁為 key，value 是經過 LLM 格式化的內容。
    """
    raw_text = get_pdf_context()
    if not raw_text:
        return {}

    from agents.gemini_agent import chat_with_gemini

    pdf_lang = st.session_state.get("pdf_language", "english")
    pages = re.split(r"\[Page (\d+)\]:", raw_text)
    page_dict = {}

    for i in range(1, len(pages), 2):
        page_num = pages[i]
        content = pages[i + 1].strip()

        content = re.sub(r"(Table:.*?)((None\s*){3,})", "", content, flags=re.DOTALL)
        content = re.sub(r"(Appendix|Contents|Table of.*?|Col\d+)", "", content, flags=re.IGNORECASE)
        content = re.sub(r"\b\d{1,3}\b", "", content)
        content = re.sub(r"\s{2,}", " ", content)
        content = re.sub(r"\n{2,}", "\n", content)
        content = re.sub(r"(None\s+){5,}", "", content)
        content = content.strip()

        if not content:
            continue

        if pdf_lang == "chinese":
            prompt = f"""
        你是一位只做格式優化的編輯，請依照以下規則處理 PDF 第 {page_num} 頁的文字內容：

        1. 保留所有文字原樣，不要刪除、改寫或補充內容。
        2. 若內容看起來像「目錄」「小節標題」或「條列清單」，請加上換行與適當符號（如 `-`）
        3. 若內容看起來像斷論文字，則保留段落格式，要有標點符號，看起來是真的在閱讀報告的形式。
        4. 若出現表格欄位（如 None 或 metric 資料），請用清單列出，避免 Markdown 表格。
        5. 若出現 `()` 或未填資料，請保持原樣，不要補內容。
        6. 請用 Markdown 標題與段落呈現，例如 `###` 或空行分段。
                    \n\n內容如下：
        {content}
        """
        else:
            prompt = f"""
        You are a formatting assistant. Please process page {page_num} using the following rules:

        1. Do not delete or rewrite anything.
        2. Use bullet points `-` or `●` and `###` headings when appropriate.
        3. Do not create Markdown tables, just list metrics as lines.
        4. Keep placeholders like `()` or `...` untouched.
        5. Format the result using Markdown with line breaks and spacing.
        Content:
        {content}
        """

        try:
            result = chat_with_gemini(prompt, restrict=False)
        except Exception as e:
            result = f"⚠️ Failed on Page {page_num}: {e}"

        page_dict[int(page_num)] = result.strip()

    return page_dict

def render_cleaned_pdf_viewer_with_selector():
    """
    顯示可切換頁碼的 Viewer，用下拉選單控制每次顯示一頁。
    """
    st.markdown("## 📄 PDF Viewer")

    if "cached_cleaned_pages" not in st.session_state:
        st.info("📥 Generating cleaned pages from PDF...")
        cleaned_pages = generate_cleaned_pdf_pages()
        st.session_state["cached_cleaned_pages"] = cleaned_pages
    else:
        cleaned_pages = st.session_state["cached_cleaned_pages"]

    if not cleaned_pages:
        st.warning("❗ No cleaned content available.")
        return

    page_list = sorted(cleaned_pages.keys())
    selected = st.selectbox("📑 Select page to view", page_list)

    with st.container(border=True):
        st.markdown(f"### 🧾 Page {selected}")
        st.markdown(cleaned_pages[selected], unsafe_allow_html=True)