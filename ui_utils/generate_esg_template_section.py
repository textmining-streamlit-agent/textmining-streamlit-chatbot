import streamlit as st
from db_utils.esg_report_db_utils import get_all_industries
from lib.generate_esg_template_analysis import run_esg_template_generation

def render_generate_template_main_section():
    st.markdown("---")
    col_title, col_close = st.columns([0.95, 0.05])
    with col_title:
        st.header("🧰 ESG Template Generator")
    with col_close:
        if st.button("❌", key=f"close_ESG_template_generator"):
            st.session_state.pop("template_task_function", None)
            st.rerun()

    # --- 預設五個產業 ---
    pinned_industries = [
        "Financial & Insurance",
        "Food",
        "Information Service Industry",
        "Shipping & Transportation",
        "Semiconductor Industry"
    ]

    try:
        all_industries_df = get_all_industries()
        all_industries = all_industries_df["industry_name_en"].dropna().unique().tolist()
    except Exception:
        all_industries = []
        st.error("⚠️ Failed to load industry list.")

    remaining_industries = [i for i in all_industries if i not in pinned_industries]
    industries_full_list = pinned_industries + sorted(remaining_industries)

    # --- 儲存使用者選項到 session_state ---
    st.session_state["template_format"] = st.selectbox(
        "📘 Choose Template Format", ["GRI", "SASB", "TCFD"],
        index=["GRI", "SASB", "TCFD"].index(st.session_state.get("template_format", "GRI"))
    )

    st.session_state["industry"] = st.selectbox(
        "🏭 Choose Industry", industries_full_list,
        index=industries_full_list.index(st.session_state.get("industry", "Financial & Insurance"))
    )

    st.session_state["compare"] = st.checkbox("📊 Compare with industry standard?", value=st.session_state.get("compare", True))

    # --- 產出與清除按鈕 ---
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🚀 Generate ESG Template", disabled=bool(st.session_state.get("template_result"))):
            st.session_state["trigger_template_result"] = True

    with col2:
        if st.button("❌ Clear Result"):
            for key in [
                "template_result", "trigger_template_result", "download_format",
                "template_format", "industry", "compare"]:
                st.session_state.pop(key, None)
            st.success("Session cleared. Please reselect options.")
            st.stop()

    # --- Call LLM / agent ---
    if st.session_state.get("trigger_template_result", False):
        st.subheader("📝 ESG Template Result")

        compare_flag = st.session_state.get("compare", True)
        template_format = st.session_state["template_format"]
        industry = st.session_state["industry"]

        with st.spinner("🔧 Generating ESG template..."):
            try:
                result = run_esg_template_generation(
                    template_format=template_format,
                    industry=industry,
                    compare=compare_flag
                )
                st.session_state["template_result"] = result
            except Exception:
                st.error("❌ Failed to generate ESG template.")
                st.session_state["template_result"] = ""
                st.stop()
            finally:
                st.session_state["trigger_template_result"] = False

    # --- 顯示產出結果 ---
    if st.session_state.get("template_result"):
        # st.markdown("#### 📋 Generated Template")
        with st.expander(f"📋 Show Generated Template", expanded=False):
            st.markdown(st.session_state["template_result"])

        # --- 下載選項 ---
        export_format = st.selectbox(
            "📦 Choose Download Format", ["TXT", "Word (.docx)"], key="download_format"
        )

        result = st.session_state["template_result"]
        industry = st.session_state["industry"]
        template_format = st.session_state["template_format"]

        if export_format == "TXT":
            file_bytes = result.encode("utf-8")
            mime, ext = "text/plain", "txt"
        else:  # Word (.docx)
            import io
            from docx import Document
            doc = Document()
            doc.add_paragraph(result)
            buffer = io.BytesIO()
            doc.save(buffer)
            file_bytes = buffer.getvalue()
            mime, ext = "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"

        st.download_button(
            label=f"📅 Download ESG Template ({ext.upper()})",
            data=file_bytes,
            file_name=f"ESG_Template_{industry}_{template_format}.{ext}",
            mime=mime
        )