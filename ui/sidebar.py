"""Sidebar navigation: New Report, Previous Reports, Settings."""
import streamlit as st


def render() -> str:
    st.sidebar.title("Company Intel")
    st.sidebar.caption("Due-diligence research tool")
    return st.sidebar.radio(
        "Menu",
        ["New Report", "Previous Reports", "Settings"],
        label_visibility="collapsed",
    )
