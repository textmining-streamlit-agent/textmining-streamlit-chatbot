from pdf_context import get_pdf_context, preprocess_pdf_sentences
from agents.gemini_agent import chat_with_gemini
import json
import pandas as pd
import streamlit as st
import re
import os
import nltk
import matplotlib.pyplot as plt
import plotly.express as px
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from wordcloud import WordCloud
from matplotlib import font_manager as fm
from ckip_transformers.nlp import CkipPosTagger
from db_utils.esg_report_db_utils import get_all_esg_reports

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

def get_english_noun_adj_tokens(tokens):
    pos_tags = pos_tag(tokens)
    filtered = [word for word, pos in pos_tags if pos.startswith("NN") or pos.startswith("JJ")]
    return filtered

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
    with st.spinner("🤖 Gemini is classifying the keywords showinto ESG dimensions..."):
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

# 模擬 TF-IDF 計算 Scenario 2.1
def compute_trend_by_year(texts_by_year, keyword):

    years = []
    texts = []

    for year, docs in texts_by_year.items():
        for doc in docs:
            years.append(year)
            texts.append(doc)

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(texts)
    vocab = vectorizer.vocabulary_

    year_score_map = {}
    for i, year in enumerate(years):
        if keyword.lower() in vocab:
            idx = vocab[keyword.lower()]
            score = tfidf_matrix[i, idx]
        else:
            score = 0.0
        year_score_map[year] = year_score_map.get(year, 0.0) + score

    return year_score_map

# 模擬 TF-IDF 計算 Scenario 2.2
def compute_company_trend_df(company_texts, keyword):
    texts = [entry["Text"] for entry in company_texts]
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(texts)
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
def plot_industry_trend(keyword, year_score_map, industry):
    sorted_years = sorted(year_score_map.keys())
    x = sorted_years
    y = [year_score_map[yr] for yr in x]

    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(x, y, color="skyblue")

    ax.set_title(f"Trend of '{keyword}' in the {industry} Industry (by Year)", fontsize=10)
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
        title=f"Trend of '{keyword}' Across Companies in the {industry} Industry"
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

def esg_charts(
    texts=None,
    title="ESG Word Cloud",
    classify_by_esg=False,
    show_trend=False,
    keyword="employee",
    years=None,
    language="english"
    ):
    if "pdf_text" not in st.session_state:
        st.warning("⚠️ Please upload a PDF for plotting word cloud.")
    else:
        pdf_text = get_pdf_context(page="all")
        language = st.session_state.get("pdf_language", "english")

    # --- 圖的標題（從 session 中撈公司資訊） ---
    pdf_info = st.session_state.get("pdf_info", {})
    company = pdf_info.get("company_name", "Unknown Company")
    industry = pdf_info.get("industry", "Unknown Industry")
    year = pdf_info.get("report_year", "Unknown Year")
    full_title = f"{company} ({year})\n{industry} Sector"

    # --- TF-IDF + POS ---
    sentences = preprocess_pdf_sentences(pdf_text, tokenize=True)
    if not sentences:
        st.warning("⚠️ No valid sentences extracted.")
        return

    tfidf = TfidfVectorizer()
    tfidf_matrix = tfidf.fit_transform(sentences)
    all_scores = tfidf_matrix.sum(axis=0).A1
    tokens = tfidf.get_feature_names_out()
    tfidf_dict = dict(zip(tokens, all_scores))

    if language == "chinese":
        words = list(tfidf_dict.keys())
        pos_tagger = CkipPosTagger()
        pos_tags = pos_tagger([words])[0]
        valid_pos_prefix = ("N", "V", "A")
        filtered = {
            w: tfidf_dict[w]
            for w, pos in zip(words, pos_tags)
            if any(pos.startswith(p) for p in valid_pos_prefix)
        }
    else:
        filtered = tfidf_dict.copy()
        filtered = {w: tfidf_dict[w] for w in get_english_noun_adj_tokens(list(tfidf_dict.keys()))}

    # --- 圖顯示邏輯 ---
    # 先顯示整合圖
    if st.session_state.get("show_aggregated", False):
        st.subheader("☁️ Aggregated Word Cloud")
        plot_wordcloud(tfidf_dict, title=full_title, language=language)

    if st.session_state.get("first_clicked") == "esg":
        if st.session_state.get("show_esg_wordclouds"):
            st.subheader("🔍 E / S / G Word Clouds")
            e_words, s_words, g_words = {}, {}, {}
            for i, (w, score) in enumerate(tfidf_dict.items()):
                r = i % 3
                if r == 0: e_words[w] = score
                elif r == 1: s_words[w] = score
                else: g_words[w] = score
            st.markdown("#### 🌿 Environmental")
            plot_wordcloud(e_words, f"{year} - {company} - Environmental Word Cloud - {industry}", language)
            st.markdown("#### 🤝 Social")
            plot_wordcloud(s_words, f"{year} - {company} - Social Word Cloud - {industry}", language)
            st.markdown("#### 🏩 Governance")
            plot_wordcloud(g_words, f"{year} - {company} - Governance Word Cloud - {industry}", language)

        if st.session_state.get("show_trend_plot"):
            st.subheader("📈 ESG Keyword Trend Plot")
            keyword = st.text_input("Enter keyword to analyze:", value=keyword)
            trend_mode = st.radio("Select Trend Plot Scenario", [
                "Industry-wide (Cross-year)",
                "Company Comparison (Cross-year)"
            ])

            if trend_mode == "Industry-wide (Cross-year)":
                df = get_all_esg_reports()
                texts_by_year = {}
                for _, row in df.iterrows():
                    year = str(row["year"])
                    text = row["content"]
                    texts_by_year.setdefault(year, []).append(text)

                year_score_map = compute_trend_by_year(texts_by_year, keyword)
                plot_industry_trend(keyword, year_score_map, industry)

            else:
                sample_data_df = get_all_esg_reports()
                industry = st.session_state.get("pdf_info", {}).get("industry")
                sample_data_df = sample_data_df[sample_data_df["industry"] == industry]
                sample_data = sample_data_df[["year", "company", "content"]].rename(
                    columns={"year": "Year", "company": "Company", "content": "Text"}
                ).to_dict(orient="records")

                df = compute_company_trend_df(sample_data, keyword)
                plot_company_comparison(keyword, df, industry)

    elif st.session_state.get("first_clicked") == "trend":
        if st.session_state.get("show_trend_plot"):
            st.subheader("📈 ESG Keyword Trend Plot")
            keyword = st.text_input("Enter keyword to analyze:", value=keyword)
            trend_mode = st.radio("Select Trend Plot Scenario", [
                "Industry-wide (Cross-year)",
                "Company Comparison (Cross-year)"
            ])

            if trend_mode == "Industry-wide (Cross-year)":
                df = get_all_esg_reports()
                texts_by_year = {}
                for _, row in df.iterrows():
                    year = str(row["year"])
                    text = row["content"]
                    texts_by_year.setdefault(year, []).append(text)

                year_score_map = compute_trend_by_year(texts_by_year, keyword)
                plot_industry_trend(keyword, year_score_map, industry)

            else:
                sample_data_df = get_all_esg_reports()
                sample_data = sample_data_df[["year", "company", "content"]].rename(
                    columns={"year": "Year", "company": "Company", "content": "Text"}
                ).to_dict(orient="records")
                
                df = compute_company_trend_df(sample_data, keyword)
                plot_company_comparison(keyword, df, industry)

        if st.session_state.get("show_esg_wordclouds"):
            st.subheader("🔍 E / S / G Word Clouds")
            e_words, s_words, g_words = {}, {}, {}
            for i, (w, score) in enumerate(tfidf_dict.items()):
                r = i % 3
                if r == 0: e_words[w] = score
                elif r == 1: s_words[w] = score
                else: g_words[w] = score
            st.markdown("#### 🌿 Environmental")
            plot_wordcloud(e_words, f"{year} - {company} - Environmental Word Cloud - {industry}", language)
            st.markdown("#### 🤝 Social")
            plot_wordcloud(s_words, f"{year} - {company} - Social Word Cloud - {industry}", language)
            st.markdown("#### 🏩 Governance")
            plot_wordcloud(g_words, f"{year} - {company} - Governance Word Cloud - {industry}", language)

# Control panel
def show_wordcloud_controls():
    st.markdown("---")
    st.markdown("#### Please select the mode you want to display:")
    if not st.session_state.get("show_aggregated", False):
        # Clear (Aggregated 也被清除) 後，出現四顆按鈕
        col1, col2, col3, col4 = st.columns(4)
    else:
        # 平常只顯示三顆按鈕
        col1, col2, col3 = st.columns(3)
        col4 = None

    with col1:
        if st.button("📥 E / S / G Word Clouds"):
            if st.session_state.get("show_esg_wordclouds", False):
                st.info("✅ E / S / G plots are already shown above.")
            else:
                if "first_clicked" not in st.session_state:
                    st.session_state["first_clicked"] = "esg"
                st.session_state["show_aggregated"] = True
                st.session_state["show_esg_wordclouds"] = True
                st.session_state["show_wordcloud_trigger"] = True
                st.rerun()

    with col2:
        if st.button("📈 Trend Plot"):
            if st.session_state.get("show_trend_plot", False):
                st.info("✅ Trend plot already shown above.")
            else:
                if "first_clicked" not in st.session_state:
                    st.session_state["first_clicked"] = "trend"
                st.session_state["show_aggregated"] = True
                st.session_state["show_trend_plot"] = True
                st.session_state["show_wordcloud_trigger"] = True
                st.rerun()

    with col3:
        if st.button("🧹 Clear WordClouds"):
            st.session_state["show_wordcloud_trigger"] = True
            st.session_state["show_aggregated"] = False
            st.session_state["show_esg_wordclouds"] = False
            st.session_state["show_trend_plot"] = False
            if st.session_state.get("show_esg_wordclouds") is False and st.session_state.get("show_trend_plot") is False:
                st.session_state.pop("first_clicked", None)
            st.rerun()

    # 額外的恢復按鈕（只在 Aggregated 被清除時出現）
    if col4:
        with col4:
            if st.button("🔁 Show Aggregated Wordcloud"):
                st.session_state["show_aggregated"] = True
                st.rerun()
