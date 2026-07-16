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
    st.markdown("### 📚 Teaching Material Generator")
    st.markdown(
        "<p style='color:#94a3b8;'>Generate materials from your uploaded textbooks or by topic. "
        "Upload PDF/image files to your book library, then select pages to generate exercises.</p>",
        unsafe_allow_html=True,
    )

    mat_mode = st.radio(
        "Source",
        ["📖 From Book Library", "✏️ By Topic (AI Generate)"],
        horizontal=True,
        key="mat_mode",
    )

    if mat_mode == "📖 From Book Library":
        # ─── Book Library Management ─────────────────────────────────────
        with st.expander("📂 Upload New Book / Material", expanded=False):
            book_title = st.text_input("Book Title", placeholder="e.g. English File Upper-Intermediate", key="book_title")
            book_file = st.file_uploader(
                "Upload PDF or images",
                type=["pdf", "jpg", "jpeg", "png", "webp"],
                accept_multiple_files=False,
                key="book_upload",
            )

            if st.button("📚 Add to Library", key="add_book_btn", use_container_width=True):
                if not book_title.strip():
                    st.error("Enter a title first.")
                elif not book_file:
                    st.error("Upload a file first.")
                else:
                    safe_name = re.sub(r'[^\w\-.]', '_', book_file.name)
                    file_type = "pdf" if safe_name.lower().endswith(".pdf") else "image"
                    dm.add_book(book_title, safe_name, file_type, book_file.getbuffer().tobytes())
                    st.success(f"✅ Added: {book_title}")
                    st.rerun()

        # ─── Book List ───────────────────────────────────────────────────
        books = dm.get_books()
        if books:
            st.markdown("#### 📖 Your Book Library")
            for book in books:
                col_bk, col_bk_del = st.columns([5, 1])
                with col_bk:
                    st.markdown(
                        f"**{book['title']}** "
                        f"<span class='badge badge-purple'>{book['file_type'].upper()}</span> "
                        f"<span style='color:#64748b; font-size:0.8rem;'>{book['filename']}</span>",
                        unsafe_allow_html=True,
                    )
                with col_bk_del:
                    if st.button("🗑️", key=f"del_book_{book['id']}"):
                        dm.delete_book(book["id"])
                        st.rerun()

            st.divider()

            # ─── Generate from Book ──────────────────────────────────────
            st.markdown("#### 🔬 Generate Exercises from Book")

            selected_book = st.selectbox(
                "Select Book",
                options=books,
                format_func=lambda b: b["title"],
                key="gen_book_select",
            )

            if selected_book:
                book_filename = selected_book["filename"]

                if selected_book["file_type"] == "pdf":
                    # Extract pages from PDF
                    try:
                        import fitz  # PyMuPDF
                        file_bytes = dm.get_file(book_filename)
                        if not file_bytes:
                            raise Exception("Failed to download file from Supabase.")
                        doc = fitz.open(stream=file_bytes, filetype="pdf")
                        total_pages = len(doc)
                        st.caption(f"📄 {total_pages} pages")

                        page_range = st.slider(
                            "Page range",
                            1, total_pages, (1, min(3, total_pages)),
                            key="pdf_page_range",
                        )

                        # Show preview of selected pages
                        preview_cols = st.columns(min(page_range[1] - page_range[0] + 1, 4))
                        selected_page_images = []
                        for i, pg_num in enumerate(range(page_range[0] - 1, page_range[1])):
                            page = doc[pg_num]
                            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                            img_bytes = pix.tobytes("png")
                            selected_page_images.append(img_bytes)
                            with preview_cols[i % 4]:
                                st.image(img_bytes, caption=f"Page {pg_num + 1}", use_container_width=True)
                        doc.close()
                    except Exception as e:
                        st.error(f"Error reading PDF: {e}")
                        selected_page_images = []
                else:
                    # Image file — just show it
                    file_bytes = dm.get_file(book_filename)
                    if file_bytes:
                        st.image(file_bytes, caption=selected_book["title"], use_container_width=False, width=400)
                        selected_page_images = [file_bytes]
                    else:
                        st.error("File not found on Supabase.")
                        selected_page_images = []

                gen_type = st.multiselect(
                    "What to generate:",
                    ["📖 Grammar Theory", "✏️ Written Exercises", "📰 Reading Comprehension", "🧠 Quiz"],
                    default=["✏️ Written Exercises"],
                    key="gen_from_book_types",
                )

                if st.button("🔬 Generate from Selected Pages", key="gen_from_book_btn", use_container_width=True):
                    if not require_api_key():
                        st.stop()
                    if not selected_page_images:
                        st.error("No pages selected.")
                    else:
                        with st.spinner("AI is analyzing the textbook pages..."):
                            gen_prompt = (
                                f"Analyze this textbook page and generate teaching materials.\n"
                                f"Target Student Level: {st.session_state.get('level_code', 'B2')}\n"
                                f"Context: Online lessons (Zoom, screen sharing)\n\n"
                                f"Generate the following:\n"
                            )
                            for gt in gen_type:
                                gen_prompt += f"- {gt}\n"
                            gen_prompt += (
                                "\nBased on the content visible in the image, create relevant exercises "
                                "and materials. Include answer keys. Format as clean markdown."
                            )

                            try:
                                # Use the first page image for vision AI
                                img_b64 = base64.b64encode(selected_page_images[0]).decode("utf-8")
                                raw = call_vision_ai(gen_prompt, img_b64, st.session_state.api_key, st.session_state.get('provider', 'OpenAI (GPT-4o)'))

                                st.markdown("---")
                                st.markdown(raw)

                                docx_data = create_docx(raw)
                                st.download_button(
                                    label="⬇️ Download as Docx",
                                    data=docx_data,
                                    file_name=f"exercises_{selected_book['title'].replace(' ', '_')}.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                )
                            except Exception as e:
                                st.error(f"Error generating materials: {e}")
        else:
            st.info("📚 No books in the library yet. Upload one above to get started!")

    else:
        # ─── Original Topic-Based Generation ─────────────────────────────
        mat_topic = st.text_input(
            "📌 Lesson Topic",
            placeholder="e.g. Modal Verbs, Present Perfect, Conditionals...",
            key="mat_topic",
        )

        st.markdown("##### Select material types to generate:")
        mat_col1, mat_col2 = st.columns(2)
        with mat_col1:
            mat_theory = st.checkbox("📖 Grammar Reference (Theory)", value=True, key="mat_theory")
            mat_exercises = st.checkbox("✏️ Written Exercises", value=True, key="mat_exercises")
        with mat_col2:
            mat_reading = st.checkbox("📰 Reading Task", value=False, key="mat_reading")
            mat_listening = st.checkbox("🎧 Listening Activity (transcript)", value=False, key="mat_listening")

        col_mat_btn, _ = st.columns([1, 4])
        with col_mat_btn:
            mat_gen_btn = st.button("📚 Generate Materials", key="mat_gen_btn")

        if mat_gen_btn:
            if not require_api_key():
                st.stop()
            if not mat_topic.strip():
                st.error("Please enter a topic.")
            else:
                selected = []
                if mat_theory:
                    selected.append("A clear grammar reference / theory section explaining the rules with examples")
                if mat_exercises:
                    selected.append("5-8 written practice exercises (fill-in-the-blank, rewrite sentences, error correction) with answer key")
                if mat_reading:
                    selected.append("A short reading passage (150-250 words) on a related real-world topic, followed by 3-4 comprehension questions with answers")
                if mat_listening:
                    selected.append("A simulated listening activity: a dialogue transcript (2 speakers, 150-200 words) on a related topic, followed by 3-4 comprehension questions with answers")

                if not selected:
                    st.warning("Select at least one material type.")
                else:
                    with st.spinner("Generating study materials..."):
                        mat_prompt = (
                            f"Create a comprehensive study material package for an English lesson.\n"
                            f"Topic: \"{mat_topic}\"\n"
                            f"Target Student Level: {st.session_state.get('level_code', 'B2')}\n"
                            f"Context: Online lessons (Zoom, screen sharing)\n\n"
                            f"Include the following sections:\n"
                        )
                        for i, section in enumerate(selected, 1):
                            mat_prompt += f"{i}. {section}\n"

                        mat_prompt += (
                            "\nFormat the output as a clean, well-structured markdown document "
                            "with clear headings and sections. Use examples that are relevant and engaging. "
                            "Make it ready to share with the student. Do NOT use JSON."
                        )

                        try:
                            raw = call_text_ai(mat_prompt, st.session_state.api_key, st.session_state.get('provider', 'OpenAI (GPT-4o)'))

                            st.markdown("---")
                            st.markdown(raw)

                            docx_data = create_docx(raw)
                            st.download_button(
                                label="⬇️ Download Materials as Docx",
                                data=docx_data,
                                file_name=f"materials_{mat_topic.replace(' ', '_')}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            )
                        except Exception as e:
                            st.error(f"Error generating materials: {e}")


    # ═══════════════════════════════════════════════════════════════════════════════
    # TAB 10 — LISTENING ACTIVITY
    # ═══════════════════════════════════════════════════════════════════════════════
