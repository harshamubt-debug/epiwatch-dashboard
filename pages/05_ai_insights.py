import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(page_title="AI Analyst — EpiWatch", page_icon="🤖", layout="wide")

st.markdown("## 🤖 AI Epidemiological Analyst")
st.caption("Powered by Claude AI. Ask questions in plain English — the AI fetches live data and answers.")

from utils.data_fetcher import (get_global_summary, get_all_countries, get_top_countries,
                                 get_outbreak_alerts, get_india_state_data,
                                 get_india_disease_burden, compute_risk_scores)

# ── API KEY SETUP ──────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    st.warning("⚠️ Set `ANTHROPIC_API_KEY` in your environment or Streamlit secrets to enable AI features.")
    st.code('echo "ANTHROPIC_API_KEY=your_key_here" >> .env', language="bash")
    st.info("Add to `.streamlit/secrets.toml`:\n```\nANTHROPIC_API_KEY = 'sk-ant-...'\n```")
    ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "") if hasattr(st, "secrets") else ""

# ── SYSTEM CONTEXT BUILDER ─────────────────────────────────────────────────────
@st.cache_data(ttl=1800)
def build_context():
    """Build a data context snapshot to inject into AI prompts."""
    summary    = get_global_summary()
    top10      = get_top_countries(10).to_dict("records")
    alerts     = get_outbreak_alerts()[:5]
    risk_df    = compute_risk_scores()
    top_risk   = risk_df.head(5)[["country", "score"]].to_dict("records") if not risk_df.empty else []
    burden_df  = get_india_disease_burden()
    burden     = burden_df.to_dict("records") if not burden_df.empty else []

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        "global_summary": {
            "total_cases": summary.get("cases", 0),
            "active_cases": summary.get("active", 0),
            "deaths": summary.get("deaths", 0),
            "recovered": summary.get("recovered", 0),
            "countries_affected": summary.get("affectedCountries", 0),
        },
        "top_10_countries_by_cases": top10,
        "top_5_risk_countries_today": top_risk,
        "active_alerts": [{"title": a["title"], "severity": a["severity"], "source": a["source"]} for a in alerts],
        "india_disease_burden_top5": burden[:5],
    }

def call_claude(messages, system_prompt):
    """Call Anthropic Claude API."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1500,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text
    except ImportError:
        return call_claude_requests(messages, system_prompt)
    except Exception as e:
        return f"❌ API Error: {str(e)}"

def call_claude_requests(messages, system_prompt):
    """Fallback using requests library."""
    import requests
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-opus-4-5",
        "max_tokens": 1500,
        "system": system_prompt,
        "messages": messages,
    }
    r = requests.post("https://api.anthropic.com/v1/messages",
                      json=payload, headers=headers, timeout=30)
    if r.status_code == 200:
        return r.json()["content"][0]["text"]
    return f"❌ API Error {r.status_code}: {r.text[:200]}"

# ── SYSTEM PROMPT ──────────────────────────────────────────────────────────────
def get_system_prompt(context):
    return f"""You are EpiWatch AI — an expert epidemiological analyst embedded in a disease surveillance dashboard.

You have access to LIVE data fetched right now ({context['timestamp']}):

GLOBAL SUMMARY:
{json.dumps(context['global_summary'], indent=2)}

TOP 10 COUNTRIES BY CASES:
{json.dumps(context['top_10_countries_by_cases'], indent=2)}

TOP 5 HIGHEST RISK COUNTRIES (today):
{json.dumps(context['top_5_risk_countries_today'], indent=2)}

ACTIVE ALERTS:
{json.dumps(context['active_alerts'], indent=2)}

INDIA DISEASE BURDEN (IHME data):
{json.dumps(context['india_disease_burden_top5'], indent=2)}

AVAILABLE DATA SOURCES: CDC Open Data, Disease.sh, WHO GHO, CDC FluView, ProMED, HealthMap, IHME India GHDx, ECDC, UK Gov Health.

INSTRUCTIONS:
- Answer questions about global and India-specific disease surveillance
- Reference the live data above in your answers
- Be precise with numbers — use the actual figures from the data
- Flag data limitations honestly
- For forecasting questions, explain methodology clearly
- Format responses with clear sections using markdown
- Keep responses concise but complete (max ~400 words)
- Suggest follow-up questions when relevant
- You are NOT a medical doctor — always note that findings are for surveillance/research only"""

# ── QUICK PROMPTS ──────────────────────────────────────────────────────────────
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

# ── CHAT INTERFACE ─────────────────────────────────────────────────────────────
st.markdown("### 💬 Ask the AI Analyst")

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Render history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"],
                          avatar="🦠" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# Handle quick prompt injection
pending = st.session_state.pop("pending_prompt", None)

# Input
user_input = st.chat_input("Ask about any disease, country, trend, or outbreak...")
if pending:
    user_input = pending

if user_input:
    if not ANTHROPIC_API_KEY:
        st.error("Please set your ANTHROPIC_API_KEY to use the AI analyst.")
    else:
        st.session_state["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar="🦠"):
            with st.spinner("Analyzing live epidemiological data..."):
                context = build_context()
                system  = get_system_prompt(context)
                api_messages = st.session_state["messages"][-10:]  # Last 10 for context window
                response = call_claude(api_messages, system)
            st.markdown(response)
            st.session_state["messages"].append({"role": "assistant", "content": response})

if st.session_state.get("messages"):
    if st.button("🗑️ Clear conversation"):
        st.session_state["messages"] = []
        st.rerun()

st.divider()

# ── SITUATION REPORT GENERATOR ─────────────────────────────────────────────────
st.markdown("### 📄 Auto-Generate Situation Report")
st.caption("One-click AI-written epidemiological brief based on current live data.")

col_rep1, col_rep2 = st.columns([2, 1])
with col_rep1:
    report_type = st.selectbox("Report Type", [
        "Weekly Global Epidemiological Situation Report",
        "India Disease Surveillance Brief",
        "Active Outbreak Risk Assessment",
        "Influenza Season Update",
        "Executive Summary for Health Officials",
    ])
with col_rep2:
    st.markdown("<br>", unsafe_allow_html=True)
    gen_report = st.button("🚀 Generate Report", use_container_width=True)

if gen_report:
    if not ANTHROPIC_API_KEY:
        st.error("API key required.")
    else:
        with st.spinner(f"Generating {report_type}..."):
            context = build_context()
            system  = get_system_prompt(context)
            report_prompt = f"""Generate a professional {report_type} based on the live data you have access to.

Structure it as:
# {report_type}
**Date**: {context['timestamp']}

## Executive Summary
[2-3 sentence overview]

## Key Findings
[Bullet points with specific numbers]

## High-Priority Situations
[Most urgent items with data]

## Trends & Projections
[What to watch]

## Recommendations
[Actionable surveillance priorities]

---
*Data sources: CDC, WHO GHO, Disease.sh, ProMED, HealthMap, IHME India GHDx, ECDC*
*Generated by EpiWatch AI Analyst — For surveillance purposes only. Not for clinical use.*"""

            report = call_claude(
                [{"role": "user", "content": report_prompt}],
                system
            )

        st.markdown(report)

        # Download button
        st.download_button(
            label="📥 Download Report (Markdown)",
            data=report,
            file_name=f"epiwatch_report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
        )
