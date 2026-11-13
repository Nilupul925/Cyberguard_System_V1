import os

import streamlit as st
from dotenv import load_dotenv

# Page Config
st.set_page_config(
    page_title="CyberGuard AI - Security Auditor", page_icon="🛡️", layout="centered"
)

st.title("🛡️ CyberGuard AI")
st.caption("Automatically check your website's security and get reports.")
st.divider()

# Load the API Key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("❌ The API Key is missing from the .env file!")
    st.stop()
