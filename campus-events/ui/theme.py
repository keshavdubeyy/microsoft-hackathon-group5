"""Injects the design system CSS into the Streamlit app."""
from pathlib import Path

import streamlit as st

_DIR = Path(__file__).resolve().parent.parent / "design-system"


def apply_theme() -> None:
    css = "\n".join((_DIR / f).read_text(encoding="utf-8") for f in ("tokens.css", "streamlit.css"))
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
