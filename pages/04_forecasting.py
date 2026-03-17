import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

st.set_page_config(page_title="Flu Surveillance — EpiWatch", page_icon="🦠", layout="wide")

st.markdown("## 🦠 Flu Surveillance & Trend Analysis")
st.caption("Influenza surveillance data from CDC FluView. Weekly ILI trends and seasonal comparisons.")

from utils.data_fetcher import get_flu_fallback, get_all_countries, get_country_historical

# ── FLU SURVEILLANCE ───────────────────────────────────────────────────────────
st.markdown("### 🤧 Influenza-Like Illness (ILI) Surveillance")
st.caption("CDC FluView data — weekly ILI percentage by season. Baseline threshold = 2.5%")

with st.spinner("Loading flu surveillance data..."):
    flu_df = get_flu_fallback()

if not flu_df.empty:
    # Season stats
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    for col, season in zip([col_s1, col_s2], flu_df["season"].unique()):
        s_df = flu_df[flu_df["season"] == season]
        peak = s_df["ili_pct"].max()
        weeks_above = (s_df["ili_pct"] > 2.5).sum()
        with col:
            st.markdown(f"""
            <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 18px;">
                <div style="font-size:1.4rem;font-weight:700;color:#58a6ff">{peak:.1f}%</div>
                <div style="font-size:0.82rem;color:#8b949e">{season} Peak ILI %</div>
            </div>""", unsafe_allow_html=True)
        with [col_s3, col_s4][list(flu_df["season"].unique()).index(season)]:
            st.markdown(f"""
            <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 18px;">
                <div style="font-size:1.4rem;font-weight:700;color:#e3b341">{weeks_above}</div>
                <div style="font-size:0.82rem;color:#8b949e">{season} Weeks Above Baseline</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Main ILI chart
    fig_flu = go.Figure()
    colors = {"2022-23": "#58a6ff", "2023-24": "#e3b341"}
    for season in flu_df["season"].unique():
        s_df = flu_df[flu_df["season"] == season]
        fig_flu.add_trace(go.Scatter(
            x=s_df["week"], y=s_df["ili_pct"],
            name=season,
            line=dict(color=colors.get(season, "#ccc"), width=2),
            fill="tozeroy" if season == "2023-24" else None,
            fillcolor="rgba(227,179,65,0.1)" if season == "2023-24" else None,
        ))
    fig_flu.add_hline(y=2.5, line_dash="dash", line_color="#f85149",
                      annotation_text="Baseline threshold (2.5%)")
    fig_flu.update_layout(
        title="Weekly ILI % by Season — CDC FluView",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        height=400,
        xaxis=dict(title="Week", gridcolor="#21262d"),
        yaxis=dict(title="ILI %", gridcolor="#21262d"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_flu, use_container_width=True)

    st.markdown("---")

    # Season comparison bar
    st.markdown("### 📊 Season Comparison")
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        season_summary = []
        for season in flu_df["season"].unique():
            s_df = flu_df[flu_df["season"] == season]
            season_summary.append({
                "season": season,
                "peak_ili": round(s_df["ili_pct"].max(), 2),
                "avg_ili": round(s_df["ili_pct"].mean(), 2),
                "weeks_above": int((s_df["ili_pct"] > 2.5).sum()),
            })
        summary_df = pd.DataFrame(season_summary)
        fig_comp = px.bar(
            summary_df, x="season", y="peak_ili",
            color="season",
            color_discrete_map={"2022-23": "#58a6ff", "2023-24": "#e3b341"},
            title="Peak ILI % by Season",
            labels={"peak_ili": "Peak ILI %", "season": "Season"},
            height=300,
        )
        fig_comp.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#c9d1d9",
            showlegend=False,
            yaxis=dict(gridcolor="#21262d"),
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    with col_c2:
        fig_weeks = px.bar(
            summary_df, x="season", y="weeks_above",
            color="season",
            color_discrete_map={"2022-23": "#58a6ff", "2023-24": "#e3b341"},
            title="Weeks Above Baseline Threshold",
            labels={"weeks_above": "Weeks", "season": "Season"},
            height=300,
        )
        fig_weeks.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#c9d1d9",
            showlegend=False,
            yaxis=dict(gridcolor="#21262d"),
        )
        st.plotly_chart(fig_weeks, use_container_width=True)

st.markdown("---")

# ── MULTI COUNTRY COVID TREND ──────────────────────────────────────────────────
st.markdown("### 🌍 Multi-Country COVID Trend Comparison")
st.caption("Historical COVID-19 case trends (Jan 2020 – Dec 2023). Compare up to 5 countries.")

countries = st.multiselect(
    "Select countries to compare",
    ["India", "USA", "Brazil", "UK", "France", "Germany", "Russia", "Italy", "Spain", "Japan"],
    default=["India", "USA", "Brazil"]
)

metric_comp = st.radio("Metric", ["cases", "deaths"], horizontal=True)

if countries:
    fig_comp2 = go.Figure()
    palette = ["#58a6ff", "#e3b341", "#f85149", "#3fb950", "#a371f7"]
    for i, country in enumerate(countries):
        with st.spinner(f"Loading {country}..."):
            h = get_country_historical(country, days=365)
        if not h.empty:
            fig_comp2.add_trace(go.Scatter(
                x=h["date"], y=h[metric_comp],
                name=country,
                line=dict(color=palette[i % len(palette)], width=2)
            ))
    fig_comp2.update_layout(
        title=f"Cumulative {metric_comp.title()} Comparison (2020-2023)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        height=380,
        xaxis=dict(gridcolor="#21262d"),
        yaxis=dict(title=metric_comp.title(), gridcolor="#21262d"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_comp2, use_container_width=True)

st.markdown("---")
st.info("📌 For live disease forecasting see the **Dengue Predictor** page — uses real 2026 seasonal data.")
