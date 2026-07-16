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
                f"Target Student CEFR Level: {st.session_state.get('level_code', 'B2')}\n\n"
                f"Provide a clean, easy-to-read markdown document containing:\n"
                f"1. A brief summary of the grammar, topic, and vocabulary covered.\n"
                f"2. Three unique practice exercises based on the detected topics, tailored for ONLINE classes (e.g. interactive whiteboards, chat typing, or breakout room discussions).\n"
                f"3. Teacher notes or answer keys at the bottom.\n"
                f"Do NOT use JSON formatting."
            )
            try:
                raw = call_vision_ai(prompt, img_b64, st.session_state.api_key, st.session_state.get('provider', 'OpenAI (GPT-4o)'))
            
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
