import streamlit as st
import json
import requests
from datetime import datetime

st.set_page_config(page_title="AI Analyst — EpiWatch", page_icon="🤖", layout="wide")

st.markdown("## 🤖 AI Epidemiological Analyst")
st.caption("Powered by Cohere AI. Ask questions in plain English — the AI fetches live data and answers.")

from utils.data_fetcher import (get_global_summary, get_top_countries,
                                get_outbreak_alerts, get_india_disease_burden,
                                compute_risk_scores)

COHERE_API_KEY = st.secrets.get("COHERE_API_KEY", "")

if not COHERE_API_KEY:
    st.warning("Add your Cohere API key in Streamlit Secrets.")
    st.code('COHERE_API_KEY = "your-key-here"', language="toml")
    st.info("Get a FREE key at [dashboard.cohere.com](https://dashboard.cohere.com)")
    st.stop()

@st.cache_data(ttl=1800)
def build_context():
    summary  = get_global_summary()
    top10    = get_top_countries(10).to_dict("records")
    alerts   = get_outbreak_alerts()[:5]
    risk_df  = compute_risk_scores()
    top_risk = risk_df.head(5)[["country", "score"]].to_dict("records") if not risk_df.empty else []
    burden   = get_india_disease_burden().to_dict("records")
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        "global_summary": {
            "total_cases": summary.get("cases", 0),
            "active_cases": summary.get("active", 0),
            "deaths": summary.get("deaths", 0),
            "recovered": summary.get("recovered", 0),
            "countries_affected": summary.get("affectedCountries", 0),
        },
        "top_10_countries": top10,
        "top_5_risk_countries": top_risk,
        "active_alerts": [{"title": a["title"], "severity": a["severity"]} for a in alerts],
        "india_burden": burden[:5],
    }

def call_ai(messages, system_prompt):
    try:
        headers = {
            "Authorization": f"Bearer {COHERE_API_KEY}",
            "Content-Type": "application/json",
        }
        cohere_messages = []
        for msg in messages[:-1]:
            cohere_messages.append({
                "role": "USER" if msg["role"] == "user" else "CHATBOT",
                "message": msg["content"]
            })
        payload = {
            "model": "command-r-plus",
            "preamble": system_prompt,
            "chat_history": cohere_messages,
            "message": messages[-1]["content"],
            "max_tokens": 1500,
            "temperature": 0.7,
        }
        r = requests.post("https://api.cohere.ai/v1/chat",
                          json=payload, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()["text"]
        return f"❌ Error {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

def get_system_prompt(context):
    return f"""You are EpiWatch AI — an expert epidemiological analyst embedded in a disease surveillance dashboard.

You have access to LIVE data fetched right now ({context['timestamp']}):

GLOBAL SUMMARY: {json.dumps(context['global_summary'])}
TOP 10 COUNTRIES BY CASES: {json.dumps(context['top_10_countries'])}
TOP 5 RISK COUNTRIES TODAY: {json.dumps(context['top_5_risk_countries'])}
ACTIVE ALERTS: {json.dumps(context['active_alerts'])}
INDIA DISEASE BURDEN: {json.dumps(context['india_burden'])}

INSTRUCTIONS:
- Answer questions about global and India-specific disease surveillance
- Reference the live data above in your answers with actual numbers
- Format responses clearly using markdown
- Keep responses concise (max 400 words)
- You are NOT a medical doctor — findings are for surveillance/research only"""

st.markdown("### 💡 Quick Questions")
quick_prompts = [
    "🌍 What is the current global disease situation?",
    "🇮🇳 Summarize India's top disease burden challenges",
    "🚨 What are the highest-risk outbreak alerts right now?",
    "📈 Which countries show the most concerning trends today?",
    "🦠 Compare COVID, flu, and dengue surveillance data",
    "📋 Generate a weekly epidemiological situation report",
]
cols = st.columns(3)
for i, prompt in enumerate(quick_prompts):
    if cols[i % 3].button(prompt, use_container_width=True):
        st.session_state.setdefault("messages", [])
        st.session_state["pending_prompt"] = prompt[2:].strip()

st.markdown("### 💬 Ask the AI Analyst")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"], avatar="🦠" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

pending    = st.session_state.pop("pending_prompt", None)
user_input = st.chat_input("Ask about any disease, country, trend, or outbreak...")
if pending:
    user_input = pending

if user_input:
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)
    with st.chat_message("assistant", avatar="🦠"):
        with st.spinner("Analyzing live epidemiological data..."):
            context  = build_context()
            system   = get_system_prompt(context)
            response = call_ai(st.session_state["messages"][-10:], system)
        st.markdown(response)
        st.session_state["messages"].append({"role": "assistant", "content": response})

if st.session_state.get("messages"):
    if st.button("🗑️ Clear conversation"):
        st.session_state["messages"] = []
        st.rerun()

st.divider()

st.markdown("### 📄 Auto-Generate Situation Report")
col1, col2 = st.columns([2, 1])
with col1:
    report_type = st.selectbox("Report Type", [
        "Weekly Global Epidemiological Situation Report",
        "India Disease Surveillance Brief",
        "Active Outbreak Risk Assessment",
        "Influenza Season Update",
        "Executive Summary for Health Officials",
    ])
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    gen_report = st.button("🚀 Generate Report", use_container_width=True)

if gen_report:
    with st.spinner(f"Generating {report_type}..."):
        context = build_context()
        system  = get_system_prompt(context)
        prompt  = f"""Generate a professional {report_type} with these sections:
# {report_type}
**Date**: {context['timestamp']}
## Executive Summary
## Key Findings
## High-Priority Situations
## Trends & Projections
## Recommendations
---
*Data: CDC, WHO, Disease.sh, ProMED, HealthMap, IHME India, ECDC*
*EpiWatch AI — For surveillance purposes only.*"""
        report = call_ai([{"role": "user", "content": prompt}], system)
    st.markdown(report)
    st.download_button(
        label="📥 Download Report",
        data=report,
        file_name=f"epiwatch_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
        mime="text/markdown",
    )
