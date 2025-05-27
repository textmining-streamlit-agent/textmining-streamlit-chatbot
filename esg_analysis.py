from pdf_context import get_pdf_context, preprocess_pdf_sentences
from agents.gemini_agent import chat_with_gemini
import streamlit as st
import re
import os
import nltk
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from wordcloud import WordCloud
from matplotlib import font_manager as fm
from ckip_transformers.nlp import CkipPosTagger

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
    language = st.session_state.get("pdf_language", "english")

    if language == "chinese":
        prompt = (
            "你是一位專業的 ESG 報告分析師。\n\n"
            "請根據下方企業永續報告的內容，分別針對三個構面進行**批判性分析與重點整理**：\n"
            "1. 🌿 環境（Environmental）：與氣候變遷、能源、碳排、資源使用、生物多樣性有關的政策與行動\n"
            "2. 🤝 社會（Social）：涉及員工、社區、客戶、教育、多元共融、員工照顧等人際互動面向\n"
            "3. 🏛️ 治理（Governance）：與公司治理、風險管理、董事會、資訊安全、政策制定有關的議題\n"
            "請針對每個構面提供以下資訊：\n"
            "1. **核心策略**：一句話描述該構面的整體方向與目標\n"
            "2. **關鍵行動**：條列 3~5 項具體實踐作法或措施（避免空泛口號）\n"
            "3. **待改善處**：指出內容中的缺口、模糊處、缺乏量化指標、或過於籠統的部分（如無則寫 N/A）\n\n"
            "請用下列 Markdown 格式回應：\n"
            "### 🌿 環境（Environmental）\n"
            "**核心策略**：...\n"
            "**關鍵行動**：\n"
            "- ...\n"
            "**待改善處**：\n"
            "- ...\n\n"
            "（依序接續列出 社會 與 治理）\n\n"
            "⚠️ 請避免同一項目出現在多個構面，需根據內容判斷最合適分類。\n"
            "⚠️ 若以下報告內容，你判斷不是一個 ESG 報告，則不用產出上述三個構面的分析，並提醒使用者上傳 ESG 報告。\n"
            "📄 報告內容如下：\n"
            f"{pdf_text}"
        )
    else:
        prompt = (
            "You are a professional ESG report analyst.\n\n"
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
            f"{pdf_text}"
        )

    with st.spinner("🤖 Gemini is reading and analyzing..."):
        result = chat_with_gemini(prompt, restrict = False)

    if language == "chinese":
        result = clean_chinese_markdown_spacing(result)

    return result

def get_english_noun_adj_tokens(tokens):
    pos_tags = pos_tag(tokens)
    filtered = [word for word, pos in pos_tags if pos.startswith("NN") or pos.startswith("JJ")]
    return filtered

def show_wordcloud(texts,
    title="ESG Word Cloud",
    classify_by_esg=False,
    show_trend=False,
    keyword="employee",
    years=None,
    language="english"
):
    if "pdf_text" not in st.session_state:
        st.warning("⚠️ Please upload a PDF for plotting.")
        return

    pdf_text = get_pdf_context(page="all")
    language = st.session_state.get("pdf_language", "english")

    # --- 圖的標題（從 session 中撈公司資訊） ---
    pdf_info = st.session_state.get("pdf_info", {})
    company = pdf_info.get("company_name", "Unknown Company")
    industry = pdf_info.get("industry", "Unknown Industry")
    year = pdf_info.get("report_year", "Unknown Year")
    full_title = f"{company} ({year})\n{industry} Sector"

    def plot_wordcloud(word_freq, title):
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
            ax.set_title(title, fontsize=10, fontproperties=font_prop)
        else:
            ax.set_title(title, fontsize=10)

        ax.axis("off")
        st.pyplot(fig)

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
    st.subheader("☁️ Aggregated Word Cloud")
    plot_wordcloud(tfidf_dict, title=title)

    # 為 ESG 分類圖提供 button 切換
    if st.button("🔄 Show E/S/G Word Clouds"):
        st.subheader("🔍 E / S / G Word Clouds")
        e_words, s_words, g_words = {}, {}, {}
        for i, (w, score) in enumerate(tfidf_dict.items()):
            r = i % 3
            if r == 0:
                e_words[w] = score
            elif r == 1:
                s_words[w] = score
            else:
                g_words[w] = score
        st.markdown("#### 🌿 Environmental")
        plot_wordcloud(e_words, "Environmental")

        st.markdown("#### 🤝 Social")
        plot_wordcloud(s_words, "Social")

        st.markdown("#### 🏩 Governance")
        plot_wordcloud(g_words, "Governance")

    if show_trend:
        st.markdown("---")
        st.subheader("📈 ESG Keyword Trend Plot")

        keyword = st.text_input("Enter keyword to analyze:", value=keyword)

        trend_mode = st.radio("Select Trend Plot Scenario", [
            "Scenario 2.1: Industry-wide (Cross-year)",
            "Scenario 2.2: Company Comparison (Same-year)"
        ])

        if trend_mode == "Scenario 2.1: Industry-wide (Cross-year)":
            # 模擬 demo
            year_score_map = {
                "2020": 0.85,
                "2021": 0.78,
                "2022": 0.41,
                "2023": 0.55
            }
            plot_industry_trend(keyword, year_score_map)

        elif trend_mode == "Scenario 2.2: Company Comparison (Same-year)":
            import pandas as pd
            # 模擬 demo
            df = pd.DataFrame({
                "Year": ["2023"] * 3,
                "Company": ["Uni-President", "I-Mei", "Wei-Chuan"],
                "Score": [0.43, 0.61, 0.57]
            })
            plot_company_comparison(keyword, df)

def plot_industry_trend(keyword, year_score_map):
    x = list(year_score_map.keys())
    y = list(year_score_map.values())

    fig, ax = plt.subplots()
    ax.bar(x, y, color="skyblue")
    ax.set_xlabel("Year")
    ax.set_ylabel("TF-IDF Score (Importance)")
    ax.set_title(f"Trend of '{keyword}' in the Industry (by Year)")
    st.pyplot(fig)

def plot_company_comparison(keyword, df):
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=df, x="Year", y="Score", hue="Company", ax=ax)
    ax.set_title(f"Trend of '{keyword}' Across Companies")
    ax.set_xlabel("Year")
    ax.set_ylabel("TF-IDF Score (Importance)")
    ax.legend(title="Company")
    st.pyplot(fig)