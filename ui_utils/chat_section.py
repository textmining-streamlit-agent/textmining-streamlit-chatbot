import streamlit as st
import time
from response_generator import generate_response

# 清除跟 run 任務有關的所有 session_state 變數
def clear_run_session_state(exclude_keys=None):
    if exclude_keys is None:
        exclude_keys = []

    keys_to_clear = [
        "template_task_function",
        "show_wordcloud_trigger",
        "show_esg_table",
        "show_cleaned_pdf_flag",

        # vector task specific
        "input_sentences",
        "user_input_text",
        "selected_indices_3d",
        "sentence_picker",
        "trigger_plot_3d"
    ]

    for key in keys_to_clear:
        if key not in exclude_keys:
            st.session_state.pop(key, None)

    st.rerun()

# 逐字 streaming 輸出
def stream_data(stream_str):
    if stream_str is None:
        yield "No prompt has been provided."
        return
    for word in stream_str.split(" "):
        yield word + " "
        time.sleep(0.1)

# 建立聊天區塊 container，主程式只需呼叫這個
def render_chat_container():
    st.session_state["chat_mode"] = "Analyze Mode" # 預設為分析模式
    return st.container(border=True)

# 單次聊天行為（加入 messages 並立即顯示）
def chat(prompt: str, chat_container, write=True):
    if write:
        st_c_chat = chat_container

        chat_user_image = st.session_state.get(
            "user_image", "https://www.w3schools.com/howto/img_avatar.png"
        )

        st_c_chat.chat_message("user", avatar=chat_user_image).write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        response = generate_response(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st_c_chat.chat_message("assistant").write_stream(stream_data(response))
    else:
        chat_user_image = st.session_state.get(
            "user_image", "https://www.w3schools.com/howto/img_avatar.png"
        )
        st.session_state.messages.append({"role": "user", "content": prompt})
        response = generate_response(prompt)
        st.session_state.messages.append({"role": "assistant", "content": response})

    #  清除跟 run 任務有關的所有 session_state 變數
    # clear_run_session_state()

# 主聊天渲染 + 處理 chat_input
def render_chat_section(st_c_chat):
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st_c_chat.chat_message(
                msg["role"], avatar=st.session_state.get("user_image", "")
            ).markdown(msg["content"])
        elif msg["role"] == "assistant":
            st_c_chat.chat_message(msg["role"]).markdown(msg["content"])
        else:
            image_tmp = msg.get("image")
            if image_tmp:
                st_c_chat.chat_message(msg["role"], avatar=image_tmp).markdown(msg["content"])
            else:
                st_c_chat.chat_message(msg["role"]).markdown(msg["content"])

    # 渲染 chat mode selector 區塊
    with st.container():
        st.markdown("---")
        col1, col2 = st.columns([1, 4])
        with col1:
            with st.expander("🤖 Select Chat Mode", expanded=False):
                chat_mode = st.selectbox(
                    label="Choose the assistant mode:",
                    options=["Chat Freely", "Analyze Mode", "Advanced Mode"],
                    index=1, # 預設為 Analyze Mode
                    key="chat_mode_selector"
                )
                st.session_state["chat_mode"] = chat_mode

        # 輸入框，使用對應的 container 呼叫 chat
        with col2:
            if prompt := st.chat_input(placeholder="Ask me about the ESG report", key="chat_bot"):
                # chat(prompt, chat_container=st_c_chat)
                display_chat = True
            else:
                display_chat = False

        if display_chat:
            chat(prompt, chat_container=st_c_chat)
