import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Global Map — EpiWatch", page_icon="🌍", layout="wide")

st.markdown("## 🌍 Global Disease Map")
st.caption("Interactive choropleth and risk heatmap powered by Disease.sh + WHO GHO data.")

from utils.data_fetcher import get_all_countries, compute_risk_scores, get_who_country_data

# Controls
col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    map_mode = st.selectbox("Map Mode", ["Total Cases", "Active Cases", "Deaths", "Cases per Million", "Risk Score"])
with col2:
    map_style = st.selectbox("Map Style", ["choropleth", "bubble"])
with col3:
    show_risk = st.checkbox("Show Risk Overlay", value=False)

with st.spinner("Loading global data..."):
    df = get_all_countries()
    risk_df = compute_risk_scores()

if df.empty:
    st.error("Could not load country data. Please check your internet connection.")
    st.stop()

metric_map = {
    "Total Cases": ("cases", "Blues"),
    "Active Cases": ("active", "Oranges"),
    "Deaths": ("deaths", "Reds"),
    "Cases per Million": ("casesPerOneMillion", "Purples"),
    "Risk Score": ("score", "RdYlGn_r"),
}

metric_col, color_scale = metric_map[map_mode]

if map_mode == "Risk Score":
    plot_df = risk_df.copy()
else:
    plot_df = df.copy()

# Choropleth
if map_style == "choropleth":
    fig = px.choropleth(
        plot_df,
        locations="country",
        locationmode="country names",
        color=metric_col if metric_col in plot_df.columns else "cases",
        color_continuous_scale=color_scale,
        title=f"World {map_mode} Heatmap",
        hover_name="country",
        hover_data={metric_col: True} if metric_col in plot_df.columns else {},
        height=520,
    )
else:
    fig = px.scatter_geo(
        plot_df,
        lat="lat", lon="lon",
        size=metric_col if metric_col in plot_df.columns else "cases",
        color=metric_col if metric_col in plot_df.columns else "cases",
        hover_name="country",
        color_continuous_scale=color_scale,
        size_max=40,
        title=f"World {map_mode} Bubble Map",
        height=520,
    )

fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False,
             showcoastlines=True, coastlinecolor="#30363d",
             landcolor="#161b22", oceancolor="#0d1117",
             showocean=True, showlakes=False),
    font_color="#c9d1d9",
    margin=dict(l=0, r=0, t=40, b=0),
    coloraxis_colorbar=dict(title=map_mode, tickfont=dict(color="#c9d1d9")),
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# Top countries table
col_left, col_right = st.columns(2)
with col_left:
    st.markdown("### 🔴 Highest Case Burden")
    top10 = df.nlargest(10, "cases")[["country", "cases", "active", "deaths"]].reset_index(drop=True)
    top10.index += 1
    top10["cases"] = top10["cases"].apply(lambda x: f"{x:,}")
    top10["active"] = top10["active"].apply(lambda x: f"{x:,}")
    top10["deaths"] = top10["deaths"].apply(lambda x: f"{x:,}")
    st.dataframe(top10, use_container_width=True)

with col_right:
    st.markdown("### ⚠️ Highest Risk Scores Today")
    risk_top = risk_df.head(10)[["country", "score", "todayCases"]].reset_index(drop=True)
    risk_top.index += 1
    risk_top["score"] = risk_top["score"].apply(lambda x: f"{x:.1f}")
    risk_top["todayCases"] = risk_top["todayCases"].apply(lambda x: f"{int(x):,}")
    risk_top.columns = ["Country", "Risk Score (0-100)", "New Cases Today"]
    st.dataframe(risk_top, use_container_width=True)

st.divider()

# Country drill-down
st.markdown("### 🔍 Country Deep Dive")
from utils.data_fetcher import get_country_historical
country_list = sorted(df["country"].tolist())
selected = st.selectbox("Select a country", country_list, index=country_list.index("India") if "India" in country_list else 0)

hist = get_country_historical(selected, days=365)
if not hist.empty:
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=hist["date"], y=hist["cases"], name="Total Cases",
                               line=dict(color="#58a6ff", width=2)))
    fig2.add_trace(go.Scatter(x=hist["date"], y=hist["deaths"], name="Deaths",
                               line=dict(color="#f85149", width=2), yaxis="y2"))
    fig2.update_layout(
        title=f"{selected} — 12-Month Case & Death Trend",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        yaxis=dict(title="Cases", gridcolor="#21262d"),
        yaxis2=dict(title="Deaths", overlaying="y", side="right", gridcolor="#21262d"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        height=350,
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info(f"No historical data available for {selected}.")
