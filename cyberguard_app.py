import os
import socket

import streamlit as st
from crewai.tools import tool
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

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

# Setup Gemini AI module
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)


# Port Scanner Tool
@tool("Port Scanner Tool")
def run_port_scanner(target_domain: str) -> str:
    """Use this tool to check for open ports on the specified target domain."""

    ports_to_scan = [21, 22, 80, 443, 3306, 8080]
    open_ports = []

    try:
        target_ip = socket.gethostbyname(target_domain)
    except socket.gaierror:
        return f"Error: Can't find '{target_domain}'..."

    for port in ports_to_scan:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        if sock.connect_ex((target_ip, port)) == 0:
            open_ports.append(str(port))
        sock.close()

    if open_ports:
        return f"Success! Open ports on {target_domain}: {', '.join(open_ports)}"
    else:
        return f"None of the ports checked on {target_domain} are open."


# Streamlit User Interface
st.write("Enter your website's domain name below.")
target_url = st.text_input("Domain Name (eg: scanme.nmap.org)", placeholder="example.com")

# The part that activates when the button is pressed
if st.button("🔍 Start scanning...", type="primary"):
    
    if not target_url:
        st.warning("Please enter a domain name.")
    else:
        # Loading Animation
        with st.spinner(f"The CyberGuard AI team is analyzing {target_url}... This will take about a minute ⏳"):
