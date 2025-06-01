import json
import streamlit as st
import requests
from openai import OpenAI
from db_utils.profile_db_utils import *
from qa_utils.Word2vec import view_2d, view_3d, cbow_skipgram
from ui_utils.pdf_upload_section import render_pdf_upload_section
from ui_utils.chat_section import *
from ui_utils.profile_section import render_profile_section
from ui_utils.ui_utils import *
from pdf_context import *
from esg_analysis import *
from ui_utils.esg_reports_section import show_esg_report_table
from optimize_esg_report import optimize_esg_report

import os
os.environ["STREAMLIT_WATCHER_TYPE"] = "none"  # 🔧 關掉 watcher，避免觸發 torch.classes bug

def is_valid_image_url(url):
    try:
        response = requests.get(url, timeout=2)
        if response.status_code == 200 and 'image' in response.headers["Content-Type"]:
            return True
        else:
            return False
    except:
        return False

def load_example_from_json(json_path, key):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(key, "")

def render_sidebar(chat_container):
    with st.sidebar:
        st_c_1 = st.container(border=True)
        with st_c_1:
            user_image = st.session_state.get("user_image", "https://www.w3schools.com/howto/img_avatar.png")
            if user_image and is_valid_image_url(user_image):
                st.image(user_image)
            else:
                show_dismissible_alert(
                    "avatar_warning",
                    "⚠️ Invalid avatar URL.<br>Showing default image.<br>Image Ref: <a href='https://unsplash.com/' target='_blank'>https://www.unsplash.com/",
                    alert_type="warning"
                )
                st.image("https://www.w3schools.com/howto/img_avatar.png")

        st.markdown("---")

        with st.expander("🌱 ESG Report Analysis", expanded=False):
            if st.button("📄 ESG Analysis"):
                chat(prompt = "esg analysis", chat_container = chat_container, write = False)
            if st.button("📄 Show Content"):
                chat(prompt = "show content", chat_container = chat_container, write = False)
            if st.button("📊 Show Word Cloud"):
                st.session_state["show_wordcloud_trigger"] = True
                st.session_state["show_aggregated"] = True
            if st.button("✨ Optimize ESG Report"):
                chat(prompt="optimize esg report", chat_container=chat_container, write=False)
                result = optimize_esg_report(compare=True)
                st.session_state.setdefault("messages", [])
                with chat_container:
                    st.markdown(result, unsafe_allow_html=True)

        with st.expander("📦 Vector Semantics - Word2vec", expanded=False):
            if st.button("🧭 Vector space - 2D View"):
                clear_vector_session_state()
                st.session_state["vector_task_function"] = view_2d.run
            if st.button("🧭 Vector space - 3D View"):
                clear_vector_session_state()
                st.session_state["vector_task_function"] = view_3d.run
            if st.button("🧭 Cbow / Skip Gram"):
                clear_vector_session_state()
                st.session_state["vector_task_function"] = cbow_skipgram.run

        st.markdown("---")
        selected_lang = st.selectbox("🌐 Language", ["English", "繁體中文"], index=0)
        st.session_state['lang_setting'] = selected_lang
        render_profile_section()

def render_vector_task_section():
    if "vector_task_function" not in st.session_state:
        return

    st.markdown("## 🧠 Provide your own sentences for Word2Vec")
    st.session_state.setdefault("user_input_text", "")
    st.session_state.setdefault("input_sentences", [])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔖 Load Example Sentences"):
            example_text = load_example_from_json("db/examples/word2vec_sentence_examples.json", "vector semantic example")
            st.session_state["user_input_text"] = example_text

    user_input_text = st.text_area(
        label="Enter sentences (one per line):",
        value=st.session_state["user_input_text"],
        height=300,
        placeholder="Type one sentence per line..."
    )
    st.session_state["user_input_text"] = user_input_text

    if st.session_state.get("vector_task_function") == cbow_skipgram.run:
        with st.container():
            st.info("ℹ️ You can manually input sentences, or leave empty to use the default Brown corpus.")

    col3, col4 = st.columns(2)
    with col3:
        if st.button("🚀 Run Vector Task"):
            if user_input_text.strip():
                input_sentences = [line.strip() for line in user_input_text.splitlines() if line.strip()]
                st.session_state["input_sentences"] = input_sentences
                st.session_state["input_sentences_source"] = "manual"
            elif st.session_state.get("vector_task_function") == cbow_skipgram.run:
                # Special case: cbow_skipgram allows no input
                st.session_state["input_sentences"] = []
                st.session_state["input_sentences_source"] = "manual"
            else:
                st.warning("⚠️ Please enter some sentences before running the vector task.")

    with col4:
        if st.button("🚀 Run Vector Task with loaded PDF"):
            if "pdf_text" in st.session_state and st.session_state["pdf_text"]:
                st.session_state["user_input_text"] = "" # clear manual input
                input_sentences = get_pdf_context(page="all")
                st.session_state["input_sentences"] = input_sentences
                st.session_state["input_sentences_source"] = "pdf"
            else:
                st.warning("⚠️ No PDF loaded. Please upload a PDF first.")

    # --- 核心 --- 執行 vector function
    if st.session_state.get("input_sentences") is not None:
        if len(st.session_state["input_sentences"]) > 0 or st.session_state["vector_task_function"] == cbow_skipgram.run:
            st.session_state["vector_task_function"](
                sentences=st.session_state["input_sentences"],
                source=st.session_state.get("input_sentences_source", "manual")
            )

    st.markdown("---")

def clear_vector_session_state():
    """清除跟 Vector 任務有關的所有 session_state 變數"""
    keys_to_clear = [
        "input_sentences",
        "user_input_text",
        "selected_indices_3d",
        "sentence_picker",
        "trigger_plot_3d"
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)

def main():
    st.set_page_config(
        page_title='K-Assistant - The Residemy Agent',
        layout='wide',
        initial_sidebar_state='auto',
        menu_items={
            'Get Help': 'https://streamlit.io/',
            'Report a bug': 'https://github.com/',
            'About': 'About your application: **https://github.com/brian0714/textmining-chatbot/blob/development/README.md**'
        },
        page_icon="img/favicon.ico"
    )

    init_db()

    profile = get_user_profile()
    st.session_state.setdefault("user_name", profile.get("user_name", "Brian") if profile else "Brian")
    st.session_state.setdefault("user_image", profile.get("user_image", "https://www.w3schools.com/howto/img_avatar.png"))

    st.title(f"💬 {st.session_state['user_name']}'s Chatbot")
    render_pdf_upload_section()

    chat_container = render_chat_container()
    render_sidebar(chat_container)
    render_chat_section(chat_container)

    render_vector_task_section()
    if "pending_vector_task" in st.session_state:
        st.session_state["vector_task_function"] = st.session_state["pending_vector_task"]
        del st.session_state["pending_vector_task"]
        st.rerun()

    # 判斷是否要顯示 Word Cloud
    if st.session_state.get("show_wordcloud_trigger", False):
        pdf_texts = st.session_state.get("pdf_texts_for_cross_comparison", None)
        industry = st.session_state.get("industry", "Unknown Industry")
        esg_charts(pdf_texts=pdf_texts, industry=industry)
        show_wordcloud_controls()
        # st.session_state["show_wordcloud_trigger"] = False  # 清除觸發

    if st.session_state.get("show_esg_table", False):
        show_esg_report_table()
if __name__ == "__main__":
    main()
