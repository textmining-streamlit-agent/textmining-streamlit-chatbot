import streamlit as st
import time
import autogen
from autogen import ConversableAgent, LLMConfig
from autogen import AssistantAgent, UserProxyAgent
from autogen.code_utils import content_str # for OpenAI
import ast
import traceback
import re
from tools.esg_tool_register import register_one_agent_all_tools # register_all_tools
from google.genai.errors import ServerError


GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", None)

if GEMINI_API_KEY is None:
    raise RuntimeError("GEMINI_API_KEY not found in secrets.toml")

def get_agent_persona():
    pdf_content = st.session_state.get("pdf_text", "")
    lang_setting = st.session_state.get("lang_setting", "English")

    if pdf_content:
        tool_usage_guide = """
        The user has uploaded a PDF report. You may use the following commands to help them explore it:

        - show_pdf_content → Display the full PDF text from the uploaded ESG report.
        - show_pdf_page_content(n) → Show content from a specific page in the uploaded ESG report `n` (e.g., show_pdf_page_content(2)).
        - esg_analysis → Extract ESG insights from the PDF.
        """
    else:
        tool_usage_guide = "User didnt upload ESG report; please gently remind users to upload one ESG report."

    agent_persona = f"""
        You are an ESG analysis assistant. Your role is to help users understand, interpret, and analyze ESG (Environmental, Social, Governance) reports and related topics.

        Before answering, first check if the user’s message is meaningfully related to ESG concepts, sustainability reporting, or corporate responsibility.

        If the user’s message is not relevant to ESG or sustainability, **do not** answer the question directly. Instead, gently remind the user to keep the conversation focused on ESG-related topics.

        {tool_usage_guide}

        Please generate your response below:
        - If the user message clearly maps to a tool (e.g., showing PDF content or performing ESG analysis), use that tool directly.
        - Do not ask the user to choose.

        1. Fallback & Termination
        – On successful completion or when ending or after using the `tool`, return '##ALL DONE##'.
        - Return '##ALL DONE##' and respond accordingly when:
            • The task is completed.
            • The input is empty.
            • An error occurs.
            • The request is repeated.
            • Additional confirmation is required from the user.
        2. Please output in {lang_setting}
        """

    return agent_persona

gemini_config = LLMConfig(
    api_type = "google",
    model="gemini-2.0-flash-lite", # The specific model
    api_key=GEMINI_API_KEY, # Authentication
)

gemini_agent = ConversableAgent(
    name="Gemini",
    llm_config=gemini_config,
    # max_consecutive_auto_reply=1, # user cannot interact with terminal if set max_consecutive_auto_reply
    system_message=get_agent_persona()
)
# register_all_tools(gemini_agent)

# assistant = AssistantAgent(
#     "assistant",
#     llm_config=gemini_config,
#     max_consecutive_auto_reply=3
# )

def is_terminated_custom(x):
    try:
        print("🔍 Received message x:", x)  # << 加在這裡 debug 看整個 message 格式

        # tool call 還沒執行完，不能終止
        if "tool_calls" in x:
            return False

        content = x.get("content", "")
        if isinstance(content, dict):
            content = content.get("output", "")
        elif isinstance(content, list):
            content = " ".join([
                str(c.get("content", "")) if isinstance(c, dict) else str(c)
                for c in content
            ])
        print("🧪 Parsed content:", content)  # << 看實際抓到的內容

        return "##ALL DONE##" in content
    except Exception as e:
        print("❌ Error in termination check:", e)
        return False

user_proxy = UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER", # "TERMINATE"
    code_execution_config=False,
    # is_termination_msg=lambda x: content_str(x.get("content")).find("##ALL DONE##") >= 0, # for OpenAI
    is_termination_msg=is_terminated_custom
)
register_one_agent_all_tools(agent=gemini_agent, proxy=user_proxy)

# Build the prompt for direct calling of Gemini API
def build_prompt(prompt: str, restrict: bool, lang_setting: str) -> str:
    if restrict:
        return f"""
        You are an ESG analysis assistant. Your role is to help users understand, interpret, and analyze ESG (Environmental, Social, Governance) reports and related topics.

        Before answering, first check if the user’s message is meaningfully related to ESG concepts, sustainability reporting, or corporate responsibility.

        If the user’s message is not relevant to ESG or sustainability, **do not** answer the question directly. Instead, gently remind the user to keep the conversation focused on ESG-related topics.

        Here is the user message:
        \"\"\"{prompt}\"\"\"

        Please output in {lang_setting}
        Please generate your response below:
        """
    else:
        return prompt

def generate_gemini_reply(agent, message, max_retries=3):
    for attempt in range(max_retries):
        try:
            reply = agent.generate_reply(messages=[message])
            if not reply or "content" not in reply:
                return "⚠️ Gemini did not return a valid reply."
            return content_str(reply["content"])
        except ServerError as e:
            is_retryable = "unavailable" in str(e).lower() or "overloaded" in str(e).lower()
            if is_retryable and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                st.warning(f"Gemini is currently unavailable. Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            else:
                tb = traceback.format_exc()
                return f"❌ Gemini ServerError (503): {e}\n\n{tb}"
        except Exception as e:
            tb = traceback.format_exc()
            return f"❌ Gemini error: {type(e).__name__} - {e}\n\n{tb}"

def chat_with_gemini(prompt: str, restrict=True) -> str:
    lang_setting = st.session_state.get("lang_setting", "")
    prompt_text = build_prompt(prompt, restrict, lang_setting)

    message = {"role": "user", "content": prompt_text}

    temp_gemini_agent = ConversableAgent(
        name="Gemini",
        llm_config=gemini_config
    )

    return generate_gemini_reply(temp_gemini_agent, message)

def summarize_messages(messages: list) -> str:
    """
    使用 Gemini 對 messages 進行摘要（最近 10 則以外）
    """

    history_text = ""
    for msg in messages:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"

    prompt = f"""
    You are a memory summarizer.
    Summarize the following conversation between a user and an assistant.
    Focus on preserving key ideas and context, not the exact wording.

    ### Conversation:
    {history_text}

    ### Summary:
    """
    response = chat_with_gemini(prompt, restrict = False)

    return response

# Extract chat history or tool response from Gemini Assitant output
def extract_final_response(chat_history, tag: str = "##ALL DONE##") -> str:
    """
    從 AutoGen chat history 中提取含有指定終止標記的回應，或在偵測到 tool call 時合併其後兩則回應。

    Args:
        chat_history (List[Dict]): AutoGen 對話歷史
        tag (str): 終止標記字串（預設為 '##ALL DONE##'）

    Returns:
        str: 移除終止標記後的內容，或合併工具後兩句話的內容。如無則回傳 fallback。
    """

    chat_history = chat_history[1:]  # Skip user prompt

    def extract_output(msg):
        """從一則訊息中提取 output 字串"""
        if isinstance(msg, dict):
            content = msg.get("content", "")
            if isinstance(content, dict):
                return content.get("output", "")
            elif isinstance(content, str):
                # 嘗試解析字串為 dict
                try:
                    parsed = ast.literal_eval(content)
                    if isinstance(parsed, dict) and "output" in parsed:
                        return parsed["output"]
                except:
                    pass
                return content  # fallback: 原始字串
        elif isinstance(msg, str):
            return msg
        return ""

    # 優先處理 tool_calls + 接續的兩則訊息合併
    for i, msg in enumerate(chat_history):
        if "tool_calls" in msg:
            msg1 = chat_history[i + 1] if i + 1 < len(chat_history) else {}
            msg2 = chat_history[i + 2] if i + 2 < len(chat_history) else {}
            text1 = extract_output(msg1).strip()
            text2 = extract_output(msg2).strip()
            combined = f"{text1}\n\n{text2}".strip()
            if combined:
                return combined

    # 處理含 tag 的純文字訊息
    for i, msg in enumerate(chat_history):
        # 如果訊息中有 tool_calls，表示 tool_calls 失敗
        if "tool_calls" in msg:
            continue

        if i != 0:
            # 如果不是第一則訊息，檢查前一則是否為空
            prev_msg = chat_history[i - 1]
            prev_content = prev_msg.get("content", "")
            if isinstance(prev_content, str) and not prev_content.strip():
                continue

        content = msg.get("content", "")
        if isinstance(content, str) and tag in content:
            return content.replace(tag, "").strip()
        if isinstance(content, dict):
            output = content.get("output", "")
            if tag in output:
                return output.replace(tag, "").strip()

    # fallback 最後一則有效內容（前一則非空 or 第一則）
    for i in range(len(chat_history) - 1, -1, -1):
        curr_msg = chat_history[i]
        curr_content = curr_msg.get("content", "")

        # ✅ 如果當前訊息沒內容，跳過
        if not isinstance(curr_content, (str, dict)) or not str(curr_content).strip():
            continue

        # ✅ 如果是第一則訊息，不用管前一則，直接回傳
        if i == 0:
            if isinstance(curr_content, dict) and "output" in curr_content:
                return curr_content["output"]
            return str(curr_content).strip()

        # ✅ 檢查前一則內容
        prev_msg = chat_history[i - 1]
        prev_content = prev_msg.get("content", "")

        # 🚫 只有「前一則是空 & 是 user_proxy」時才 continue
        if (
            isinstance(prev_content, str) and not prev_content.strip()
            and prev_msg.get("role") == "assistant" and prev_msg.get("name") == "user_proxy"
        ):
            continue  # ❌ 其他空訊息也不採用，往前找

        # ✅ 否則，當前訊息可被接受為 fallback
        if isinstance(curr_content, dict) and "output" in curr_content:
            return curr_content["output"]
        return str(curr_content).strip()

    # 若全部都不符合，回傳預設訊息
    return "⚠️ No valid response found."

# Use agent (gemini) with registered tools
def chat_with_gemini_agent(prompt: str, restrict = True) -> str:
    pdf_content = st.session_state.get("pdf_text", "")
    lang_setting = st.session_state.get("lang_setting", "English")

    message_history = st.session_state.get("messages", [])
    # 構建歷史對話文字區段
    # history_text = ""
    # for msg in message_history[-10:]:  # 只取最近 10 則，避免太長
    #     role = "User" if msg["role"] == "user" else "Assistant"
    #     history_text += f"{role}: {msg['content']}\n"
    history_text = summarize_messages(messages=message_history)

    if pdf_content:
        tool_usage_guide = """
        The user has already uploaded a ESG report, please use the following functions considering user's needs:

        - show_pdf_content → Display the full PDF text from the uploaded ESG report.
        - show_pdf_page_content(n) → Show content from a specific page in the uploaded ESG report `n` (e.g., show_pdf_page_content(2)).
        - esg_analysis → To summarize, do ESG report analysis and extract ESG insights from the ESG report (PDF).
        - cross_comparison_analysis(industry, years) → Perform ESG cross-comparison analysis for a given industry over specified years (e.g., cross_comparison_analysis("Food", [2020, 2021, 2022].)  If industry is not specified, takes `None` as an argument of `industry`. If years are not specified, takes `None` as an argument of `year`.)
        """
        # If the user asks about the uploaded ESG report (or clearly refers to its contents), you may use the following functions:
        # - clustering analysis → Run clustering analysis on the PDF.
    else:
        tool_usage_guide = """
        If the user is clearly asking for an analysis of an uploaded ESG report, and no report is currently available, you may gently remind them to upload one.
        However, if the user is asking general ESG-related questions (e.g., "What is ESG?"), respond directly without requiring a report.
        """

    if restrict:
        prompt_template = f"""
        You are an ESG assistant. You may help the user by answering general ESG-related questions directly.

        {tool_usage_guide}

        Here is the prior conversation:
        {history_text}

        Here is the user message:
        \"\"\"{prompt}\"\"\"

        Please generate your response below:
        - If the user message clearly maps to a tool (e.g., showing PDF content or ESG analysis), use that tool directly.
        - Do not ask the user to choose.
        - After using the `tool`, return '##ALL DONE##'

        1. Fallback & Termination
        – On successful completion or when ending, return '##ALL DONE##'.
        - Return '##ALL DONE##' and respond accordingly when:
            • The task is completed.
            • The input is empty.
            • An error occurs.
            • The request is repeated.
            • Additional confirmation is required from the user.
        2. Please output in {lang_setting}
        """
    else:
        prompt_template = prompt

    try:
        result = user_proxy.initiate_chat(
            recipient=gemini_agent,
            message=prompt_template,
            max_turns=2 # User cannot interact with terminal (user_proxy (to Gemini) will be empty in further turns) if set max_turns
        )

        chat_history = result.chat_history
        print(chat_history)
        response = extract_final_response(chat_history)
        if "##ALL DONE##" in response:
            response = response.replace("##ALL DONE##", "").rstrip().rstrip("\n")
        return response

    except Exception as e:
        tb = traceback.format_exc()
        return f"⚠️ Gemini error: {type(e).__name__} - {e}\n\n{tb}"

def extract_json_from_gemini_output(text: str) -> str:
    """從 Gemini 回應中清理並提取 JSON 字串"""
    text = re.sub(r"```json|```", "", text, flags=re.IGNORECASE).strip()
    json_start = text.find("{")
    json_end = text.rfind("}") + 1
    return text[json_start:json_end].strip()
