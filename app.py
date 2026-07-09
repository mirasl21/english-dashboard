"""
English Teacher Dashboard - Streamlit App
Senior Python Developer: clean, professional, production-ready code with premium dark UI.
"""

import base64
import io
import json
import os
import re
from datetime import datetime, date, time as dt_time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn

from paste_component import global_paste
import data_manager as dm

import notion_sync

import telegram_bot as tg_bot

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="English Teacher Dashboard",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "pasted_images" not in st.session_state:
    st.session_state.pasted_images = {}
if "last_paste_id" not in st.session_state:
    st.session_state.last_paste_id = ""

paste_data = global_paste(key="global_paste_listener")
if paste_data and isinstance(paste_data, str) and paste_data.startswith("data:image"):
    parts = paste_data.split("|paste_")
    data_uri = parts[0]
    paste_id = parts[1] if len(parts) > 1 else ""
    
    base64_str = data_uri.split(",")[1]
    
    if paste_id and st.session_state.last_paste_id != paste_id:
        st.session_state.last_paste_id = paste_id
        st.session_state.pasted_images[paste_id] = base64_str
    elif not paste_id:
        st.session_state.pasted_images["default"] = base64_str

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS — Premium design update
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    /* Gradient Background */
    .stApp {
        background: radial-gradient(circle at 50% 10%, #151233 0%, #090818 70%, #05040d 100%);
        color: #f1f5f9;
    }

    /* We intentionally leave the native header and toolbar untouched so the sidebar toggle works flawlessly. */

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d0c1d 0%, #161430 100%) !important;
        border-right: 1px solid rgba(139, 92, 246, 0.2);
    }
    [data-testid="stSidebar"] .stMarkdown h2 {
        color: #a78bfa !important;
    }

    /* Custom Glassmorphic Cards */
    .card {
        background: rgba(25, 23, 48, 0.45);
        border: 1px solid rgba(139, 92, 246, 0.18);
        border-radius: 16px;
        padding: 24px;
        margin: 14px 0;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4);
        transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
    }
    .card:hover {
        border-color: rgba(139, 92, 246, 0.45);
        box-shadow: 0 10px 35px rgba(139, 92, 246, 0.12);
        transform: translateY(-2px);
    }

    /* Accent & Action Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed 0%, #c084fc 100%);
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 10px 28px !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        letter-spacing: 0.5px !important;
        box-shadow: 0 4px 18px rgba(124, 58, 237, 0.3);
        transition: all 0.25s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(124, 58, 237, 0.5);
        background: linear-gradient(135deg, #6d28d9 0%, #a855f7 100%) !important;
    }
    .stButton > button:active {
        transform: translateY(0);
    }

    /* Secondary buttons / resets */
    div.stButton > button[key*="reset"], div.stButton > button[key*="clear"] {
        background: rgba(255, 255, 255, 0.08) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        box-shadow: none !important;
    }
    div.stButton > button[key*="reset"]:hover, div.stButton > button[key*="clear"]:hover {
        background: rgba(255, 255, 255, 0.15) !important;
        border-color: rgba(255, 255, 255, 0.3) !important;
    }

    /* Modern Styled Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(13, 11, 28, 0.6);
        border-radius: 16px;
        padding: 6px;
        gap: 6px;
        border: 1px solid rgba(139, 92, 246, 0.15);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px;
        color: #94a3b8;
        font-weight: 600;
        font-family: 'Plus Jakarta Sans', sans-serif;
        padding: 10px 20px;
        transition: all 0.25s ease;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #7c3aed 0%, #9061f9 100%) !important;
        color: white !important;
        box-shadow: 0 4px 20px rgba(124, 58, 237, 0.35);
    }

    /* Text Inputs & Inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background: rgba(13, 11, 28, 0.4) !important;
        border: 1px solid rgba(139, 92, 246, 0.25) !important;
        border-radius: 12px !important;
        color: #f1f5f9 !important;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #a78bfa !important;
        box-shadow: 0 0 0 3px rgba(167, 139, 250, 0.2) !important;
    }

    /* Custom File Uploader */
    [data-testid="stFileUploader"] {
        background: rgba(25, 23, 48, 0.3);
        border: 2px dashed rgba(139, 92, 246, 0.3);
        border-radius: 16px;
    }

    /* Spans & Error Highlights */
    .error-highlight {
        background: rgba(239, 68, 68, 0.2);
        border-bottom: 2px solid #ef4444;
        border-radius: 4px;
        padding: 2px 4px;
        color: #fca5a5;
        font-weight: 600;
        cursor: help;
        position: relative;
    }
    .error-highlight:hover::after {
        content: attr(title);
        position: absolute;
        bottom: 125%;
        left: 50%;
        transform: translateX(-50%);
        background: #0f172a;
        color: #f8fafc;
        padding: 6px 12px;
        border-radius: 8px;
        font-size: 0.85rem;
        white-space: nowrap;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        border: 1px solid rgba(139, 92, 246, 0.3);
        z-index: 999;
    }

    /* Dynamic Pill Badges */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 3px 12px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        border: 1px solid transparent;
    }
    .badge-purple { background: rgba(139, 92, 246, 0.15); color: #c084fc; border-color: rgba(139, 92, 246, 0.3); }
    .badge-green  { background: rgba(16, 185, 129, 0.15); color: #34d399; border-color: rgba(16, 185, 129, 0.3); }
    .badge-blue   { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border-color: rgba(59, 130, 246, 0.3); }
    .badge-red    { background: rgba(239, 68, 68, 0.15);  color: #f87171; border-color: rgba(239, 68, 68, 0.3); }
    .badge-yellow { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.3); }

    /* Custom Tables */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(139, 92, 246, 0.15);
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background: rgba(25, 23, 48, 0.3) !important;
        border: 1px solid rgba(139, 92, 246, 0.15) !important;
        border-radius: 12px !important;
        padding: 12px 18px !important;
        color: #c084fc !important;
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(13, 11, 28, 0.4);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(139, 92, 246, 0.35);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(139, 92, 246, 0.55);
    }

    /* Hide default Streamlit footer */
    footer { visibility: hidden; }
    #MainMenu { visibility: hidden; }

    /* Smooth fade-in for content */
    .stTabs [data-baseweb="tab-panel"] {
        animation: fadeIn 0.3s ease-in-out;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(6px); }
        to   { opacity: 1; transform: translateY(0); }
    }

    /* Metric cards styling */
    [data-testid="stMetric"] {
        background: rgba(25, 23, 48, 0.35);
        border: 1px solid rgba(139, 92, 246, 0.15);
        border-radius: 14px;
        padding: 16px;
    }
    [data-testid="stMetricLabel"] {
        color: #a78bfa !important;
    }

    /* Divider styling */
    hr {
        border-color: rgba(139, 92, 246, 0.12) !important;
    }

    /* Toast notifications */
    [data-testid="stToast"] {
        background: rgba(25, 23, 48, 0.9) !important;
        border: 1px solid rgba(139, 92, 246, 0.3) !important;
        border-radius: 12px !important;
    }
    </style>

    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS — Robust JSON Parsing & Conversions
# ─────────────────────────────────────────────────────────────────────────────

from utils import *
import importlib
import tabs.grammar_checker
import tabs.quiz_generator
import tabs.vocab_builder
import tabs.textbook_scanner
import tabs.lesson_planner
import tabs.schedule
import tabs.payments
import tabs.homework_check
import tabs.materials
import tabs.listening
import tabs.guide

import data_manager
import utils

utils.render_sidebar()

ui_tabs = st.tabs([
    "✅ Grammar Checker",
    "🧠 Quiz Generator",
    "📖 Vocabulary Builder",
    "📷 Textbook Scanner",
    "🗓️ Lesson Planner",
    "📅 Schedule",
    "💰 Payments",
    "📝 Homework Check",
    "📚 Materials",
    "🎧 Listening",
    "💡 Guide",
])

with ui_tabs[0]:
    tabs.grammar_checker.render()
with ui_tabs[1]:
    tabs.quiz_generator.render()
with ui_tabs[2]:
    tabs.vocab_builder.render()
with ui_tabs[3]:
    tabs.textbook_scanner.render()
with ui_tabs[4]:
    tabs.lesson_planner.render()
with ui_tabs[5]:
    tabs.schedule.render()
with ui_tabs[6]:
    tabs.payments.render()
with ui_tabs[7]:
    tabs.homework_check.render()
with ui_tabs[8]:
    tabs.materials.render()
with ui_tabs[9]:
    tabs.listening.render()
with ui_tabs[10]:
    tabs.guide.render()
