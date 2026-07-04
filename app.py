"""
English Teacher Dashboard - Streamlit App
Senior Python Developer: clean, professional, production-ready code with premium dark UI.
"""

import base64
import io
import json
import os
import re
from pathlib import Path

import pandas as pd
import streamlit as st
from PIL import Image

from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn

from paste_component import global_paste

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

    /* Hide Streamlit Native Header, Footer, and Main Menu */
    [data-testid="stHeader"] { display: none !important; }
    footer { display: none !important; }
    #MainMenu { visibility: hidden; }
    
    /* Adjust top padding since header is gone */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

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
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS — Robust JSON Parsing & Conversions
# ─────────────────────────────────────────────────────────────────────────────

def create_docx(markdown_text: str) -> io.BytesIO:
    """Convert simple markdown text to a DOCX file."""
    doc = Document()
    
    # Configure default style
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)

    for line in markdown_text.split('\n'):
        line = line.strip()
        if not line:
            doc.add_paragraph()
            continue
            
        if line.startswith('### '):
            p = doc.add_heading(line[4:], level=3)
        elif line.startswith('## '):
            p = doc.add_heading(line[3:], level=2)
        elif line.startswith('# '):
            p = doc.add_heading(line[2:], level=1)
        elif line.startswith('- ') or line.startswith('* '):
            doc.add_paragraph(line[2:], style='List Bullet')
        else:
            # Basic bolding `**text**` replacement for simple cases
            p = doc.add_paragraph()
            parts = line.split('**')
            for i, part in enumerate(parts):
                run = p.add_run(part)
                if i % 2 == 1:
                    run.bold = True

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def image_to_base64(uploaded_file) -> str:
    """Convert Streamlit UploadedFile to base64 JPEG string."""
    img = Image.open(uploaded_file)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def resize_preview(uploaded_file, max_width: int = 600):
    """Resize image for preview representation."""
    img = Image.open(uploaded_file)
    w, h = img.size
    if w > max_width:
        img = img.resize((max_width, int(h * max_width / w)), Image.Resampling.LANCZOS)
    return img


# ─────────────────────────────────────────────────────────────────────────────
# AI BACKEND
# ─────────────────────────────────────────────────────────────────────────────

def _get_openai_client(api_key: str):
    from openai import OpenAI
    return OpenAI(api_key=api_key)


def call_text_ai(prompt: str, api_key: str, provider: str) -> str:
    """Run text-based model request."""
    if provider == "OpenAI (GPT-4o)":
        client = _get_openai_client(api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    else:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        return response.text.strip()


def call_vision_ai(prompt: str, image_b64: str, api_key: str, provider: str) -> str:
    """Run image + text request."""
    if provider == "OpenAI (GPT-4o)":
        client = _get_openai_client(api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            temperature=0.6,
            max_tokens=4096,
        )
        return response.choices[0].message.content.strip()
    else:
        import google.generativeai as genai
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-pro")
        image_bytes = base64.b64decode(image_b64)
        image_part = {"mime_type": "image/jpeg", "data": image_bytes}
        response = model.generate_content(
            [prompt, image_part],
            safety_settings={
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            },
        )
        return response.text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style='text-align:center; padding:18px 0 10px 0;'>
            <span style='font-size:3rem;'>📚</span>
            <h2 style='margin:8px 0 2px 0; font-family: "Montserrat", sans-serif; font-size:1.35rem; font-weight:800;'>
                Teacher Panel
            </h2>
            <p style='color:#94a3b8; font-size:0.8rem; margin:0;'>AI English Teaching Toolkit</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    provider = st.selectbox(
        "🤖 AI Provider",
        ["OpenAI (GPT-4o)", "Google Gemini (1.5 Pro)"],
        help="Select model endpoint backend.",
    )

    api_key = st.text_input(
        "🔑 API Key",
        type="password",
        placeholder="sk-... or AIza...",
        help="Your secret key for OpenAI or Gemini APIs.",
    ) if "api_key" not in st.session_state else st.text_input(
        "🔑 API Key",
        value=st.session_state.api_key,
        type="password",
        placeholder="sk-... or AIza...",
        help="Your secret key for OpenAI or Gemini APIs.",
    )
    # Save key in state
    if api_key:
        st.session_state.api_key = api_key

    student_level = st.selectbox(
        "🎓 Student Level",
        ["A1 – Beginner", "A2 – Elementary", "B1 – Intermediate",
         "B2 – Upper-Intermediate", "C1 – Advanced", "C2 – Proficiency"],
        index=3,
        help="Instructs the model to generate content appropriate for this level.",
    )
    level_code = student_level.split("–")[0].strip()

    st.divider()
    st.markdown(
        """
        <div style='font-size:0.8rem; color:#64748b; line-height:1.6; padding: 0 6px;'>
            <b style='color:#a78bfa;'>Dashboard Guide:</b><br>
            1. Select AI backend & enter key<br>
            2. Choose student level target<br>
            3. Switch between workspaces below!
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown(
        "<div style='font-size:0.75rem; color:#475569; text-align:center;'>English Teacher Dashboard v1.1</div>",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# API KEY GUARD
# ─────────────────────────────────────────────────────────────────────────────
def require_api_key() -> bool:
    if not st.session_state.get("api_key"):
        st.warning("⚠️ Please provide an API key in the sidebar to start utilizing AI features.", icon="🔑")
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style='text-align:center; padding: 18px 0 10px 0;'>
        <h1 style='font-size:2.8rem; font-weight:800; margin:0;
                   background: linear-gradient(135deg, #a78bfa 0%, #818cf8 50%, #f472b6 100%);
                   -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                   background-clip:text;'>
            📚 English Teacher Dashboard
        </h1>
        <p style='color:#94a3b8; font-size:1.05rem; margin:8px 0 0 0;'>
            Advanced toolkit to correct grammar, build quizzes, extract vocabulary, and plan lessons
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# TABS SETUP
# ─────────────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "✅ Grammar Checker",
    "🧠 Quiz Generator",
    "📖 Vocabulary Builder",
    "📷 Textbook Scanner",
    "🗓️ Lesson Planner",
])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — GRAMMAR CHECKER
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
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
                    f"submitted by a student targeting {level_code} level.\n\n"
                    f"TEXT:\n\"\"\"\n{student_text}\n\"\"\"\n\n"
                    f"Provide a clear, simple markdown response containing:\n"
                    f"1. A corrected version of the text.\n"
                    f"2. A bulleted list explaining the grammar mistakes and rules suitable for level {level_code}.\n"
                    f"Note: Assume this is for an ONLINE lesson (Zoom/Miro), so provide suggestions that are easy to screen-share or type in a chat.\n"
                    f"Keep it clean and easy to read. Do NOT use complex JSON formatting."
                )
                try:
                    raw = call_text_ai(prompt, st.session_state.api_key, provider)
                    
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
with tabs[1]:
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
                    f"Target Student CEFR Level: {level_code}.\n"
                    f"Provide exactly 4 options labeled A, B, C, and D for each item.\n\n"
                    f"Format the output as a simple, easy-to-read markdown document.\n"
                    f"Include an 'Answer Key & Explanations' section at the bottom.\n"
                    f"IMPORTANT: The quiz must be adapted for an ONLINE format (e.g., questions that are easy to share on a Zoom screen or send in chat).\n"
                    f"Do NOT use JSON or complex formatting."
                )
                try:
                    raw = call_text_ai(prompt, st.session_state.api_key, provider)
                    st.session_state.quiz_data = raw
                    st.session_state.quiz_key_topic = quiz_topic
                    st.rerun()
                except Exception as e:
                    st.error(f"Error generating quiz content: {e}")

    if st.session_state.quiz_data:
        st.markdown(f"#### 📝 Topic: *{st.session_state.quiz_key_topic}* — Level {level_code}")
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
with tabs[2]:
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
                    raw = call_text_ai(prompt, st.session_state.api_key, provider)
                    
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
with tabs[3]:
    st.markdown("### 📷 Textbook Scanner & Exercise Generator")
    st.markdown(
        "<p style='color:#94a3b8;'>Upload one or several textbook pages. "
        "Select the page you want to analyze, then click Analyse.</p>",
        unsafe_allow_html=True,
    )

    # ─── session state init
    if "sc_selected_idx" not in st.session_state:
        st.session_state.sc_selected_idx = 0

    # ─── Upload zone
    scanner_files = st.file_uploader(
        "📂 Upload textbook pages OR click here and press Ctrl+V to paste a screenshot",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="scanner_upload",
        help="You can drag and drop multiple files, or click the box and press Ctrl+V to paste an image directly from your clipboard.",
    )

    # ─── Build image list
    sc_images = []
    for f in (scanner_files or []):
        sc_images.append((f.name, f.read(), None))
        
    if "pasted_images" in st.session_state:
        pasted = [(f"📋 Pasted image {i+1}", base64.b64decode(p_b64), p_id) for i, (p_id, p_b64) in enumerate(st.session_state.pasted_images.items())]
        sc_images = pasted + sc_images

    if sc_images:
        # ─── Thumbnail gallery with selection
        if len(sc_images) > 1:
            st.markdown(
                f"<p style='color:#a78bfa; font-size:0.9rem; margin:10px 0 4px 0;'>"
                f"✔️ {len(sc_images)} images loaded — click a thumbnail to select which page to analyse:</p>",
                unsafe_allow_html=True,
            )
            thumb_cols = st.columns(min(len(sc_images), 5))
            for ti, item in enumerate(sc_images):
                tname, tbytes = item[:2]
                with thumb_cols[ti % 5]:
                    thumb = resize_preview(io.BytesIO(tbytes), max_width=150)
                    is_active = (st.session_state.sc_selected_idx == ti)
                    border = "3px solid #a78bfa" if is_active else "2px solid rgba(139,92,246,0.2)"
                    st.markdown(
                        f"<div style='border:{border}; border-radius:10px; overflow:hidden; "
                        f"cursor:pointer; opacity:{'1' if is_active else '0.65'}; "
                        f"transition:all 0.2s;'>",
                        unsafe_allow_html=True,
                    )
                    st.image(thumb, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    label = f"★ {tname[:20]}" if is_active else tname[:20]
                    if st.button(label, key=f"sc_thumb_{ti}", use_container_width=True):
                        st.session_state.sc_selected_idx = ti
                        st.rerun()

        # Clamp selection index
        sel_idx = min(st.session_state.sc_selected_idx, len(sc_images) - 1)
        sel_name, sel_bytes = sc_images[sel_idx][:2]
        sel_paste_id = sc_images[sel_idx][2] if len(sc_images[sel_idx]) > 2 else None

        # ─── Preview of selected image
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(f"<p style='color:#a78bfa; font-size:0.9rem; margin:12px 0 4px 0;'>🔍 Previewing: <b>{sel_name}</b></p>", unsafe_allow_html=True)
        with c2:
            if sel_paste_id:
                if st.button("🗑️ Remove", key=f"del_preview_{sel_paste_id}"):
                    del st.session_state.pasted_images[sel_paste_id]
                    st.rerun()
                    
        st.image(resize_preview(io.BytesIO(sel_bytes), max_width=600), use_container_width=False)

        active_img_bytes = sel_bytes
    else:
        active_img_bytes = None
        st.markdown(
            "<div style='border:2px dashed rgba(139,92,246,0.3); border-radius:14px; "
            "padding:32px; text-align:center; color:#475569; margin:16px 0;'>"
            "<span style='font-size:2rem;'>📷</span><br>"
            "<b style='color:#94a3b8;'>No images yet</b><br>"
            "<span style='font-size:0.85rem;'>Upload files above or click the box to paste a screenshot (Ctrl+V)</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.divider()
    col_sc, _ = st.columns([2, 4])
    with col_sc:
        scan_btn = st.button(
            "🔬 Analyse Page & Generate Exercises",
            key="scan_btn",
            use_container_width=True,
            disabled=not active_img_bytes,
        )

    if scan_btn and active_img_bytes:
        if not require_api_key():
            st.stop()
        with st.spinner("Analyzing scanned page and planning tasks…"):
            img_b64 = base64.b64encode(active_img_bytes).decode("utf-8")
            prompt = (
                f"Analyze the text and topics on this textbook page image.\n"
                f"Target Student CEFR Level: {level_code}\n\n"
                f"Provide a clean, easy-to-read markdown document containing:\n"
                f"1. A brief summary of the grammar, topic, and vocabulary covered.\n"
                f"2. Three unique practice exercises based on the detected topics, tailored for ONLINE classes (e.g. interactive whiteboards, chat typing, or breakout room discussions).\n"
                f"3. Teacher notes or answer keys at the bottom.\n"
                f"Do NOT use JSON formatting."
            )
            try:
                raw = call_vision_ai(prompt, img_b64, st.session_state.api_key, provider)
                
                st.markdown("---")
                st.markdown(raw)
                
                docx_data = create_docx(raw)
                st.download_button(
                    label="⬇️ Download as Docx (Word/Google Docs)",
                    data=docx_data,
                    file_name="exercises.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"Could not complete Vision page scan: {e}")



# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — LESSON PLANNER
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
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
                    f"Create a 60-minute Lesson Plan for a class of {planner_class_size} students at level {level_code}.\n"
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
                        raw = call_vision_ai(base_prompt, img_b64, st.session_state.api_key, provider)
                    else:
                        raw = call_text_ai(base_prompt, st.session_state.api_key, provider)
                    
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
