"""Corporate styling — white background, blue accents — injected as CSS."""
import streamlit as st

BLUE = "#1a4f8b"


def inject() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{ background: #ffffff; }}
        h1, h2, h3 {{ color: {BLUE}; }}
        .stButton > button {{
            background: {BLUE}; color: #ffffff; border: none;
            padding: 0.55rem 1.3rem; font-weight: 600; border-radius: 6px;
        }}
        .stButton > button:hover {{ background: #15406f; color: #ffffff; }}
        section[data-testid="stSidebar"] {{ background: #f5f8fc; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
