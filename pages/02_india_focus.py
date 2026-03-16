import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json

st.set_page_config(page_title="India Dashboard — EpiWatch", page_icon="🇮🇳", layout="wide")

st.markdown("## 🇮🇳 India Health Intelligence Dashboard")
st.caption("State-level analysis powered by Disease.sh + IHME GHDx India data.")

from utils.data_fetcher import get_india_state_data, get_india_disease_burden, get_country_historical

with st.spinner("Loading India data..."):
    state_df, india_national = get_india_state_data()
    burden_df = get_india_disease_burden()
    india_hist = get_country_historical("India", days=730)

# National KPIs
st.markdown("### 📊 National Overview")
k1, k2, k3, k4 = st.columns(4)
kpis = [
    ("Total Cases", f"{india_national.get('cases', 44690000):,}", "#58a6ff"),
    ("Active Cases", f"{india_national.get('active', 3400):,}", "#e3b341"),
    ("Total Deaths", f"{india_national.get('deaths', 530779):,}", "#f85149"),
    ("Recovered", f"{india_national.get('recovered', 44000000):,}", "#3fb950"),
]
for col, (label, val, color) in zip([k1,k2,k3,k4], kpis):
    with col:
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 18px;">
            <div style="font-size:1.7rem;font-weight:700;color:{color}">{val}</div>
            <div style="font-size:0.82rem;color:#8b949e">{label}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown("### 🗺️ State-Level Case Distribution")

    # Simple bar chart for states (choropleth requires geojson which is a large file)
    fig_states = px.bar(
        state_df.sort_values("cases", ascending=True).tail(15),
        x="cases", y="state",
        orientation="h",
        color="cases_per_million",
        color_continuous_scale="Blues",
        title="Top States by Total Cases",
        labels={"cases": "Total Cases", "state": "State", "cases_per_million": "Cases/Million"},
        height=420,
    )
    fig_states.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        title_font_size=13,
        xaxis=dict(gridcolor="#21262d"),
        yaxis=dict(gridcolor="#21262d"),
        coloraxis_colorbar=dict(tickfont=dict(color="#c9d1d9")),
    )
    st.plotly_chart(fig_states, use_container_width=True)

with col_right:
    st.markdown("### 📋 State Summary Table")
    display_df = state_df.sort_values("cases", ascending=False).copy()
    display_df["cases"] = display_df["cases"].apply(lambda x: f"{x:,}")
    display_df["cases_per_million"] = display_df["cases_per_million"].apply(lambda x: f"{x:,}")
    display_df.columns = ["State", "Total Cases", "Population", "Cases/Million"]
    st.dataframe(display_df[["State", "Total Cases", "Cases/Million"]], use_container_width=True, height=400)

st.markdown("---")

# India trend
st.markdown("### 📈 India COVID-19 Timeline")
if not india_hist.empty:
    tab1, tab2 = st.tabs(["📊 Case Trend", "📉 Daily New Cases"])
    with tab1:
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=india_hist["date"], y=india_hist["cases"],
            name="Cumulative Cases", line=dict(color="#58a6ff", width=2),
            fill="tozeroy", fillcolor="rgba(88,166,255,0.1)"
        ))
        fig_trend.add_trace(go.Scatter(
            x=india_hist["date"], y=india_hist["deaths"],
            name="Cumulative Deaths", line=dict(color="#f85149", width=2),
            yaxis="y2"
        ))
        fig_trend.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#c9d1d9", height=300,
            yaxis=dict(title="Cases", gridcolor="#21262d"),
            yaxis2=dict(title="Deaths", overlaying="y", side="right"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    with tab2:
        india_hist["daily_cases"] = india_hist["cases"].diff().clip(lower=0)
        india_hist["7day_avg"] = india_hist["daily_cases"].rolling(7).mean()
        fig_daily = go.Figure()
        fig_daily.add_trace(go.Bar(
            x=india_hist["date"], y=india_hist["daily_cases"],
            name="Daily Cases", marker_color="rgba(88,166,255,0.4)"
        ))
        fig_daily.add_trace(go.Scatter(
            x=india_hist["date"], y=india_hist["7day_avg"],
            name="7-Day Average", line=dict(color="#e3b341", width=2)
        ))
        fig_daily.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#c9d1d9", height=300,
            yaxis=dict(gridcolor="#21262d"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_daily, use_container_width=True)

st.markdown("---")

# Disease burden
st.markdown("### ⚕️ India Disease Burden (IHME GHDx Data)")
col_b1, col_b2 = st.columns(2)

with col_b1:
    category = st.selectbox("Filter by Category", ["All"] + burden_df["Category"].unique().tolist())
    filtered = burden_df if category == "All" else burden_df[burden_df["Category"] == category]

    fig_burden = px.bar(
        filtered.sort_values("Deaths_per_100k", ascending=True),
        x="Deaths_per_100k", y="Disease", orientation="h",
        color="Category",
        color_discrete_map={
            "NCD": "#58a6ff", "Infectious": "#f85149",
            "Neonatal": "#e3b341", "Injury": "#a371f7",
            "Mental": "#3fb950", "Nutritional": "#79c0ff"
        },
        title="Deaths per 100,000 population",
        height=400,
    )
    fig_burden.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9", title_font_size=12,
        xaxis=dict(gridcolor="#21262d"),
        showlegend=False,
    )
    st.plotly_chart(fig_burden, use_container_width=True)

with col_b2:
    fig_daly = px.treemap(
        burden_df, path=["Category", "Disease"],
        values="DALYs_per_100k",
        color="DALYs_per_100k",
        color_continuous_scale="Blues",
        title="DALYs per 100,000 — Treemap View",
        height=400,
    )
    fig_daly.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        title_font_size=12,
    )
    st.plotly_chart(fig_daly, use_container_width=True)

st.info("📌 **Data source**: IHME Global Health Data Exchange (GHDx) — India 2019 estimates. State-level proportions are modelled from national totals using IHME GBD India regional weights.")
