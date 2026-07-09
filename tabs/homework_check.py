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
    st.markdown("### 📝 AI Homework Checker")
    st.markdown(
        "<p style='color:#94a3b8;'>Paste the assignment and the student's answer. "
        "AI will check it, find errors, grade it, and provide recommendations. "
        "You can also send homework via Telegram bot and see bot check results below.</p>",
        unsafe_allow_html=True,
    )

    # ─── Send Homework via Telegram Bot ──────────────────────────────────
    with st.expander("📤 Send Homework to Student (Telegram)", expanded=False):
        hw_students = dm.get_students()
        tg_linked = [s for s in hw_students if s.get("telegram_username")]

        if not tg_linked:
            st.info("👈 Link students to Telegram usernames in the sidebar first.")
        else:
            col_hw_student, col_hw_due = st.columns([3, 1])
            with col_hw_student:
                hw_tg_student = st.selectbox(
                    "Student",
                    options=tg_linked,
                    format_func=lambda s: f"{s['name']} (@{s.get('telegram_username', '')})",
                    key="hw_tg_student",
                )
            with col_hw_due:
                hw_due_date = st.date_input("Due date", key="hw_due_date")

            hw_tg_assignment = st.text_area(
                "Assignment text",
                height=150,
                placeholder="e.g. Fill in the blanks with the correct form of the verb...\n1. She ___ (go) to school every day.",
                key="hw_tg_assignment",
            )

            if st.button("📤 Send via Telegram", key="send_hw_tg_btn", use_container_width=True):
                if not hw_tg_assignment.strip():
                    st.error("Enter the assignment text first.")
                else:
                    hw_record = dm.create_homework(
                        hw_tg_student["id"],
                        hw_tg_assignment,
                        hw_due_date.isoformat() if hw_due_date else "",
                    )
                    st.success(
                        f"✅ Homework created for {hw_tg_student['name']}!\n\n"
                        f"When the bot is running (`python telegram_bot.py`), "
                        f"it will send this assignment to @{hw_tg_student.get('telegram_username', '')} "
                        f"and auto-check the response."
                    )
                    st.rerun()

    # ─── Manual Homework Check (original) ────────────────────────────────
    with st.expander("✍️ Manual Homework Check", expanded=True):
        hw_col1, hw_col2 = st.columns(2, gap="large")

        with hw_col1:
            st.markdown("##### 📋 Assignment")
            hw_assignment = st.text_area(
                "Task / Exercise",
                height=200,
                placeholder="e.g. Fill in the blanks with the correct form of the verb...\n1. She ___ (go) to school every day.\n2. They ___ (not/like) spicy food.",
                key="hw_assignment",
            )

        with hw_col2:
            st.markdown("##### ✍️ Student's Answer")
            hw_answer = st.text_area(
                "Student's response",
                height=200,
                placeholder="1. goes\n2. doesn't like",
                key="hw_answer",
            )

        # Option to upload handwritten answer as image
        hw_image = st.file_uploader(
            "📷 Or upload a photo of handwritten answers",
            type=["jpg", "jpeg", "png", "webp"],
            key="hw_image_upload",
        )

        col_hw_btn, _ = st.columns([1, 4])
        with col_hw_btn:
            hw_check_btn = st.button("🔍 Check Homework", key="hw_check_btn")

        if hw_check_btn:
            if not require_api_key():
                st.stop()

            has_text_answer = bool(hw_answer.strip())
            has_image_answer = hw_image is not None

            if not hw_assignment.strip():
                st.error("Please provide the assignment/task.")
            elif not has_text_answer and not has_image_answer:
                st.error("Please provide the student's answer (text or image).")
            else:
                with st.spinner("AI is checking the homework..."):
                    hw_prompt = (
                        f"You are a professional English teacher checking homework.\n"
                        f"Student Level: {st.session_state.get("level_code", "B2")}\n\n"
                        f"ASSIGNMENT:\n\"\"\"\n{hw_assignment}\n\"\"\"\n\n"
                    )
                    if has_text_answer:
                        hw_prompt += f"STUDENT'S ANSWER:\n\"\"\"\n{hw_answer}\n\"\"\"\n\n"
                    if has_image_answer:
                        hw_prompt += "The student's handwritten answer is attached as an image. Please read and check it.\n\n"

                    hw_prompt += (
                        "Please provide a clear markdown response:\n"
                        "1. **Grade**: X/10\n"
                        "2. **Correct Answers**: Show the correct version\n"
                        "3. **Errors Found**: List each mistake with explanation\n"
                        "4. **Corrected Version**: The student's answer with all fixes applied\n"
                        "5. **Recommendations**: Tips for improvement\n"
                        "Keep it friendly and encouraging. Do NOT use JSON."
                    )
                    try:
                        if has_image_answer:
                            img_b64 = image_to_base64(hw_image)
                            raw = call_vision_ai(hw_prompt, img_b64, st.session_state.api_key, st.session_state.get("provider", "OpenAI (GPT-4o)"))
                        else:
                            raw = call_text_ai(hw_prompt, st.session_state.api_key, st.session_state.get("provider", "OpenAI (GPT-4o)"))

                        st.markdown("---")
                        st.markdown(raw)

                        docx_data = create_docx(raw)
                        st.download_button(
                            label="⬇️ Download Check Result as Docx",
                            data=docx_data,
                            file_name="homework_check.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                    except Exception as e:
                        st.error(f"Error checking homework: {e}")

    # ─── Homework History from Bot ────────────────────────────────────────
    with st.expander("📜 Homework History (Bot Results)", expanded=False):
        all_hw = dm.get_all_homework()
        if all_hw:
            student_map = {s["id"]: s["name"] for s in hw_students}
            for hw in all_hw[:20]:
                s_name = student_map.get(hw["student_id"], "Unknown")
                status_icon = {"sent": "📤", "submitted": "📥", "checked": "✅"}.get(hw["status"], "❓")
                st.markdown(f"**{status_icon} {s_name}** — {hw.get('created_at', '')[:10]}")
                st.markdown(f"> {hw['assignment'][:120]}...")
                if hw["status"] == "checked" and hw.get("check_result"):
                    st.markdown(f"**Оценка:** {hw.get('grade', '—')}")
                    with st.expander("Показать результат проверки", expanded=False):
                        st.markdown(hw["check_result"])
                elif hw["status"] == "submitted":
                    st.info(f"Ответ получен: {hw.get('student_answer', '')[:100]}...")
                st.markdown("---")
        else:
            st.caption("No homework history yet.")


    # ═══════════════════════════════════════════════════════════════════════════════
    # TAB 9 — MATERIAL GENERATOR (with Book Library)
    # ═══════════════════════════════════════════════════════════════════════════════
