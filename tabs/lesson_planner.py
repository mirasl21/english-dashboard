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
    st.markdown("### 🗓️ Modern Lesson Planner")
    st.markdown(
        "<p style='color:#94a3b8;'>Plan your next 60-minute lesson. "
        "Upload one or more textbook pages for context, or just type a topic.</p>",
        unsafe_allow_html=True,
    )

    col_input1, col_input2 = st.columns([1, 1], gap="large")

    with col_input1:
        st.markdown("##### 📷 Option A — Textbook Source")

        # ─── session state for planner
        if "pl_selected_idx" not in st.session_state:
            st.session_state.pl_selected_idx = 0

        planner_files = st.file_uploader(
            "📂 Upload textbook pages OR click here and press Ctrl+V to paste a screenshot",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="planner_upload",
            help="You can drag and drop multiple files, or click the box and press Ctrl+V to paste an image directly from your clipboard.",
        )

        # Build image list
        pl_images = []
        for f in (planner_files or []):
            pl_images.append((f.name, f.read(), None))
        
        if "pasted_images" in st.session_state:
            pasted = [(f"📋 Pasted image {i+1}", base64.b64decode(p_b64), p_id) for i, (p_id, p_b64) in enumerate(st.session_state.pasted_images.items())]
            pl_images = pasted + pl_images

        if pl_images:
            if len(pl_images) > 1:
                st.markdown(
                    f"<p style='color:#a78bfa; font-size:0.85rem; margin:8px 0 4px 0;'>"
                    f"{len(pl_images)} pages — select which to use:</p>",
                    unsafe_allow_html=True,
                )
                thumb_pl_cols = st.columns(min(len(pl_images), 4))
                for ti, item in enumerate(pl_images):
                    tname, tbytes = item[:2]
                    with thumb_pl_cols[ti % 4]:
                        is_active = (st.session_state.pl_selected_idx == ti)
                        border = "3px solid #a78bfa" if is_active else "2px solid rgba(139,92,246,0.2)"
                        st.markdown(f"<div style='border:{border}; border-radius:8px; overflow:hidden; opacity:{'1' if is_active else '0.6'};'>", unsafe_allow_html=True)
                        st.image(resize_preview(io.BytesIO(tbytes), max_width=120), use_container_width=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                        if st.button(tname[:16], key=f"pl_thumb_{ti}", use_container_width=True):
                            st.session_state.pl_selected_idx = ti
                            st.rerun()

            pl_sel_idx = min(st.session_state.pl_selected_idx, len(pl_images) - 1)
            pl_sel_name, pl_sel_bytes = pl_images[pl_sel_idx][:2]
            pl_sel_paste_id = pl_images[pl_sel_idx][2] if len(pl_images[pl_sel_idx]) > 2 else None
        
            c1, c2 = st.columns([4, 1])
            with c2:
                if pl_sel_paste_id:
                    if st.button("🗑️ Remove", key=f"del_pl_preview_{pl_sel_paste_id}"):
                        del st.session_state.pasted_images[pl_sel_paste_id]
                        st.rerun()
        
            st.image(resize_preview(io.BytesIO(pl_sel_bytes), max_width=300), caption="Selected page", use_container_width=False)
            planner_img_bytes = pl_sel_bytes
        else:
            planner_img_bytes = None
            st.markdown(
                "<div style='border:2px dashed rgba(139,92,246,0.25); border-radius:12px; "
                "padding:24px; text-align:center; color:#475569; margin-top:8px;'>"
                "<span style='font-size:1.5rem;'>📷</span><br>"
                "<span style='font-size:0.85rem;'>Upload or paste textbook pages here (Ctrl+V)</span>"
                "</div>",
                unsafe_allow_html=True,
            )

    with col_input2:
        st.markdown("##### ✏️ Option B — Topic Prompting")
        planner_topic = st.text_input(
            "Lesson Focus Topic",
            placeholder="e.g. Mixed Conditionals, Presentation Vocabulary...",
            key="planner_topic",
        )
        planner_objective = st.text_input(
            "Target Lesson Objective",
            placeholder="e.g. Enable students to debate and propose solutions using structure...",
            key="planner_objective",
        )
        planner_class_size = st.slider("Class size (students)", 1, 30, 10, key="planner_class_size")

    st.markdown("---")
    col_plan, _ = st.columns([1, 4])
    with col_plan:
        plan_btn = st.button("🗓️ Plan Lesson Schedule", key="plan_btn")

    if plan_btn:
        if not require_api_key():
            st.stop()
        
        has_image = planner_img_bytes is not None
        has_topic = bool(planner_topic.strip())
    
        if not has_image and not has_topic:
            st.error("Please provide either a scan image or type a manual topic target.")
        else:
            with st.spinner("Structuring lesson flow (Warm-up, Presentation, Practice, Production, Cool-down)…"):
                objective_line = f"LESSON OBJECTIVE: {planner_objective}" if planner_objective else ""
                topic_or_image = (
                    "Based on the provided textbook page image, create a lesson plan pointing directly "
                    "to context or visual grammar points from the page."
                    if has_image else
                    f"Plan a lesson centered around: \"{planner_topic}\""
                )
            
                base_prompt = (
                    f"Create a 60-minute Lesson Plan for a class of {planner_class_size} students at level {st.session_state.get("level_code", "B2")}.\n"
                    f"{objective_line}\n"
                    f"{topic_or_image}\n\n"
                    f"Structure your response as a clean, simple markdown document including:\n"
                    f"- Lesson Title, Topic, Level, and Objective\n"
                    f"- Required Materials (e.g. Miro boards, Google Docs, specific links)\n"
                    f"- A clear step-by-step schedule (Warm-up, Presentation, Practice, Production, Cool-down) with timings and teacher/student actions. Focus entirely on ONLINE methodologies like Zoom Breakout Rooms, Screen Sharing, and Digital Whiteboards.\n"
                    f"- Homework and differentiation notes at the end.\n"
                    f"Do NOT use JSON formatting."
                )
                try:
                    if has_image:
                        img_b64 = base64.b64encode(planner_img_bytes).decode("utf-8")
                        raw = call_vision_ai(base_prompt, img_b64, st.session_state.api_key, st.session_state.get("provider", "OpenAI (GPT-4o)"))
                    else:
                        raw = call_text_ai(base_prompt, st.session_state.api_key, st.session_state.get("provider", "OpenAI (GPT-4o)"))
                
                    st.markdown("---")
                    st.markdown(raw)
                
                    docx_data = create_docx(raw)
                    st.download_button(
                        label="⬇️ Download as Docx (Word/Google Docs)",
                        data=docx_data,
                        file_name="lesson_plan.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

                except Exception as e:
                    st.error(f"Failed to generate lesson schedule: {e}")


    # ═══════════════════════════════════════════════════════════════════════════════
    # TAB 6 — SCHEDULE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════════
