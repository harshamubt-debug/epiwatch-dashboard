import streamlit as st

st.set_page_config(
    page_title="EpiWatch — Disease Surveillance Dashboard",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
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
    .metric-value { font-size: 2rem; font-weight: 700; color: #58a6ff; }
    .metric-label { font-size: 0.85rem; color: #8b949e; margin-top: 2px; }
    .alert-high { border-left: 4px solid #f85149; background: #1a0f0f; padding: 10px 14px; border-radius: 0 8px 8px 0; margin: 6px 0; }
    .alert-med  { border-left: 4px solid #e3b341; background: #1a150a; padding: 10px 14px; border-radius: 0 8px 8px 0; margin: 6px 0; }
    .alert-low  { border-left: 4px solid #3fb950; background: #0d1a0f; padding: 10px 14px; border-radius: 0 8px 8px 0; margin: 6px 0; }
    .section-header { font-size: 1.1rem; font-weight: 600; color: #e6edf3; margin: 1rem 0 0.5rem; border-bottom: 1px solid #30363d; padding-bottom: 6px; }
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
st.sidebar.markdown("🇮🇳 India Health Dashboard")
st.sidebar.markdown("🚨 Outbreak Alerts")
st.sidebar.markdown("📈 Forecasting & Trends")
st.sidebar.markdown("🤖 AI Analyst")")

st.sidebar.divider()
st.sidebar.markdown("**Data Sources**")
sources = ["Disease.sh API", "CDC Open Data", "WHO GHO", "CDC FluView", "ProMED RSS", "HealthMap", "IHME India", "ECDC", "UK Gov Health"]
for s in sources:
    st.sidebar.markdown(f"<span style='font-size:0.75rem;color:#3fb950'>● {s}</span>", unsafe_allow_html=True)

# ── MAIN CONTENT ──────────────────────────────────────────────────────────────
st.markdown("## 🦠 EpiWatch — Disease Surveillance Dashboard")
st.caption("Real-time global health intelligence aggregated from 9 authoritative public health sources.")

from utils.data_fetcher import get_global_summary, get_outbreak_alerts
import pandas as pd

with st.spinner("Fetching live data..."):
    summary = get_global_summary()
    alerts  = get_outbreak_alerts()

# KPI Row
col1, col2, col3, col4, col5 = st.columns(5)
kpis = [
    ("Total Cases (COVID)", f"{summary.get('cases', 0):,}", "#58a6ff"),
    ("Active Cases",        f"{summary.get('active', 0):,}", "#e3b341"),
    ("Deaths (Global)",     f"{summary.get('deaths', 0):,}", "#f85149"),
    ("Recovered",           f"{summary.get('recovered', 0):,}", "#3fb950"),
    ("Countries Affected",  f"{summary.get('affectedCountries', 0):,}", "#a371f7"),
]
for col, (label, value, color) in zip([col1,col2,col3,col4,col5], kpis):
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:{color}">{value}</div>
            <div class="metric-label">{label}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown('<div class="section-header">📊 Quick Global Stats</div>', unsafe_allow_html=True)
    from utils.data_fetcher import get_top_countries
    top_df = get_top_countries(10)
    if not top_df.empty:
        import plotly.express as px
        fig = px.bar(
            top_df, x="country", y="cases",
            color="deaths",
            color_continuous_scale="Reds",
            title="Top 10 Countries by Total Cases",
            labels={"cases": "Total Cases", "country": "Country"},
            height=350,
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#c9d1d9",
            title_font_size=13,
        )
        st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.markdown('<div class="section-header">🚨 Live Alerts</div>', unsafe_allow_html=True)
    if alerts:
        for alert in alerts[:6]:
            severity = alert.get("severity", "low")
            css_class = {"high": "alert-high", "medium": "alert-med"}.get(severity, "alert-low")
            st.markdown(f"""
            <div class="{css_class}">
                <strong style="font-size:0.8rem">{alert.get('title','')[:60]}...</strong><br>
                <span style="font-size:0.72rem;color:#8b949e">{alert.get('source','')} · {alert.get('date','')}</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No active alerts fetched. Check API connectivity.")

st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#8b949e;font-size:0.75rem;">
EpiWatch | Built for Disease Surveillance Hackathon | Data from CDC, WHO, Disease.sh, ProMED, HealthMap, IHME, ECDC, UK Gov
</div>""", unsafe_allow_html=True)
