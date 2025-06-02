import json
import pandas as pd
import streamlit as st
import os
import nltk
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import plotly.express as px
from wordcloud import WordCloud
from ckip_transformers.nlp import CkipPosTagger
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List, Dict, Tuple

from db_utils.esg_report_db_utils import get_all_esg_reports
from pdf_context import get_pdf_context, preprocess_pdf_sentences
from agents.gemini_agent import chat_with_gemini

# 若部署在 Streamlit Cloud，自動加載這個路徑
nltk_data_path = "/home/appuser/.nltk_data"
if os.path.exists(nltk_data_path):
    nltk.data.path.append(nltk_data_path)

# 自動下載 NLTK 所需資源（避免雲端錯誤）
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

try:
    nltk.data.find("taggers/averaged_perceptron_tagger")
except LookupError:
    nltk.download("averaged_perceptron_tagger")

from nltk import pos_tag

# Should be refactored in other file
def clean_chinese_markdown_spacing(text):
    text = text.replace("。\n", "。\n\n").replace("。", "。\n")
    text = re.sub(r"(?<!\n)- ", r"\n- ", text)
    return text

def analyze_esg_from_pdf():
    pdf_text = get_pdf_context(page="all")
    # language = st.session_state.get("pdf_language", "english")
    lang_setting = st.session_state.get("lang_setting", "English")

    prompt = (
        "You are a professional ESG report analyst.\n\n"
        f"⚠️ Please output in {lang_setting}\n"
        "Please critically analyze the following ESG report and summarize findings into the **three official ESG dimensions**:\n"
        "1. 🌿 Environmental (E): climate change, energy, emissions, biodiversity, etc.\n"
        "2. 🤝 Social (S): employee relations, diversity, education, customer/community engagement\n"
        "3. 🏛️ Governance (G): board structure, transparency, cybersecurity, risk management, ethics\n\n"
        "For each of the three sections, return:\n"
        "- **Core Strategy**: One concise sentence that summarizes the main goal or policy direction\n"
        "- **Key Actions**: A bullet list (3–5 items) of clear, concrete actions or programs the company has taken.\n"
        "- **Areas for Improvement**: Any vague statements, missing indicators, repetitive info, or lack of quantitative support (write 'N/A' if none)\n\n"
        "⚠️ Avoid overlaps — each point should appear in only one category.\n"
        "⚠️ If applicable, comment on whether the actions include measurable KPIs, clear timelines, or observable outcomes — but also include meaningful qualitative efforts.\n"
        "⚠️ If the below content is not identified as a ESG report content, you dont have to analyze it, but gently remind users to upload ESG report.\n"
        "📄 ESG Report Content:\n"
        f"{pdf_text}\n"
    )

    with st.spinner("🤖 Gemini is reading and analyzing..."):
        result = chat_with_gemini(prompt, restrict = False)

    if lang_setting == "繁體中文":
        result = clean_chinese_markdown_spacing(result)

    return result

# Should be refactored in other file
def get_english_noun_adj_tokens(tokens):
    pos_tags = pos_tag(tokens)
    filtered = [word for word, pos in pos_tags if pos.startswith("NN") or pos.startswith("JJ")]
    return filtered

# 分析 E/S/G 關鍵詞並生成詞組
def analyze_esg_for_wordcloud(filtered_keywords):
    # 匯入 Gemini Agent
    try:
        from agents.gemini_agent import chat_with_gemini, extract_json_from_gemini_output
        GEMINI_ENABLED = bool(st.secrets.get("GEMINI_API_KEY", None))
    except Exception as e:
        GEMINI_ENABLED = False
        print(f"❌ Failed to import Gemini agent: {e}")
        st.warning(f"Gemini Agent not available: {e}")

    # 將 keyword dict 轉成文字（如 "keyword1: 123, keyword2: 87, ..."）
    keyword_str = ", ".join([f"{k}: {v}" for k, v in filtered_keywords.items()])

    # prompt 結構
    prompt = f"""
    You are an ESG assistant. Please classify the following keywords into three categories: Environmental, Social, and Governance.

    Only use the keywords provided, and assign each keyword to **one and only one** category.

    ⚠️ Only return pure JSON with no explanation, no markdown formatting, and no extra text.
    ✅ The JSON format should look exactly like:
    {{
        "Environmental": ["keyword1", "keyword2", ...],
        "Social": ["keyword3", "keyword4", ...],
        "Governance": ["keyword5", "keyword6", ...]
    }}

    Here are the keywords with their frequencies:

    {keyword_str}
    """

    # 呼叫 Gemini 並取得結果
    with st.spinner("🤖 Gemini is classifying the keywords into ESG dimensions..."):
        result = chat_with_gemini(prompt, restrict=False)

    # 嘗試將 Gemini 回傳的內容轉成 JSON
    try:
        cleaned = extract_json_from_gemini_output(result)
        classification = json.loads(cleaned)
        e_words = classification.get("Environmental", [])
        s_words = classification.get("Social", [])
        g_words = classification.get("Governance", [])
    except json.JSONDecodeError as e:
        # st.error("❌ Failed to parse Gemini response as JSON.")
        # st.text(result)
        st.info("⚠️ Unable to classify keywords into ESG categories. Please check the response.")
        raise e

    return e_words, s_words, g_words

# --- E/S/G 分類圖 ---
def render_esg_split_wordclouds(tfidf_dict, language, display="expander"):
    e_worddict, s_worddict, g_worddict = {}, {}, {}

    # Get Top 50 filtered words
    filtered_keywords = dict(sorted(tfidf_dict.items(), key=lambda item: item[1], reverse=True)[:100])

    e_words, s_words, g_words = analyze_esg_for_wordcloud(filtered_keywords)
    for word, score in filtered_keywords.items():
        if word in e_words:
            e_worddict[word] = score
        elif word in s_words:
            s_worddict[word] = score
        elif word in g_words:
            g_worddict[word] = score

    if display == "expander":
        st.markdown("---")
        st.subheader("🔍 E / S / G Word Clouds")
        with st.expander(f"🌿 Environmental", expanded=False):
            plot_wordcloud(e_worddict, title="Environmental Word Cloud", language=language)

        with st.expander(f"🤝 Social", expanded=False):
            plot_wordcloud(s_worddict, title="Social Word Cloud", language=language)

        with st.expander(f"🏛️ Governance", expanded=False):
            plot_wordcloud(g_worddict, title="Governance Word Cloud", language=language)
    else:
        # col2, col3, col4 = st.columns(3)
        col2, col3, col4 = display[0], display[1], display[2]
        with col2:
            st.markdown("### 🌿 Environmental")
            plot_wordcloud(e_worddict, title="Environmental Word Cloud", language=language)
        with col3:
            st.markdown("### 🤝 Social")
            plot_wordcloud(s_worddict, title="Social Word Cloud", language=language)
        with col4:
            st.markdown("### 🏛️ Governance")
            plot_wordcloud(g_worddict, title="Governance Word Cloud", language=language)

def plot_wordcloud(word_freq, title, language):
    FONT_PATH = os.path.join("fonts", "TaipeiSansTCBeta-Regular.ttf")
    try:
        wc = WordCloud(
            font_path=FONT_PATH if language == "chinese" else None,
            width=800,
            height=500,
            background_color="white"
        ).generate_from_frequencies(word_freq)
    except Exception as e:
        wc = WordCloud(width=800, height=500, background_color="white").generate_from_frequencies(word_freq)

    fig, ax = plt.subplots()
    ax.imshow(wc, interpolation='bilinear')
    if language == "chinese":
        font_prop = fm.FontProperties(fname=FONT_PATH)
        ax.set_title(title, fontsize=12, fontproperties=font_prop)
    else:
        ax.set_title(title, fontsize=12)
    ax.axis("off")
    st.pyplot(fig)
    plt.close(fig)

# 計算 TF-IDF 並根據詞性過濾關鍵詞
def compute_tfidf_with_filter(
    sentences: List[str],
    language: str = "english"
) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    計算 TF-IDF 並根據詞性過濾關鍵詞。

    參數:
        sentences: 一個句子列表。
        language: "english" 或 "chinese"，決定詞性過濾方式。

    回傳:
        - tfidf_dict: 所有詞的 TF-IDF 分數。
        - filtered: 根據詞性過濾後的詞與其分數。
    """
    tfidf = TfidfVectorizer()
    tfidf_matrix = tfidf.fit_transform(sentences)
    all_scores = tfidf_matrix.sum(axis=0).A1
    tokens = tfidf.get_feature_names_out()
    tfidf_dict = dict(zip(tokens, all_scores))

    if language.lower() == "chinese":
        pos_tagger = CkipPosTagger()
        words = list(tfidf_dict.keys())
        pos_tags = pos_tagger([words])[0]
        valid_pos_prefix = ("N", "V", "A")
        filtered = {
            w: tfidf_dict[w]
            for w, pos in zip(words, pos_tags)
            if any(pos.startswith(p) for p in valid_pos_prefix)
        }
    else:
        # 請先定義此函數以處理英文詞性過濾
        filtered_words = get_english_noun_adj_tokens(list(tfidf_dict.keys()))
        filtered = {
            w: tfidf_dict[w]
            for w in filtered_words
        }

    return tfidf_dict, filtered

# 模擬 TF-IDF 計算 Scenario 2.1
def compute_trend_by_year(texts_by_year, keyword):

    years, texts = [], []

    for year, docs in texts_by_year.items():
        for doc in docs:
            if doc and doc.strip():
                years.append(year)
                texts.append(doc)
    if not texts:
        return {}

    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return {}

    vocab = vectorizer.vocabulary_

    year_score_map = {}
    for i, year in enumerate(years):
        score = 0.0
        if keyword.lower() in vocab:
            idx = vocab[keyword.lower()]
            score = tfidf_matrix[i, idx]
        year_score_map[year] = year_score_map.get(year, 0.0) + score

    return year_score_map

# 模擬 TF-IDF 計算 Scenario 2.2
def compute_company_trend_df(company_texts, keyword):
    texts = [entry["Text"] for entry in company_texts if entry["Text"] and entry["Text"].strip()]
    if not texts:
        return pd.DataFrame()

    vectorizer = TfidfVectorizer()
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return pd.DataFrame()

    vocab = vectorizer.vocabulary_
    data = []
    for i, entry in enumerate(company_texts):
        score = 0.0
        if keyword.lower() in vocab:
            idx = vocab[keyword.lower()]
            score = tfidf_matrix[i, idx]
        data.append({
            "Year": entry["Year"],
            "Company": entry["Company"],
            "Score": score
        })
    return pd.DataFrame(data)

# Trend plot - Scenario 2.1
def plot_industry_trend(keyword, year_score_map, industry, language):
    sorted_years = sorted(year_score_map.keys())
    x = sorted_years
    y = [year_score_map[yr] for yr in x]

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(x, y, color="skyblue")

    if language == "english":
        ax.set_title(f"Trend of `{keyword}` in the {industry} Industry (by Year)", fontsize=10)
    elif language == "chinese":
        FONT_PATH = os.path.join("fonts", "TaipeiSansTCBeta-Regular.ttf")
        font_prop = fm.FontProperties(fname=FONT_PATH)
        ax.set_title(f"Trend of `{keyword}` in the {industry} Industry (by Year)", fontsize=10, fontproperties=font_prop)

    ax.set_xlabel("Year", fontsize=9)
    ax.set_ylabel("TF-IDF Score (Importance)", fontsize=9)
    ax.tick_params(axis='x', labelsize=8)
    ax.tick_params(axis='y', labelsize=8)

    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=6)
    st.pyplot(fig)

# Trend plot - Scenario 2.2
def plot_company_comparison(keyword, df, industry):
    fig = px.bar(
        df,
        x="Year",
        y="Score",
        color="Company",
        barmode="group",
        text_auto=".2f",
        title=f"Trend of `{keyword}` Across Companies in the {industry} Industry"
    )

    fig.update_layout(
        width=700,
        height=450,
        font=dict(size=10),
        legend_title_text='Company',
        xaxis_title="Year",
        yaxis_title="TF-IDF Score (Importance)",
        margin=dict(l=20, r=20, t=40, b=40),
    )

    st.plotly_chart(fig, use_container_width=True)

# --- 趨勢圖 ---
def render_trend_section(keyword, industry):
    st.markdown("---")
    st.subheader("📈 ESG Keyword Trend Plot")

    if "trend_keyword" not in st.session_state:
        st.session_state["trend_keyword"] = keyword  # 預設值由外部傳入

    # 使用者可以更新這個 keyword
    st.session_state["trend_keyword"] = st.text_input("Enter keyword to analyze:", value=st.session_state["trend_keyword"])
    keyword = st.session_state["trend_keyword"]

    trend_mode = st.radio("Select Trend Plot Scenario", [
        "Industry-wide (Cross-year)",
        "Company Comparison (Cross-year)"
    ])

    pdf_language = st.session_state["pdf_language"]
    df = get_all_esg_reports()
    if pdf_language == "english":
        df = df[df["industry"] == industry]
    if pdf_language == "chinese":
        df = df[df["industry_zh"] == industry]
    # print("🔍 Filtered DataFrame for industry:", df)

    if trend_mode == "Industry-wide (Cross-year)":
        texts_by_year = {}
        for _, row in df.iterrows():
            year = str(row["year"])
            texts_by_year.setdefault(year, []).append(row["content"])
        year_score_map = compute_trend_by_year(texts_by_year, keyword)
        if not year_score_map or all(v == 0 for v in year_score_map.values()):
            # st.info(f"📊 No TF-IDF value found for keyword: `{keyword}` in selected `{industry}` industry.")
            st.warning(f"⚠️ Keyword: `{keyword}` not found in selected `{industry}` industry.")
            return
        plot_industry_trend(keyword, year_score_map, industry, pdf_language)

    elif trend_mode == "Company Comparison (Cross-year)":
        sample_data = df[["year", "company", "content"]].rename(
            columns={"year": "Year", "company": "Company", "content": "Text"}
        ).to_dict(orient="records")
        if not sample_data:
            st.warning(f"⚠️ Keyword: `{keyword}` not found in all companies.")
            return

        trend_df = compute_company_trend_df(sample_data, keyword)
        if trend_df['Score'].sum() == 0:
            st.warning(f"⚠️ Keyword: `{keyword}` not found in all companies.")
            return
        plot_company_comparison(keyword, trend_df, industry)

# 主程式
def esg_charts(
    pdf_texts=None, # for agent tools
    keyword="employee", # for agent tools
    industry="Unknown Industry", # for agent tools
    language="english" # for agent tools
):
    # --- 通用輸入來源（chat-trigger 或 button-trigger 都能用） ---
    if "pdf_text" in st.session_state:
    # if "pdf_text" in st.session_state\
        # and st.session_state["show_wordcloud_trigger"]: # 檢查是否 triggered by btn
        pdf_text = get_pdf_context(page="all")
        pdf_language = st.session_state.get("pdf_language", "english")
        pdf_info = st.session_state.get("pdf_info", {})
        company = pdf_info.get("company_name", "Unknown Company")
        industry = pdf_info.get("industry", "Unknown Industry")
        year = pdf_info.get("report_year", "Unknown Year")
        full_title = f"{company} ({year})\n{industry} industry"

        sentences = preprocess_pdf_sentences(pdf_text, tokenize=True)
        if not sentences:
            st.warning("⚠️ No valid sentences extracted.")
            return

        tfidf_dict, filtered = compute_tfidf_with_filter(sentences, pdf_language)

        if st.session_state.get("show_aggregated", False):
            st.markdown("---")
            st.subheader("☁️ Aggregated Word Cloud")
            # No POS filtering for aggregated word cloud
            # plot_wordcloud(tfidf_dict, title=full_title, language=pdf_language)
            # POS filtering for aggregated word cloud
            plot_wordcloud(filtered, title=full_title, language=pdf_language)

        if st.session_state.get("first_clicked") == "esg":
            if st.session_state.get("show_esg_wordclouds"):
                render_esg_split_wordclouds(tfidf_dict, pdf_language)
            if st.session_state.get("show_trend_plot"):
                render_trend_section(keyword, industry)

        elif st.session_state.get("first_clicked") == "trend":
            if st.session_state.get("show_trend_plot"):
                render_trend_section(keyword, industry)
            if st.session_state.get("show_esg_wordclouds"):
                render_esg_split_wordclouds(tfidf_dict, pdf_language)

    else:
        st.warning("⚠️ Please upload a PDF for plotting word cloud.")

    # Cross Comparison of Companies in Industry
    if pdf_texts:
        st.markdown("---")
        st.subheader(f"📊 Cross Comparison of companies in {industry} industry:")
        for year, company_texts in pdf_texts.items():
            st.markdown(f"### 🕑 Year {year}")
            for company, pdf_text in company_texts.items():
                # st.markdown(f"### {company} ({year})")
                with st.expander(f"🏬 Company - {company} ({year})", expanded=False):
                    sentences = preprocess_pdf_sentences(pdf_text, tokenize=True)
                    tfidf_dict, filtered = compute_tfidf_with_filter(sentences, language)

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown("### Total")
                        # plot_wordcloud(tfidf_dict, f"{year} - {company} - {industry}", language)
                        plot_wordcloud(filtered, f"{year} - {company} - {industry}", language)

                    # st.markdown("---")
                    render_esg_split_wordclouds(filtered, language, display=[col2, col3, col4])
        st.session_state.pop("pdf_texts_for_cross_comparison", None)

def init_cross_comparison_data(industry: str, years: list[int]):
    df = get_all_esg_reports()
    df = df.drop_duplicates(subset=["company", "year"], keep="first")  # 去除重複公司年度

    if industry in df["industry"].unique().tolist():
        df = df[df["industry"] == industry]
    elif industry in df["industry_zh"].unique().tolist():
        df = df[df["industry_zh"] == industry]
    else:
        st.warning(f"⚠️ Industry `{industry}` not found in the database. Please check the industry name and try the cross comparison again.")
        return {}

    years = [int(year) for year in years]
    df = df[df["year"].isin(years)]

    pdf_texts = {}
    for _, row in df.iterrows():
        year = int(row["year"])
        company = row["company"]
        content = row["content"]
        if year not in pdf_texts:
            pdf_texts[year] = {}
        pdf_texts[year][company] = content

    # 將資料存入 session_state
    if "show_wordcloud_trigger" in st.session_state:
        st.session_state["pdf_texts_for_cross_comparison"] = pdf_texts
        st.session_state["industry"] = industry # industry for cross comparison
        st.session_state["first_clicked"] = "industry_companies"
        st.rerun()
    else:
        st.session_state["pdf_texts_for_cross_comparison"] = pdf_texts
        st.session_state["industry"] = industry # industry for cross comparison
        st.session_state["show_aggregated"] = True
        return pdf_texts

# Control panel
def show_wordcloud_controls():
    if "pdf_text" not in st.session_state:
        # st.warning("⚠️ Please upload a PDF for plotting word cloud.")
        return

    st.markdown("---")
    with st.container():
        col_title, col_close = st.columns([0.95, 0.05])
        with col_title:
            st.subheader("📊 Please select the mode you want to display:")
            # st.markdown("#### Please select the mode you want to display:")
        with col_close:
            if st.button("❌", key=f"close_wordcloud_controls"):
                st.session_state.pop("show_aggregated", None)
                st.session_state.pop("show_esg_wordclouds", None)
                st.session_state.pop("show_trend_plot", None)
                st.session_state.pop("show_comparison", None)
                st.session_state.pop("first_clicked", None)
                st.session_state.pop("industry", None)
                st.session_state.pop("pdf_texts_for_cross_comparison", None)
                st.session_state["show_wordcloud_trigger"] = False
                st.rerun()

        show_aggregated = st.session_state.get("show_aggregated", False)
        cols = st.columns(5)
        # E / S / G Word Clouds
        with cols[0]:
            if st.button("📥 E / S / G Word Clouds"):
                if st.session_state.get("show_esg_wordclouds", False):
                    st.info("✅ E / S / G plots are already shown above.")
                else:
                    st.session_state["first_clicked"] = "esg"
                    st.session_state["show_aggregated"] = True
                    st.session_state["show_esg_wordclouds"] = True
                    st.session_state["show_wordcloud_trigger"] = True
                    st.session_state["show_comparison"] = False
                    st.rerun()
        # Trend Plot
        with cols[1]:
            if st.button("📈 Trend Plot"):
                if st.session_state.get("show_trend_plot", False):
                    st.info("✅ Trend plots are already shown above.")
                else:
                    st.session_state["first_clicked"] = "trend"
                    st.session_state["show_aggregated"] = True
                    st.session_state["show_trend_plot"] = True
                    st.session_state["show_wordcloud_trigger"] = True
                    st.session_state["show_comparison"] = False
                    st.rerun()

        # Cross comparison: WordCloud by Company in Industry
        with cols[2]:
            if st.button("🏢 Cross Comparison"):
                if st.session_state.get("show_comparison", False):
                    st.info("✅ Company comparison is already shown above.")

                st.session_state["first_clicked"] = "industry_companies"
                st.session_state["show_aggregated"] = True
                st.session_state["show_esg_wordclouds"] = False
                st.session_state["show_trend_plot"] = False
                st.session_state["show_comparison"] = True
                st.session_state["show_wordcloud_trigger"] = True
                init_cross_comparison_data("Food", [2022, 2023])
                st.rerun()

        # Aggregated 恢復按鈕
        with cols[3]:
            if not show_aggregated:
                if st.button("🔁 Show Aggregated Wordcloud"):
                    st.session_state["show_aggregated"] = True
                    st.session_state["show_wordcloud_trigger"] = True
                    st.rerun()

        # Clear
        with cols[4]:
            if st.button("🧹 Clear Plot"):
                st.session_state["show_aggregated"] = False
                st.session_state["show_esg_wordclouds"] = False
                st.session_state["show_trend_plot"] = False
                st.session_state["show_comparison"] = False
                st.session_state.pop("industry", None)
                st.session_state.pop("pdf_texts_for_cross_comparison", None)
                # st.session_state["show_wordcloud_trigger"] = False
                st.session_state.pop("first_clicked", None)
                st.rerun()
