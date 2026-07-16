import streamlit as st
import data_manager as dm
import notion_sync
from utils import *
import re
from pathlib import Path
import io
import json
from datetime import datetime, date, time as dt_time, timedelta

def render():
    st.markdown("### ✅ Grammar & Style Checker")
    st.markdown(
        "<p style='color:#94a3b8;'>Analyze student essays or written text. "
        "AI will check grammatical correctness, style consistency, and rule violations.</p>",
        unsafe_allow_html=True,
    )

    student_text = st.text_area(
        "Student Essay / Writing Input",
        height=220,
        placeholder="Paste writing draft here...",
        key="grammar_input",
    )

    col_btn, _ = st.columns([1, 5])
    with col_btn:
        check_btn = st.button("🔍 Check Grammar", key="grammar_check_btn")

    if check_btn:
        if not require_api_key():
            st.stop()
        if not student_text.strip():
            st.error("Please insert text to examine first.")
        else:
            with st.spinner("Analyzing essay grammar…"):
                prompt = (
                    f"You are a professional English ESL teacher. Analyze this writing "
                    f"submitted by a student targeting {st.session_state.get('level_code', 'B2')} level.\n\n"
                    f"TEXT:\n\"\"\"\n{student_text}\n\"\"\"\n\n"
                    f"Provide a clear, simple markdown response containing:\n"
                    f"1. A corrected version of the text.\n"
                    f"2. A bulleted list explaining the grammar mistakes and rules suitable for level {st.session_state.get('level_code', 'B2')}.\n"
                    f"Note: Assume this is for an ONLINE lesson (Zoom/Miro), so provide suggestions that are easy to screen-share or type in a chat.\n"
                    f"Keep it clean and easy to read. Do NOT use complex JSON formatting."
                )
                try:
                    raw = call_text_ai(prompt, st.session_state.api_key, st.session_state.get("provider", "OpenAI (GPT-4o)"))
                
                    st.markdown("---")
                    st.markdown(raw)
                
                    docx_data = create_docx(raw)
                    st.download_button(
                        label="⬇️ Download as Docx (Word/Google Docs)",
                        data=docx_data,
                        file_name="grammar_correction.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                
                except Exception as e:
                    st.error(f"Failed to complete grammar inspection: {e}")


    # ═══════════════════════════════════════════════════════════════════════════════
    # TAB 2 — QUIZ GENERATOR
    # ═══════════════════════════════════════════════════════════════════════════════
