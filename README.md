# 💬 ESG Language Decoder – Streamlit App

An interactive ESG report assistant powered by Streamlit and LLM agents (Gemini and OpenAI's GPT-3.5).

### ✨ Features

- 📄 Upload and analyze ESG reports using multi-agent LLMs
- ✨ Optimize ESG content with AI-powered suggestions
- 📊 Visualize ESG trends through interactive word clouds
- 🧰 Generate industry-specific ESG report templates
- 💬 Chat in three modes: Free, Analyze, and Advanced
- 🌐 Multilingual support: English and Traditional Chinese (optimized for English)

---

Ideal for ESG report writers, researchers, analysts, investors, and students exploring AI-powered sustainability reporting.

Chatbot template reference: A simple Streamlit app that shows how to build a chatbot using OpenAI's GPT-3.5.
[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://chatbot-template.streamlit.app/)

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

    - Note (commands for window users): if numpy installed with error:
      - Use python version == 3.10 and open venv to run 3.10 version
      ```
      $ py -3.10 -m venv .venv
      ```
      -  Run powershell as administrator and get authorized for venv-activation
      ```
      # Run in powershell as administrator
      $ Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
      ```

      ```
      # Run in terminal
      $ .venv\Scripts\activate
      ```

      - Deactivate to quit
      ```
      $ deactivate
      ```


2. Run the app (in venv)
   - Activate venv if needed to run in venv

   ```
   $ streamlit run streamlit_app.py
   ```

   - Press ctrl+C to stop the app

### Note:
#### About Gemini agent
   - Apply for Gemini API key: https://aistudio.google.com/app/apikey
   - About API quota: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas
   - About autogen using Gemini: https://microsoft.github.io/autogen/0.2/docs/topics/non-openai-models/cloud-gemini_vertexai/
   - About `content_str` with agent tool response: https://microsoft.github.io/autogen/0.2/docs/reference/code_utils/
   - Debug note: Additional manual install autogen instead of `pip install -r requirements.txt`
      ```
      $ pip install autogen
      ```
#### Resource
   - Python Version: 3.10
   - Using Gemini and OpenAI API

---

## See Deployed:
- Production (ckip-allowed): https://textmining-chatbot-group6-project.streamlit.app/
- Test: https://brian-textmining-chatbot.streamlit.app/
