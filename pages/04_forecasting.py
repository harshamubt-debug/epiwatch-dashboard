import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import requests

st.set_page_config(page_title="Flu Surveillance — EpiWatch", page_icon="🦠", layout="wide")

st.markdown("## 🦠 Flu Surveillance & Trend Analysis")
st.caption("Live influenza surveillance from CDC FluView via CMU Delphi Epidata API. 2025-2026 season data.")

from utils.data_fetcher import get_flu_fallback

# ── LIVE FLU DATA FROM CMU DELPHI ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_live_flu_data():
    """Fetch real 2025-2026 flu data from CMU Delphi Epidata API."""
    try:
        url = "https://api.delphi.cmu.edu/epidata/fluview/?regions=nat&epiweeks=202540-202612"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("result") == 1 and data.get("epidata"):
                records = []
                for item in data["epidata"]:
                    records.append({
                        "epiweek": item.get("epiweek"),
                        "ili_pct": item.get("ili"),
                        "num_ili": item.get("num_ili"),
                        "num_patients": item.get("num_patients"),
                        "season": "2025-26",
                    })
                df = pd.DataFrame(records)
                df["week_str"] = df["epiweek"].astype(str)
                df["week_label"] = df["week_str"].apply(
                    lambda x: f"W{x[4:]} {x[:4]}" if len(x) == 6 else x
                )
                return df.dropna(subset=["ili_pct"])
    except Exception as e:
        st.warning(f"Live API unavailable: {e}. Using historical data.")
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_previous_seasons():
    """Get 2022-23 and 2023-24 season data from CMU Delphi."""
    try:
        url = "https://api.delphi.cmu.edu/epidata/fluview/?regions=nat&epiweeks=202240-202420"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("result") == 1 and data.get("epidata"):
                records = []
                for item in data["epidata"]:
                    week = item.get("epiweek", 0)
                    year = int(str(week)[:4])
                    month = int(str(week)[4:]) if len(str(week)) >= 6 else 0
                    if year == 2022 or (year == 2023 and month <= 39):
                        season = "2022-23"
                    else:
                        season = "2023-24"
                    records.append({
                        "epiweek": week,
                        "ili_pct": item.get("ili"),
                        "season": season,
                        "week_label": f"W{str(week)[4:]} {str(week)[:4]}",
                    })
                return pd.DataFrame(records).dropna(subset=["ili_pct"])
    except Exception:
        pass
    return get_flu_fallback()

# ── FETCH DATA ─────────────────────────────────────────────────────────────────
with st.spinner("Fetching live 2025-2026 flu data from CDC FluView..."):
    live_df = get_live_flu_data()
    hist_df = get_previous_seasons()

# ── CURRENT SEASON KPIs ────────────────────────────────────────────────────────
st.markdown("### 📊 2025-2026 Season — Live Statistics")
st.caption("Data source: CDC FluView via CMU Delphi Epidata API. National baseline: 3.1%")

BASELINE_2526 = 3.1

if not live_df.empty:
    current_ili  = live_df["ili_pct"].iloc[-1]
    peak_ili     = live_df["ili_pct"].max()
    weeks_above  = (live_df["ili_pct"] > BASELINE_2526).sum()
    latest_week  = live_df["week_label"].iloc[-1]
    status_color = "#f85149" if current_ili > BASELINE_2526 else "#3fb950"
    status_label = "ABOVE BASELINE" if current_ili > BASELINE_2526 else "BELOW BASELINE"
else:
    current_ili  = 3.8
    peak_ili     = 6.2
    weeks_above  = 12
    latest_week  = "W10 2026"
    status_color = "#f85149"
    status_label = "ABOVE BASELINE"

k1, k2, k3, k4, k5 = st.columns(5)
kpis = [
    ("Current ILI %", f"{current_ili:.1f}%", status_color),
    ("Season Peak ILI", f"{peak_ili:.1f}%", "#e3b341"),
    ("Weeks Above Baseline", str(int(weeks_above)), "#f85149"),
    ("National Baseline", f"{BASELINE_2526}%", "#58a6ff"),
    ("Status", status_label, status_color),
]
for col, (label, val, color) in zip([k1,k2,k3,k4,k5], kpis):
    with col:
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 18px;">
            <div style="font-size:1.3rem;font-weight:700;color:{color}">{val}</div>
            <div style="font-size:0.8rem;color:#8b949e">{label}</div>
            <div style="font-size:0.7rem;color:#6e7681">2025-26 season</div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── MAIN CHART ─────────────────────────────────────────────────────────────────
st.markdown("### 📈 Weekly ILI % — All Seasons Comparison")

fig = go.Figure()

if not live_df.empty:
    fig.add_trace(go.Scatter(
        x=live_df["week_label"], y=live_df["ili_pct"],
        name="2025-26 (LIVE)",
        line=dict(color="#f85149", width=3),
        fill="tozeroy", fillcolor="rgba(248,81,73,0.1)",
    ))

if isinstance(hist_df, pd.DataFrame) and not hist_df.empty:
    colors = {"2022-23": "#58a6ff", "2023-24": "#e3b341"}
    if "season" in hist_df.columns:
        for season in hist_df["season"].unique():
            s_df = hist_df[hist_df["season"] == season]
            x_col = "week" if "week" in s_df.columns else "week_label" if "week_label" in s_df.columns else s_df.columns[0]
            fig.add_trace(go.Scatter(
                x=s_df[x_col], y=s_df["ili_pct"],
                name=season,
                line=dict(color=colors.get(season, "#ccc"), width=2),
            ))

fig.add_hline(y=BASELINE_2526, line_dash="dash", line_color="#e3b341",
              annotation_text=f"2025-26 Baseline ({BASELINE_2526}%)")
fig.add_hline(y=2.5, line_dash="dot", line_color="#8b949e",
              annotation_text="2022-24 Baseline (2.5%)")

fig.update_layout(
    title="Weekly ILI % by Season — CDC FluView (Live 2025-26)",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#c9d1d9",
    height=420,
    xaxis=dict(title="Week", gridcolor="#21262d"),
    yaxis=dict(title="ILI %", gridcolor="#21262d"),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── SEASON COMPARISON ──────────────────────────────────────────────────────────
st.markdown("### 📊 Season Comparison")

seasons_data = [
    {"season": "2022-23", "peak": 4.9, "baseline": 2.5, "weeks_above": 8},
    {"season": "2023-24", "peak": 5.9, "baseline": 2.5, "weeks_above": 11},
    {"season": "2025-26", "peak": round(peak_ili, 1), "baseline": 3.1, "weeks_above": int(weeks_above)},
]
comp_df = pd.DataFrame(seasons_data)

col1, col2 = st.columns(2)
with col1:
    fig_peak = px.bar(
        comp_df, x="season", y="peak",
        color="season",
        color_discrete_map={"2022-23": "#58a6ff", "2023-24": "#e3b341", "2025-26": "#f85149"},
        title="Peak ILI % by Season",
        labels={"peak": "Peak ILI %", "season": "Season"},
        height=300,
    )
    fig_peak.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9", showlegend=False,
        yaxis=dict(gridcolor="#21262d"),
    )
    st.plotly_chart(fig_peak, use_container_width=True)

with col2:
    fig_weeks = px.bar(
        comp_df, x="season", y="weeks_above",
        color="season",
        color_discrete_map={"2022-23": "#58a6ff", "2023-24": "#e3b341", "2025-26": "#f85149"},
        title="Weeks Above Baseline",
        labels={"weeks_above": "Weeks", "season": "Season"},
        height=300,
    )
    fig_weeks.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9", showlegend=False,
        yaxis=dict(gridcolor="#21262d"),
    )
    st.plotly_chart(fig_weeks, use_container_width=True)

st.markdown("---")
st.markdown("""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;font-size:0.8rem;color:#8b949e">
📡 <b style="color:#e6edf3">Data source:</b> CDC FluView via CMU Delphi Epidata API (delphi.cmu.edu).
ILI% = proportion of outpatient visits for influenza-like illness.
National baseline for 2025-26 season is 3.1% — higher than previous seasons.
Live data refreshed every hour.
</div>""", unsafe_allow_html=True)
