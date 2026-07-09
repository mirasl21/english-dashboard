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
    st.markdown("### 📖 Vocabulary Extractor")
    st.markdown(
        "<p style='color:#94a3b8;'>Scan articles or texts to extract complex terms (B2-C1 CEFR range), translations, and classroom examples.</p>",
        unsafe_allow_html=True,
    )

    vocab_text = st.text_area(
        "Source Reading Passage",
        height=200,
        placeholder="Paste read material or articles...",
        key="vocab_input",
    )

    target_lang = st.selectbox(
        "Translation Language",
        ["Russian", "Ukrainian", "Spanish", "French", "German",
         "Chinese (Simplified)", "Arabic", "Turkish", "Portuguese"],
        key="vocab_lang",
    )

    col_v, _ = st.columns([1, 4])
    with col_v:
        vocab_btn = st.button("📖 Extract Vocabulary", key="vocab_btn")

    if vocab_btn:
        if not require_api_key():
            st.stop()
        if not vocab_text.strip():
            st.error("Provide a passage first.")
        else:
            with st.spinner("Identifying target vocabulary…"):
                prompt = (
                    f"Extract 8 to 12 challenging words, phrasal verbs, or idioms (B2-C1 difficulty) "
                    f"from the English text below.\n\n"
                    f"TEXT:\n\"\"\"\n{vocab_text}\n\"\"\"\n\n"
                    f"Provide a clean markdown list. For each word, include:\n"
                    f"- Part of speech\n"
                    f"- CEFR Level\n"
                    f"- Definition in English\n"
                    f"- Translation to {target_lang}\n"
                    f"- A clear example sentence\n"
                    f"Do NOT use JSON."
                )
                try:
                    raw = call_text_ai(prompt, st.session_state.api_key, st.session_state.get("provider", "OpenAI (GPT-4o)"))
                
                    st.markdown("---")
                    st.markdown(raw)
                
                    docx_data = create_docx(raw)
                    st.download_button(
                        label="⬇️ Download as Docx (Word/Google Docs)",
                        data=docx_data,
                        file_name="vocabulary_list.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                except Exception as e:
                    st.error(f"Error extracting vocabulary: {e}")


    # ═══════════════════════════════════════════════════════════════════════════════
    # TAB 4 — TEXTBOOK SCANNER
    # ═══════════════════════════════════════════════════════════════════════════════
