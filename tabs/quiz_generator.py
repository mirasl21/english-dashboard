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
    st.markdown("### 🧠 Multiple-Choice Quiz Generator")
    st.markdown(
        "<p style='color:#94a3b8;'>Generate a 5-question evaluation quiz about any grammar point or general topic.</p>",
        unsafe_allow_html=True,
    )

    quiz_topic = st.text_input(
        "Quiz Subject or Topic",
        placeholder="e.g. Third Conditional, Collocations with 'Take', Past Continuous...",
        key="quiz_topic_input",
    )

    # Session State Initialization
    if "quiz_data" not in st.session_state:
        st.session_state.quiz_data = None
    if "quiz_key_topic" not in st.session_state:
        st.session_state.quiz_key_topic = ""

    col_gen, col_reset = st.columns([1, 4])
    with col_gen:
        gen_btn = st.button("⚡ Generate Quiz", key="quiz_gen_btn")
    with col_reset:
        if st.session_state.quiz_data:
            reset_btn = st.button("🔄 Reset Quiz", key="quiz_reset")
            if reset_btn:
                st.session_state.quiz_data = None
                st.rerun()

    if gen_btn:
        if not require_api_key():
            st.stop()
        if not quiz_topic.strip():
            st.error("Please specify a topic.")
        else:
            with st.spinner("Creating multiple choice assessment..."):
                prompt = (
                    f"Create a 5-question multiple-choice quiz testing knowledge on: \"{quiz_topic}\".\n"
                    f"Target Student CEFR Level: {st.session_state.get('level_code', 'B2')}.\n"
                    f"Provide exactly 4 options labeled A, B, C, and D for each item.\n\n"
                    f"Format the output as a simple, easy-to-read markdown document.\n"
                    f"Include an 'Answer Key & Explanations' section at the bottom.\n"
                    f"IMPORTANT: The quiz must be adapted for an ONLINE format (e.g., questions that are easy to share on a Zoom screen or send in chat).\n"
                    f"Do NOT use JSON or complex formatting."
                )
                try:
                    raw = call_text_ai(prompt, st.session_state.api_key, st.session_state.get('provider', 'OpenAI (GPT-4o)'))
                    st.session_state.quiz_data = raw
                    st.session_state.quiz_key_topic = quiz_topic
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating quiz content: {e}")

    if st.session_state.quiz_data:
        st.markdown(f"#### 📝 Topic: *{st.session_state.quiz_key_topic}* — Level {st.session_state.get('level_code', 'B2')}")
        st.markdown("---")
        st.markdown(st.session_state.quiz_data)
    
        docx_data = create_docx(st.session_state.quiz_data)
        st.download_button(
            label="⬇️ Download as Docx (Word/Google Docs)",
            data=docx_data,
            file_name=f"quiz_{st.session_state.quiz_key_topic.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )


    # ═══════════════════════════════════════════════════════════════════════════════
    # TAB 3 — VOCABULARY BUILDER
    # ═══════════════════════════════════════════════════════════════════════════════
