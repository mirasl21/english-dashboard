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
    st.markdown("### 🎧 Listening Activity")
    st.markdown(
        "<p style='color:#94a3b8;'>Upload audio files from your textbooks or the internet. "
        "Students can listen and complete comprehension exercises. "
        "You can also generate questions based on the audio topic.</p>",
        unsafe_allow_html=True,
    )

    # ─── Upload Audio Files ──────────────────────────────────────────────
    with st.expander("📂 Upload Audio File", expanded=False):
        audio_title = st.text_input(
            "Audio Title",
            placeholder="e.g. Unit 3 - Dialogue at the Airport",
            key="audio_title",
        )
        audio_topic = st.text_input(
            "Topic / Description",
            placeholder="e.g. Travel vocabulary, asking for directions",
            key="audio_topic",
        )
        audio_level = st.selectbox(
            "Level",
            ["A1", "A2", "B1", "B2", "C1", "C2"],
            index=3,
            key="audio_level",
        )

        # Optionally link to a book
        audio_books = dm.get_books()
        audio_book_id = ""
        if audio_books:
            link_book = st.selectbox(
                "Link to book (optional)",
                options=[{"id": "", "title": "— None —"}] + audio_books,
                format_func=lambda b: b["title"],
                key="audio_link_book",
            )
            audio_book_id = link_book["id"] if link_book["id"] else ""

        audio_file = st.file_uploader(
            "Upload audio",
            type=["mp3", "wav", "ogg", "m4a", "flac"],
            key="audio_file_upload",
        )

        if st.button("🎵 Add Audio", key="add_audio_btn", use_container_width=True):
            if not audio_title.strip():
                st.error("Enter an audio title first.")
            elif not audio_file:
                st.error("Upload an audio file first.")
            else:
                safe_name = re.sub(r'[^\w\-.]', '_', audio_file.name)
                dm.add_audio_file(audio_title, safe_name, audio_file.getbuffer().tobytes(), audio_book_id, audio_topic, audio_level)
                st.success(f"✅ Added: {audio_title}")
                st.rerun()

    # ─── Audio Library & Player ──────────────────────────────────────────
    audio_files = dm.get_audio_files()

    if audio_files:
        st.markdown("#### 🎵 Audio Library")

        # Filter by level
        filter_levels = st.multiselect(
            "Filter by level",
            ["A1", "A2", "B1", "B2", "C1", "C2"],
            default=[],
            key="audio_filter_level",
        )

        filtered = audio_files
        if filter_levels:
            filtered = [a for a in audio_files if a.get("level", "") in filter_levels]

        for audio in filtered:
            with st.container():
                st.markdown(
                    f"<div class='card'>"
                    f"<div style='display:flex; justify-content:space-between; align-items:center;'>"
                    f"<div>"
                    f"<span style='font-size:1.2rem; font-weight:700; color:#c084fc;'>🎧 {audio['title']}</span><br>"
                    f"<span style='color:#94a3b8; font-size:0.85rem;'>"
                    f"{audio.get('topic', '')} "
                    f"<span class='badge badge-purple'>{audio.get('level', '')}</span>"
                    f"</span>"
                    f"</div>"
                    f"</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                audio_filename = audio.get("filename", "")
                if audio_filename:
                    audio_bytes = dm.get_file(audio_filename)
                    if audio_bytes:
                        suffix = audio_filename.split(".")[-1]
                        st.audio(audio_bytes, format=f"audio/{suffix}")

                    col_gen_q, col_dl, col_del_audio = st.columns([2, 1, 1])
                    with col_gen_q:
                        if st.button("🧠 Generate Questions", key=f"gen_q_{audio['id']}"):
                            if not require_api_key():
                                st.stop()
                            with st.spinner("Generating listening comprehension questions..."):
                                q_prompt = (
                                    f"Create a listening comprehension exercise for English students.\n"
                                    f"Audio Topic: \"{audio.get('topic', audio['title'])}\"\n"
                                    f"Student Level: {audio.get('level', 'B2')}\n\n"
                                    f"Generate:\n"
                                    f"1. 5 pre-listening discussion questions\n"
                                    f"2. 5 while-listening comprehension questions (True/False and multiple choice)\n"
                                    f"3. 3 post-listening discussion prompts\n"
                                    f"4. Answer key\n\n"
                                    f"Format as clean markdown. Make questions engaging and level-appropriate."
                                )
                                try:
                                    raw = call_text_ai(q_prompt, st.session_state.api_key, st.session_state.get("provider", "OpenAI (GPT-4o)"))
                                    st.markdown("---")
                                    st.markdown(raw)

                                    docx_data = create_docx(raw)
                                    st.download_button(
                                        label="⬇️ Download Questions as Docx",
                                        data=docx_data,
                                        file_name=f"listening_{audio['title'].replace(' ', '_')}.docx",
                                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                        key=f"dl_q_{audio['id']}",
                                    )
                                except Exception as e:
                                    st.error(f"Error: {e}")

                    with col_dl:
                        st.download_button(
                            label="⬇️ Download Audio",
                            data=audio_bytes,
                            file_name=audio["filename"],
                            mime=f"audio/{suffix}",
                            key=f"dl_audio_{audio['id']}",
                        )
                    with col_del_audio:
                        if st.button("🗑️ Delete", key=f"del_audio_{audio['id']}"):
                            dm.delete_audio_file(audio["id"])
                            st.rerun()
                else:
                    st.warning(f"⚠️ File not found: {audio['filename']}")
                st.markdown("")
    else:
        st.markdown(
            "<div style='border:2px dashed rgba(139,92,246,0.3); border-radius:14px; "
            "padding:32px; text-align:center; color:#475569; margin:16px 0;'>"
            "<span style='font-size:2rem;'>🎧</span><br>"
            "<b style='color:#94a3b8;'>No audio files yet</b><br>"
            "<span style='font-size:0.85rem;'>Upload MP3/WAV/OGG files from your textbooks or the internet</span>"
            "</div>",
            unsafe_allow_html=True,
        )

