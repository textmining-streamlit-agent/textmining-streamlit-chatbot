# import sys
# import os
# import re
# import ast
# from autogen import (
#     ConversableAgent, LLMConfig, UserProxyAgent,
#     GroupChat, GroupChatManager
# )
# from dotenv import load_dotenv
# from tools.esg_tool_register import register_all_tools

# # Add project root to import custom modules
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# # Load environment variables
# load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# # LLM Configuration
# llm_config_openai = LLMConfig(
#     api_type="openai",
#     model="gpt-4o-mini",
#     api_key=OPENAI_API_KEY
# )

# # --------------------------------------------
# # ✅ Helper Functions
# # --------------------------------------------

# def content_str(content):
#     """Normalize the content for termination checks"""
#     if isinstance(content, str):
#         return content
#     elif isinstance(content, dict) and "content" in content:
#         return str(content["content"])
#     return str(content)

# def extract_output(msg):
#     """從一則訊息中提取 output 字串"""
#     if isinstance(msg, dict):
#         content = msg.get("content", "")
#         if isinstance(content, dict):
#             return content.get("output", "")
#         elif isinstance(content, str):
#             try:
#                 parsed = ast.literal_eval(content)
#                 if isinstance(parsed, dict) and "output" in parsed:
#                     return parsed["output"]
#             except:
#                 pass
#             return content
#     elif isinstance(msg, str):
#         return msg
#     return ""

# def format_tool_output(raw: str) -> str:
#     """Format ESG tool output for better readability"""
#     if raw.startswith("{'output':"):
#         raw = re.sub(r"^\{'output':\s*", "", raw).rstrip("}").strip("'").strip('"')
#     raw = raw.replace("\\n", "\n").replace("\\t", "\t")
#     raw = re.sub(r"\n[*•\-] ", "\n- ", raw)
#     raw = re.sub(r"#+\s*(Environmental|Social|Governance).*", r"\n### \1", raw)
#     raw = raw.replace("##ALL DONE##", "").strip()
#     return raw

# # --------------------------------------------
# # ✅ Agent Personas
# # --------------------------------------------

# student_persona = """
# You are a student assistant trained to extract, analyze, and summarize ESG reports.
# Use the available tools upon instruction.
# """

# teacher_persona = """
# You are an ESG professor. Responsibilities:
# 1. Instruct the student to analyze reports.
# 2. Call functions like `esg_analysis()` or `show_pdf_content()` if needed.
# Say 'ALL DONE' when everything is complete.
# """

# tech_persona = """
# You are a technical advisor for ESG analytics systems. Assist with tool functionality or technical questions.
# """

# general_persona = """
# You are a general business consultant offering advice on ESG-related decisions from a management point of view.
# """

# # --------------------------------------------
# # ✅ Create Agents
# # --------------------------------------------

# student_agent = ConversableAgent(
#     name="Student_Agent",
#     llm_config=llm_config_openai,
#     system_message=student_persona,
# )

# teacher_agent = ConversableAgent(
#     name="Teacher_Agent",
#     llm_config=llm_config_openai,
#     system_message=teacher_persona,
#     is_termination_msg=lambda x: "ALL DONE" in content_str(x.get("content", "")),
#     human_input_mode="NEVER"
# )

# tech_agent = ConversableAgent(
#     name="Tech_Agent",
#     llm_config=llm_config_openai,
#     system_message=tech_persona
# )

# general_agent = ConversableAgent(
#     name="General_Agent",
#     llm_config=llm_config_openai,
#     system_message=general_persona
# )

# user_proxy = UserProxyAgent(
#     name="User_Proxy",
#     human_input_mode="NEVER",
#     code_execution_config={"use_docker": False},
#     is_termination_msg=lambda x: "ALL DONE" in content_str(x.get("content", "")),
# )

# # Register tools
# register_all_tools(teacher_agent, student_agent)

# # --------------------------------------------
# # ✅ GroupChat Setup
# # --------------------------------------------

# all_agents = [user_proxy, teacher_agent, student_agent, tech_agent, general_agent]
# group_chat = GroupChat(
#     agents=all_agents,
#     messages=[],
#     max_round=12
# )

# manager = GroupChatManager(
#     groupchat=group_chat,
#     llm_config=llm_config_openai
# )

# # --------------------------------------------
# # ✅ Main Entry Point
# # --------------------------------------------

# def run_multi_agent_chat(prompt: str) -> str:
#     """Entry function to run the ESG analysis conversation"""

#     # Start the conversation
#     user_proxy.initiate_chat(manager, message=f"Please help me analyze the following ESG report: {prompt}")

#     # Extract tool output
#     tool_output = ""
#     student_summary = ""

#     for msg in reversed(manager.groupchat.messages):
#         if not tool_output and msg.get("role") == "function":
#             tool_output = extract_output(msg)

#         if not student_summary and msg.get("name") == "Student_Agent":
#             student_summary = extract_output(msg)

#         if tool_output and student_summary:
#             break

#     # Check fallback
#     if not tool_output and not student_summary:
#         return "[⚠️ No agent output returned]"

#     # Format outputs
#     formatted_tool_output = format_tool_output(tool_output)

#     return (
#         f"### ☁️ Word Cloud / ESG Tool Output\n{formatted_tool_output}\n\n"
#         f"---\n\n"
#     )
# import sys
# import os
# import re
# import ast
# from autogen import (
#     ConversableAgent, LLMConfig, UserProxyAgent,
#     GroupChat, GroupChatManager
# )
# from dotenv import load_dotenv
# from tools.esg_tool_register import register_all_tools

# # Add project root to import custom modules
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# # Load environment variables
# load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# # LLM Configuration
# llm_config_openai = LLMConfig(
#     api_type="openai",
#     model="gpt-4o-mini",
#     api_key=OPENAI_API_KEY
# )

# # --------------------------------------------
# # ✅ Helper Functions
# # --------------------------------------------

# def content_str(content):
#     """Normalize the content for termination checks"""
#     if isinstance(content, str):
#         return content
#     elif isinstance(content, dict) and "content" in content:
#         return str(content["content"])
#     return str(content)

# def extract_output(msg):
#     """Extract the 'output' string from a message"""
#     if isinstance(msg, dict):
#         content = msg.get("content", "")
#         if isinstance(content, dict):
#             return content.get("output", "")
#         elif isinstance(content, str):
#             try:
#                 parsed = ast.literal_eval(content)
#                 if isinstance(parsed, dict) and "output" in parsed:
#                     return parsed["output"]
#             except:
#                 pass
#             return content
#     elif isinstance(msg, str):
#         return msg
#     return ""

# def format_tool_output(raw: str) -> str:
#     """Format ESG tool output for better readability"""
#     if raw.startswith("{'output':"):
#         raw = re.sub(r"^\{'output':\s*", "", raw).rstrip("}").strip("'").strip('"')
#     raw = raw.replace("\\n", "\n").replace("\\t", "\t")
#     raw = re.sub(r"\n[*•\-] ", "\n- ", raw)
#     raw = re.sub(r"#+\s*(Environmental|Social|Governance).*", r"\n### \1", raw)
#     raw = raw.replace("##ALL DONE##", "").strip()
#     return raw

# # --------------------------------------------
# # ✅ Agent Personas
# # --------------------------------------------

# student_persona = """
# You are a student assistant trained to extract, analyze, and summarize ESG reports.
# Use the available tools upon instruction.
# """

# teacher_persona = """
# You are an ESG professor. Responsibilities:
# 1. Instruct the student to analyze reports.
# 2. Call functions like `esg_analysis()` or `show_pdf_content()` if needed.
# Say 'ALL DONE' when everything is complete.
# """

# tech_persona = """
# You are a technical advisor for ESG analytics systems. Assist with tool functionality or technical questions.
# """

# general_persona = """
# You are a general business consultant offering advice on ESG-related decisions from a management point of view.
# """

# # --------------------------------------------
# # ✅ Create Agents
# # --------------------------------------------

# student_agent = ConversableAgent(
#     name="Student_Agent",
#     llm_config=llm_config_openai,
#     system_message=student_persona,
# )

# teacher_agent = ConversableAgent(
#     name="Teacher_Agent",
#     llm_config=llm_config_openai,
#     system_message=teacher_persona,
#     is_termination_msg=lambda x: "ALL DONE" in content_str(x.get("content", "")),
#     human_input_mode="NEVER"
# )

# tech_agent = ConversableAgent(
#     name="Tech_Agent",
#     llm_config=llm_config_openai,
#     system_message=tech_persona
# )

# general_agent = ConversableAgent(
#     name="General_Agent",
#     llm_config=llm_config_openai,
#     system_message=general_persona
# )

# user_proxy = UserProxyAgent(
#     name="User_Proxy",
#     human_input_mode="NEVER",
#     code_execution_config={"use_docker": False},
#     is_termination_msg=lambda x: "ALL DONE" in content_str(x.get("content", "")),
# )

# # Register tools
# register_all_tools(teacher_agent, student_agent)

# # --------------------------------------------
# # ✅ GroupChat Setup
# # --------------------------------------------

# all_agents = [user_proxy, teacher_agent, student_agent, tech_agent, general_agent]
# group_chat = GroupChat(
#     agents=all_agents,
#     messages=[],
#     max_round=12
# )

# manager = GroupChatManager(
#     groupchat=group_chat,
#     llm_config=llm_config_openai
# )

# # --------------------------------------------
# # ✅ Main Entry Point
# # --------------------------------------------

# def run_multi_agent_chat(prompt: str) -> str:
#     """Entry function to run the ESG analysis conversation"""

#     # Start the conversation
#     user_proxy.initiate_chat(manager, message=f"Please help me analyze the following ESG report: {prompt}")

#     # Extract tool output and student summary
#     tool_output = ""
#     student_summary = ""

#     for msg in reversed(manager.groupchat.messages):
#         if not tool_output and msg.get("role") == "function":
#             tool_output = extract_output(msg)

#         if not student_summary and msg.get("name") == "Student_Agent":
#             student_summary = extract_output(msg)

#         if tool_output and student_summary:
#             break

#     # Check fallback
#     if not tool_output and not student_summary:
#         return "[⚠️ No agent output returned]"

#     # Format outputs
#     formatted_tool_output = format_tool_output(tool_output)

#     return (
#         f"### ☁️ Word Cloud / ESG Tool Output\n{formatted_tool_output}\n\n"
#         f"---\n\n"
#         f"### 🎓 Student Summary\n{student_summary.strip()}"
#     )
import streamlit as st
import sys
import os
import re
import ast
from autogen import (
    ConversableAgent, LLMConfig, UserProxyAgent,
    GroupChat, GroupChatManager
)
from dotenv import load_dotenv
from tools.esg_tool_register import register_all_tools

# Add project root to import custom modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables
# load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)

if OPENAI_API_KEY is None:
    raise RuntimeError("OPENAI_API_KEY not found in secrets.toml")

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
    """Normalize the content for termination checks"""
    if isinstance(content, str):
        return content
    elif isinstance(content, dict) and "content" in content:
        return str(content["content"])
    return str(content)

def extract_output(msg):
    """Extract the 'output' string from a message, even if it's not a string"""
    if isinstance(msg, dict):
        content = msg.get("content", "")
        if isinstance(content, dict) and "output" in content:
            out = content["output"]
        elif isinstance(content, str):
            try:
                parsed = ast.literal_eval(content)
                if isinstance(parsed, dict) and "output" in parsed:
                    out = parsed["output"]
                else:
                    out = parsed
            except Exception:
                out = content
        else:
            out = content
    elif isinstance(msg, str):
        out = msg
    else:
        out = str(msg)

    # ✅ Additional logic: parse again if it's a list/dict string
    try:
        return ast.literal_eval(out)
    except Exception:
        return out

def format_tool_output(raw) -> str:
    """Format ESG tool output including PDF page content"""
    if isinstance(raw, list):
        # parsed as [{'page': 1, 'content': "..."}]
        return "\n".join(
            f"**Page {item['page']}**\n\n{item['content'].strip()}" for item in raw if item.get("content", "").strip()
        )

    if isinstance(raw, str) and raw.startswith("{'output':"):
        raw = re.sub(r"^\{'output':\s*", "", raw).rstrip("}").strip("'").strip('"')
        raw = raw.replace("\\n", "\n").replace("\\t", "\t")

    return raw.strip()

# def format_tool_output(raw: str) -> str:
#     """Format ESG tool output for better readability"""
#     if raw.startswith("{'output':"):
#         raw = re.sub(r"^\{'output':\s*", "", raw).rstrip("}").strip("'").strip('"')
    
#     # Decode escape sequences
#     raw = raw.replace("\\n", "\n").replace("\\t", "\t")
    
#     # Remove empty tables with all "None"
#     raw = re.sub(r'Table:\n(?:.*None.*\n?)+', '', raw, flags=re.MULTILINE)

#     # Format bullets
#     raw = re.sub(r"\n[*•\-] ", "\n- ", raw)

#     # Add headers
#     raw = re.sub(r"#+\s*(Environmental|Social|Governance).*", r"\n### \1", raw)

#     # Clean up ending marker
#     raw = raw.replace("##ALL DONE##", "").strip()
#     return raw

# --------------------------------------------
# ✅ Agent Personas
# --------------------------------------------

student_persona = """
You are a student assistant trained to extract, analyze, and summarize ESG reports.
Use the available tools upon instruction.
"""

teacher_persona = """
You are an ESG professor. Responsibilities:
1. Instruct the student to analyze reports.
2. Call functions like `esg_analysis()` or `show_pdf_content()` if needed.
Say 'ALL DONE' when everything is complete.
"""

tech_persona = """
You are a technical advisor for ESG analytics systems. Assist with tool functionality or technical questions.
"""

general_persona = """
You are a general business consultant offering advice on ESG-related decisions from a management point of view.
"""

# --------------------------------------------
# ✅ Create Agents
# --------------------------------------------

student_agent = ConversableAgent(
    name="Student_Agent",
    llm_config=llm_config_openai,
    system_message=student_persona,
)

teacher_agent = ConversableAgent(
    name="Teacher_Agent",
    llm_config=llm_config_openai,
    system_message=teacher_persona,
    is_termination_msg=lambda x: "ALL DONE" in content_str(x.get("content", "")),
    human_input_mode="NEVER"
)

tech_agent = ConversableAgent(
    name="Tech_Agent",
    llm_config=llm_config_openai,
    system_message=tech_persona
)

general_agent = ConversableAgent(
    name="General_Agent",
    llm_config=llm_config_openai,
    system_message=general_persona
)

user_proxy = UserProxyAgent(
    name="User_Proxy",
    human_input_mode="NEVER",
    code_execution_config={"use_docker": False},
    is_termination_msg=lambda x: "ALL DONE" in content_str(x.get("content", "")),
)

# Register tools
register_all_tools(teacher_agent, student_agent)

# --------------------------------------------
# ✅ GroupChat Setup
# --------------------------------------------

all_agents = [user_proxy, teacher_agent, student_agent, tech_agent, general_agent]
group_chat = GroupChat(
    agents=all_agents,
    messages=[],
    max_round=12
)

manager = GroupChatManager(
    groupchat=group_chat,
    llm_config=llm_config_openai
)

# --------------------------------------------
# ✅ Main Entry Point
# --------------------------------------------

def run_multi_agent_chat(prompt: str) -> str:
    """Entry function to run the ESG analysis conversation"""
    user_proxy.initiate_chat(manager, message=f"Please help me analyze the following ESG report: {prompt}")

    tool_output = ""
    student_summary = ""

    for msg in reversed(manager.groupchat.messages):
        if not tool_output and msg.get("role") == "function":
            tool_output = extract_output(msg)
        if not student_summary and msg.get("name") == "Student_Agent":
            student_summary = extract_output(msg)
        if tool_output and student_summary:
            break

    if not tool_output and not student_summary:
        return "[⚠️ No agent output returned]"

    if isinstance(tool_output, (dict, list)):
        tool_output = str(tool_output)
    if isinstance(student_summary, (dict, list)):
        student_summary = str(student_summary)

    formatted_tool_output = format_tool_output(tool_output)

    return (
    f"### \n{formatted_tool_output}\n\n"
    f"### \n{student_summary.strip()}"
    )
