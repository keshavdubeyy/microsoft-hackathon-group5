"""Injects the design system CSS into the Streamlit app.

tokens.css and streamlit.css are the shared design system, used unchanged.
APP_CSS adds the few app-specific pieces, built only from its tokens.
"""
from pathlib import Path

import streamlit as st

_DIR = Path(__file__).resolve().parent.parent / "design-system"

APP_CSS = """
/* Brand line in the sidebar (h1 is display-size, too big there) */
.ce-brand { font-size: var(--text-subheading); font-weight: var(--font-weight-medium); margin: 0; }

/* Status chips: outlined pills, monochrome */
.ce-chip {
  display: inline-block; padding: 2px var(--spacing-12);
  border: 1px solid var(--color-hairline); border-radius: var(--radius-tags);
  font-size: var(--text-caption); font-weight: var(--font-weight-medium); color: var(--color-graphite);
}
.ce-chip--confirmed { color: var(--color-obsidian); }
.ce-chip--rejected, .ce-chip--cancelled { color: var(--color-smoke); }

/* Alerts: no accent colours; hairline outline, meaning carried by the text */
.stAlertContainer {
  background: transparent !important; border: 1px solid var(--color-hairline);
  border-radius: var(--radius-cards); color: var(--color-obsidian);
}
.stAlertContainer * { color: var(--color-obsidian) !important; }
.stAlertContainer[role="alert"] p:first-child { font-weight: var(--font-weight-medium); }
"""


def apply_theme() -> None:
    css = "\n".join((_DIR / f).read_text(encoding="utf-8") for f in ("tokens.css", "streamlit.css"))
    st.markdown(f"<style>{css}\n{APP_CSS}</style>", unsafe_allow_html=True)


def chip(label, variant):
    """Status chip HTML for st.markdown(..., unsafe_allow_html=True)."""
    return f'<span class="ce-chip ce-chip--{variant}">{label}</span>'
