import os
import socket
import time
from urllib.parse import urlparse

import streamlit as st
from crewai import LLM, Agent, Crew, Process, Task
from crewai.tools import tool
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

# Setup Gemini AI module (CrewAI's built-in Gemini provider; LangChain models are not supported).
# Models are tried in order: if one is overloaded (503) or rate-limited (429), the next one is used.
# Override in .env, e.g. GEMINI_MODELS=gemini-3.8-flash,gemini-3.6-flash
GEMINI_MODELS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_MODELS", "gemini-3.8-flash,gemini-3.6-flash,gemini-3.5-flash"
    ).split(",")
    if m.strip()
]
RETRYABLE_ERRORS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "overloaded")


def make_llm(model_name: str) -> LLM:
    return LLM(model=f"gemini/{model_name}", api_key=api_key, temperature=0.3)


def normalize_domain(value: str) -> str:
    """Turn inputs like 'https://www.example.com/path' into 'www.example.com'."""
    value = value.strip()
    if "://" not in value:
        value = "//" + value
    return (urlparse(value).hostname or "").lower()


# Port Scanner Tool
@tool("Port Scanner Tool")
def run_port_scanner(target_domain: str) -> str:
    """Use this tool to check for open ports on the specified target domain."""

    ports_to_scan = [21, 22, 80, 443, 3306, 8080]
    open_ports = []
    target_domain = normalize_domain(target_domain)

    try:
        target_ip = socket.gethostbyname(target_domain)
    except (socket.gaierror, UnicodeError):
        return f"Error: Can't find '{target_domain}'..."

    for port in ports_to_scan:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                if sock.connect_ex((target_ip, port)) == 0:
                    open_ports.append(str(port))
        except OSError:
            continue

    if open_ports:
        return f"Success! Open ports on {target_domain}: {', '.join(open_ports)}"
    else:
        return f"None of the ports checked on {target_domain} are open."


def build_crew(target: str, llm: LLM) -> Crew:
    """Create the CrewAI agents & tasks for one scan."""

    # Agent 1: Security Analyst (The agent using the tool)
    analyst = Agent(
        role="Senior Security Analyst",
        goal=f"Checking the security of {target} and discovering open ports.",
        backstory="You are a skilled cybersecurity expert who tests the security of servers.",
        tools=[run_port_scanner],
        verbose=False,
        allow_delegation=False,
        llm=llm,
    )

    # Agent 2: Report Writer (The agent write the report)
    writer = Agent(
        role="Cybersecurity Report Writer",
        goal="Drafting a security report in simple Sinhala—easily understood by the client—based on the technical data provided by the analyst.",
        backstory="You are a skilled writer who explains complex technical data in simple Sinhala, in a way that is understandable to the average business person.",
        verbose=False,
        allow_delegation=False,
        llm=llm,
    )

    # Task 1
    scan_task = Task(
        description=f'Check which ports are open on the website "{target}". Identify the purpose of these ports.',
        expected_output="A list of scanned ports and a brief technical summary regarding them.",
        agent=analyst,
    )

    # Task 2
    write_task = Task(
        description="Using the data provided by the analyst, draft a compelling security report in Sinhala. Clearly explain the potential risks to the business arising from open ports.",
        expected_output="A standardized Sinhala security report, including a title, findings, and recommendations.",
        agent=writer,
    )

    return Crew(
        agents=[analyst, writer],
        tasks=[scan_task, write_task],
        process=Process.sequential,
    )


# Streamlit User Interface
st.write("Enter your website's domain name below.")
target_url = st.text_input(
    "Domain Name (eg: scanme.nmap.org)", placeholder="example.com"
)

# The part that activates when the button is pressed
if st.button("🔍 Start scanning", type="primary"):

    target_url = normalize_domain(target_url) if target_url else ""

    if not target_url:
        st.warning("Please enter a valid domain name.")
    else:
        # Loading Animation
        with st.spinner(
            f"The CyberGuard AI team is analyzing {target_url}... This will take about a minute ⏳"
        ):
            final_report, used_model, last_error = None, None, None

            # Try each model; if Gemini is overloaded / rate-limited, fall back to the next one.
            # (CrewAI already retries failed LLM calls internally, so no extra retry loop here.)
            for model_name in GEMINI_MODELS:
                try:
                    cyber_crew = build_crew(target_url, make_llm(model_name))
                    final_report = cyber_crew.kickoff()
                    used_model = model_name
                    break
                except Exception as e:
                    last_error = e
                    if not any(code in str(e) for code in RETRYABLE_ERRORS):
                        break  # not a temporary error -> stop and show it
                    time.sleep(2)

        if final_report is not None:
            st.success(f"✅ The test concluded successfully! (model: {used_model})")
            st.divider()

            # Show the final result report
            st.markdown("### 📊 Your Security Report")
            st.markdown(final_report.raw)
        elif any(code in str(last_error) for code in RETRYABLE_ERRORS):
            st.error(
                "⚠️ Gemini is busy or your API quota is used up on all models "
                f"({', '.join(GEMINI_MODELS)}). Try again later, or add other models "
                "to GEMINI_MODELS in your .env file."
            )
            st.caption(f"Details: {last_error}")
        else:
            st.error(f"An error occurred: {last_error}")
