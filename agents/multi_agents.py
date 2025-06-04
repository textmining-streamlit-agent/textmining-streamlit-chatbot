import streamlit as st
import sys
import os
import re
import ast
from autogen import (
    ConversableAgent, LLMConfig, UserProxyAgent,
    GroupChat, GroupChatManager,
    register_function
)
from tools.esg_tools import (
    show_pdf_content,
    get_pdf_page_content,
    esg_analysis,
    optimize_esg_report,
    cross_comparison_analysis,
    generate_esg_template_analysis
)

# Add project root to import custom modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load secrets
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)
if OPENAI_API_KEY is None:
    # raise RuntimeError("OPENAI_API_KEY not found in secrets.toml")
    st.warning("OPENAI_API_KEY not found in secrets.toml. Please set it up to use the LLM features such as `advanced mode`.")

# LLM Configuration
llm_config_openai = LLMConfig(
    api_type="openai",
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY
)

# --------------------------------------------
# ✅ Helper Functions
# --------------------------------------------

def content_str(content):
    if isinstance(content, str):
        return content
    elif isinstance(content, dict) and "content" in content:
        return str(content["content"])
    return str(content)

def extract_output(msg):
    content = msg.get("content", "") if isinstance(msg, dict) else msg
    try:
        if isinstance(content, str):
            parsed = ast.literal_eval(content)
            if isinstance(parsed, dict) and "output" in parsed:
                return parsed["output"]
            return parsed
    except Exception:
        pass
    return content

def format_tool_output(raw) -> str:
    if isinstance(raw, list):
        return "\n".join(
            f"**Page {item['page']}**\n\n{item['content'].strip()}" for item in raw if item.get("content", "").strip()
        )
    if isinstance(raw, str) and raw.startswith("{'output':"):
        raw = re.sub(r"^\{'output':\\s*", "", raw).rstrip("}").strip("'").strip('"')
        raw = raw.replace("\\n", "\n").replace("\\t", "\t")
    return raw.strip()

# --------------------------------------------
# ✅ Language Setting
# --------------------------------------------
lang_setting = st.session_state.get("lang_setting", "English")

# --------------------------------------------
# ✅ Agent Personas
# --------------------------------------------

teacher_persona = f"""
You are an ESG professor. Responsibilities:
1. Instruct the student to analyze reports.
2. Call functions like `esg_analysis()` or `cross_comparison_analysis()` if needed.
Respond in {lang_setting}.
Say 'ALL DONE' when everything is complete.
"""

content_agent_persona = f"You handle document-related tasks such as `show_pdf_content` and `get_pdf_page_content`. Please respond in {lang_setting}."
analysis_agent_persona = f"You perform ESG report content analysis using `esg_analysis` and `optimize_esg_report`. Please respond in {lang_setting}."
comparison_agent_persona = f"You do cross-year and cross-industry ESG comparisons using `cross_comparison_analysis`. Please respond in {lang_setting}."

# --------------------------------------------
# ✅ Create Agents
# --------------------------------------------

content_agent = ConversableAgent(
    name="Content_Agent",
    llm_config=llm_config_openai,
    system_message=content_agent_persona
)

analysis_agent = ConversableAgent(
    name="Analysis_Agent",
    llm_config=llm_config_openai,
    system_message=analysis_agent_persona
)

comparison_agent = ConversableAgent(
    name="Comparison_Agent",
    llm_config=llm_config_openai,
    system_message=comparison_agent_persona
)

teacher_agent = ConversableAgent(
    name="Teacher_Agent",
    llm_config=llm_config_openai,
    system_message=teacher_persona,
    is_termination_msg=lambda x: "ALL DONE" in content_str(x.get("content", "")),
    human_input_mode="NEVER"
)

user_proxy = UserProxyAgent(
    name="User_Proxy",
    human_input_mode="NEVER",
    code_execution_config={"use_docker": False},
    is_termination_msg=lambda x: "ALL DONE" in content_str(x.get("content", "")),
)

# Register functions to appropriate executors
def register_all_tools():
    register_function(
        show_pdf_content,
        caller=teacher_agent,
        executor=content_agent,
        description="Display the full uploaded PDF text.",
        name="show_pdf_content"
    )
    register_function(
        get_pdf_page_content,
        caller=teacher_agent,
        executor=content_agent,
        description="Display the content of a specific PDF page. Takes 'page' as an integer argument.",
        name="get_pdf_page_content"
    )
    register_function(
        esg_analysis,
        caller=teacher_agent,
        executor=analysis_agent,
        description="Extract ESG-related insights from the uploaded PDF.",
        name="esg_analysis"
    )
    register_function(
        optimize_esg_report,
        caller=teacher_agent,
        executor=analysis_agent,
        description="Optimize the ESG report based on the uploaded PDF content and industry benchmarks.",
        name="optimize_esg_report"
    )
    register_function(
        cross_comparison_analysis,
        caller=teacher_agent,
        executor=comparison_agent,
        description="Perform ESG cross-comparison analysis for a given industry over specified years. If industry is not specified, takes `None` as an argument. If years are not specified, takes `None` as an argument.",
        name="cross_comparison_analysis"
    )
    register_function(
        generate_esg_template_analysis,
        caller=teacher_agent,
        executor=analysis_agent,
        description="Generate ESG template analysis based on the selected template format and industry.",
        name="generate_esg_template_analysis"
    )
register_all_tools()

# Register reply behavior for tool tracing (Use session-state held placeholder for tool messages)
if "tool_info_placeholder" not in st.session_state:
    st.session_state["tool_info_placeholder"] = st.empty()

# Register reply behavior for tool tracing
def tool_reply_trace(recipient, messages, sender, config):
    st.session_state["tool_info_placeholder"].info(f"🔧 **{recipient.name} is using a tool...**")
    return False, None

for agent in [teacher_agent, content_agent, analysis_agent, comparison_agent]:
    agent.register_reply([ConversableAgent, None], reply_func=tool_reply_trace)

# GroupChat
all_agents = [user_proxy, teacher_agent, content_agent, analysis_agent, comparison_agent]
group_chat = GroupChat(agents=all_agents, messages=[], max_round=5)
manager = GroupChatManager(groupchat=group_chat, llm_config=llm_config_openai)

# --------------------------------------------
# ✅ Main Entry Point
# --------------------------------------------

def run_multi_agent_chat(prompt: str) -> str:
    user_proxy.initiate_chat(manager, message=f"Please help me analyze the following ESG report: {prompt}")

    tool_output = ""
    agent_summary = ""

    for msg in reversed(manager.groupchat.messages):
        if not tool_output and msg.get("role") == "function":
            tool_output = extract_output(msg)
        if not agent_summary and msg.get("name", "").endswith("_Agent"):
            agent_summary = extract_output(msg)
        if tool_output and agent_summary:
            break

    # Clear the placeholder after processing
    st.session_state["tool_info_placeholder"].empty()

    if not tool_output and not agent_summary:
        return "[⚠️ No agent output returned]"

    if isinstance(tool_output, (dict, list)):
        tool_output = str(tool_output)
    if isinstance(agent_summary, (dict, list)):
        agent_summary = str(agent_summary)

    formatted_tool_output = format_tool_output(tool_output)
    return (
        # f"### Tool Output\n{formatted_tool_output}\n\n"
        f"### Agent Summary\n{agent_summary.strip()}"
    )
