import streamlit as st

st.set_page_config(
    page_title="EpiWatch — Disease Surveillance Dashboard",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background: #0d1117; }
    [data-testid="stSidebar"] * { color: #c9d1d9 !important; }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 16px 20px;
        margin: 4px 0;
    }
    .metric-value { font-size: 2rem; font-weight: 700; }
    .metric-label { font-size: 0.82rem; color: #8b949e; margin-top: 2px; }
    .metric-sublabel { font-size: 0.72rem; color: #6e7681; margin-top: 1px; }
    .section-header { font-size: 1.1rem; font-weight: 600; color: #e6edf3; margin: 1rem 0 0.5rem; border-bottom: 1px solid #30363d; padding-bottom: 6px; }
    .alert-high { border-left: 4px solid #f85149; background: #1a0f0f; padding: 10px 14px; border-radius: 0 8px 8px 0; margin: 6px 0; }
    .alert-med  { border-left: 4px solid #e3b341; background: #1a150a; padding: 10px 14px; border-radius: 0 8px 8px 0; margin: 6px 0; }
    .alert-low  { border-left: 4px solid #3fb950; background: #0d1a0f; padding: 10px 14px; border-radius: 0 8px 8px 0; margin: 6px 0; }
    .divider-label { font-size: 0.75rem; font-weight: 600; color: #8b949e; text-transform: uppercase; letter-spacing: 0.08em; margin: 1rem 0 0.5rem; }
    .stButton > button { background: #238636; color: white; border: none; border-radius: 6px; font-weight: 500; }
    .stButton > button:hover { background: #2ea043; }
</style>
""", unsafe_allow_html=True)

st.sidebar.image("https://img.icons8.com/fluency/48/virus.png", width=40)
st.sidebar.title("EpiWatch")
st.sidebar.caption("Disease Surveillance Intelligence Platform")
st.sidebar.divider()
st.sidebar.markdown("**Navigation**")
st.sidebar.markdown("🏠 Home / Overview")
st.sidebar.markdown("🌍 Global Disease Map")
st.sidebar.markdown("🇮🇳 India Focus")
st.sidebar.markdown("🚨 Outbreak Alerts")
st.sidebar.markdown("🦠 Flu Surveillance")
st.sidebar.markdown("🤖 AI Analyst")
st.sidebar.markdown("🎯 COVID Cycle Analyser")
st.sidebar.markdown("🦟 Dengue Tracker")
st.sidebar.markdown("🦟 Dengue Predictor")
st.sidebar.markdown("🧬 Disease Intelligence")
st.sidebar.divider()
st.sidebar.markdown("**Data Sources**")
sources = ["Disease.sh API", "CDC Open Data", "WHO GHO", "CDC FluView",
           "ProMED RSS", "HealthMap", "IHME India", "ECDC", "UK Gov Health"]
for s in sources:
    st.sidebar.markdown(f"<span style='font-size:0.75rem;color:#3fb950'>● {s}</span>", unsafe_allow_html=True)

st.markdown("## 🦠 EpiWatch — Disease Surveillance Dashboard")
st.caption("Unified disease intelligence from 12 authoritative sources. COVID-19: complete historical record (Jan 2020 – Dec 2023). Dengue, Flu & outbreak alerts: live 2026.")

from utils.data_fetcher import get_global_summary, get_outbreak_alerts, get_top_countries
import pandas as pd

with st.spinner("Fetching live data..."):
    summary = get_global_summary()
    alerts  = get_outbreak_alerts()

st.markdown('<div class="divider-label">COVID-19 — Complete Historical Record (Jan 2020 – Dec 2023)</div>', unsafe_allow_html=True)
col1, col2, col3, col4, col5 = st.columns(5)
cases  = summary.get('cases', 1)
deaths = summary.get('deaths', 0)
cfr    = round((deaths / cases) * 100, 2) if cases > 0 else 0
covid_kpis = [
    ("Total Cases", f"{summary.get('cases', 0):,}", "#58a6ff"),
    ("Total Deaths", f"{summary.get('deaths', 0):,}", "#f85149"),
    ("Case Fatality Rate", f"{cfr}%", "#e3b341"),
    ("Most Affected", "USA & India", "#ff7b72"),
    ("Countries Affected", f"{summary.get('affectedCountries', 0):,}", "#a371f7"),
]
for col, (label, value, color) in zip([col1,col2,col3,col4,col5], covid_kpis):
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:{color}">{value}</div>
            <div class="metric-label">{label}</div>
            <div class="metric-sublabel">COVID-19 historical</div>
        </div>""", unsafe_allow_html=True)

st.markdown('<div class="divider-label">🦟 Dengue — Live 2026 Surveillance</div>', unsafe_allow_html=True)

from utils.data_fetcher import get_dengue_summary
with st.spinner("Fetching live dengue data..."):
    dengue = get_dengue_summary()

d1, d2, d3, d4 = st.columns(4)
dengue_kpis = [
    ("Dengue Alerts (Live)", str(dengue.get("active_alerts", 0)), "#f85149"),
    ("Countries Reporting", str(dengue.get("countries_reporting", 0)), "#e3b341"),
    ("High Risk Regions", str(dengue.get("high_risk", 0)), "#ff7b72"),
    ("Data Updated", dengue.get("last_updated", "Live"), "#3fb950"),
]
for col, (label, value, color) in zip([d1,d2,d3,d4], dengue_kpis):
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:{color}">{value}</div>
            <div class="metric-label">{label}</div>
            <div class="metric-sublabel">Live 2026</div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown('<div class="section-header">📊 Top 10 Countries by COVID Cases</div>', unsafe_allow_html=True)
    top_df = get_top_countries(10)
    if not top_df.empty:
        import plotly.express as px
        fig = px.bar(
            top_df, x="country", y="cases",
            color="deaths", color_continuous_scale="Reds",
            title="Top 10 Countries — Total COVID Cases (2020-2023)",
            labels={"cases": "Total Cases", "country": "Country"},
            height=350,
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#c9d1d9", title_font_size=13,
        )
        st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.markdown('<div class="section-header">🚨 Live Alerts (Dengue + All Diseases)</div>', unsafe_allow_html=True)
    dengue_alerts = [a for a in alerts if "dengue" in a.get("title","").lower()]
    other_alerts  = [a for a in alerts if "dengue" not in a.get("title","").lower()]
    display_alerts = dengue_alerts + other_alerts

    for alert in display_alerts[:6]:
        severity  = alert.get("severity", "low")
        css_class = {"high": "alert-high", "medium": "alert-med"}.get(severity, "alert-low")
        is_dengue = "dengue" in alert.get("title","").lower()
        badge = '<span style="background:#f85149;color:white;font-size:0.65rem;padding:1px 5px;border-radius:4px;margin-right:4px">DENGUE</span>' if is_dengue else ""
        st.markdown(f"""
        <div class="{css_class}">
            {badge}<strong style="font-size:0.8rem">{alert.get('title','')[:60]}...</strong><br>
            <span style="font-size:0.72rem;color:#8b949e">{alert.get('source','')} · {str(alert.get('date',''))[:16]}</span>
        </div>""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#8b949e;font-size:0.75rem;">
EpiWatch | Disease Surveillance Intelligence | CDC · WHO · Disease.sh · ProMED · HealthMap · IHME · ECDC · UK Gov
</div>""", unsafe_allow_html=True)
