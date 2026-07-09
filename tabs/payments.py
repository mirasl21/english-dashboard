import streamlit as st
import pandas as pd
import data_manager as dm
import notion_sync
from utils import *
import re
from pathlib import Path
import io
import json
from datetime import datetime, date, time as dt_time, timedelta

def render():
    st.markdown("### 💰 Payment Tracker")
    st.markdown(
        "<p style='color:#94a3b8;'>Track paid and conducted lessons for each student. "
        "Get automatic reminders when a student's balance runs out.</p>",
        unsafe_allow_html=True,
    )

    pay_students = dm.get_students()

    if not pay_students:
        st.info("👈 Add students in the sidebar first.")
    else:
        # ─── Record Payment ──────────────────────────────────────────────
        with st.expander("💳 Record New Payment", expanded=False):
            col_ps, col_pn = st.columns(2)
            with col_ps:
                pay_student = st.selectbox(
                    "Student",
                    options=pay_students,
                    format_func=lambda s: s["name"],
                    key="pay_student",
                )
            with col_pn:
                pay_count = st.number_input("Number of lessons paid", min_value=1, max_value=100, value=4, key="pay_count")
            if st.button("💰 Record Payment", key="record_pay_btn", use_container_width=True):
                dm.record_payment(pay_student["id"], pay_count)
                st.success(f"Recorded: {pay_student['name']} paid for {pay_count} lessons")
                st.rerun()

        # ─── Balance Table ───────────────────────────────────────────────
        st.markdown("#### 📊 Student Balances")
        summaries = dm.get_all_payment_summaries()
        if summaries:
            table_data = []
            for s in summaries:
                if s["balance"] > 2:
                    status = "🟢 OK"
                elif s["balance"] > 0:
                    status = "🟡 Скоро закончится"
                else:
                    status = "🔴 Пора платить!"
                table_data.append({
                    "Student": s["name"],
                    "Level": s["level"],
                    "Paid": s["paid"],
                    "Conducted": s["conducted"],
                    "Balance": s["balance"],
                    "Status": status,
                })
            st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
        else:
            st.caption("No payment data yet.")


    # ═══════════════════════════════════════════════════════════════════════════════
    # TAB 8 — HOMEWORK CHECK
    # ═══════════════════════════════════════════════════════════════════════════════
