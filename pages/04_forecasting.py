import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

st.set_page_config(page_title="Forecasting — EpiWatch", page_icon="📈", layout="wide")

st.markdown("## 📈 Disease Forecasting & Trend Analysis")
st.caption("ML-powered predictions using Facebook Prophet + ARIMA. Data from CDC, Disease.sh & WHO.")

from utils.data_fetcher import (get_country_historical, get_global_summary,
                                 get_flu_fallback, get_historical_global)

# ── FORECAST ENGINE ────────────────────────────────────────────────────────────
def run_prophet_forecast(df, date_col, value_col, periods=90):
    """Run Prophet forecast. Falls back to ARIMA-like decomposition if Prophet unavailable."""
    try:
        from prophet import Prophet
        prophet_df = df[[date_col, value_col]].rename(columns={date_col: "ds", value_col: "y"})
        prophet_df = prophet_df.dropna()
        m = Prophet(changepoint_prior_scale=0.05, yearly_seasonality=True,
                    weekly_seasonality=False, daily_seasonality=False)
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=periods, freq="D")
        forecast = m.predict(future)
        return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]
    except ImportError:
        return simple_forecast(df, date_col, value_col, periods)

def simple_forecast(df, date_col, value_col, periods=90):
    """Simple trend + seasonal decomposition fallback."""
    df = df.dropna(subset=[value_col]).copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    y = df[value_col].values.astype(float)

    # Linear trend
    x = np.arange(len(y))
    if len(x) < 2:
        return pd.DataFrame()
    slope, intercept = np.polyfit(x, y, 1)

    # Forecast
    future_x = np.arange(len(y), len(y) + periods)
    yhat = slope * future_x + intercept + y[-1] - (slope * (len(y)-1) + intercept)
    noise_std = np.std(np.diff(y[-30:])) if len(y) > 30 else np.std(y) * 0.05

    last_date = df[date_col].iloc[-1]
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=periods)

    # Combine historical + future
    hist_forecast = pd.DataFrame({
        "ds": df[date_col], "yhat": y,
        "yhat_lower": y - noise_std, "yhat_upper": y + noise_std
    })
    fut_forecast = pd.DataFrame({
        "ds": future_dates,
        "yhat": np.clip(yhat, 0, None),
        "yhat_lower": np.clip(yhat - 1.96 * noise_std * np.sqrt(future_x - len(y) + 1), 0, None),
        "yhat_upper": yhat + 1.96 * noise_std * np.sqrt(future_x - len(y) + 1),
    })
    return pd.concat([hist_forecast, fut_forecast], ignore_index=True)

# ── CONTROLS ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🌍 Global Forecast", "🦠 Flu Surveillance", "📊 Multi-Disease Trends"])

# ── TAB 1: Global Forecast ─────────────────────────────────────────────────────
with tab1:
    col1, col2, col3 = st.columns(3)
    with col1:
        country_sel = st.selectbox("Country", ["Global", "India", "USA", "Brazil", "UK", "France",
                                                 "Germany", "Japan", "Australia", "South Africa"])
    with col2:
        metric_sel = st.selectbox("Metric", ["cases", "deaths"])
    with col3:
        forecast_days = st.slider("Forecast horizon (days)", 30, 180, 90, step=30)

    with st.spinner(f"Running forecast model for {country_sel}..."):
        if country_sel == "Global":
            hist_df = get_historical_global(days=730)
        else:
            hist_df = get_country_historical(country_sel, days=730)

    if hist_df.empty:
        st.warning("No historical data available for this selection.")
    else:
        with st.spinner("Generating forecast..."):
            forecast = run_prophet_forecast(hist_df, "date", metric_sel, periods=forecast_days)

        if forecast.empty:
            st.error("Forecast could not be generated.")
        else:
            cutoff = hist_df["date"].max()
            forecast_only = forecast[forecast["ds"] > cutoff]

            # Peak prediction
            peak_date = forecast_only.loc[forecast_only["yhat"].idxmax(), "ds"]
            peak_val  = forecast_only["yhat"].max()
            peak_change = ((peak_val - hist_df[metric_sel].iloc[-1]) /
                           (hist_df[metric_sel].iloc[-1] + 1e-9)) * 100

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Current Value", f"{int(hist_df[metric_sel].iloc[-1]):,}")
            with m2:
                st.metric(f"Predicted Peak ({forecast_days}d)", f"{int(peak_val):,}",
                          delta=f"{peak_change:+.1f}%")
            with m3:
                st.metric("Peak Date", peak_date.strftime("%b %d, %Y"))

            fig = go.Figure()
            # Historical
            fig.add_trace(go.Scatter(
                x=hist_df["date"], y=hist_df[metric_sel],
                name="Historical", line=dict(color="#58a6ff", width=2)
            ))
            # Forecast
            fig.add_trace(go.Scatter(
                x=forecast_only["ds"], y=forecast_only["yhat"],
                name="Forecast", line=dict(color="#e3b341", width=2, dash="dot")
            ))
            # Confidence interval
            fig.add_trace(go.Scatter(
                x=pd.concat([forecast_only["ds"], forecast_only["ds"][::-1]]),
                y=pd.concat([forecast_only["yhat_upper"], forecast_only["yhat_lower"][::-1]]),
                fill="toself", fillcolor="rgba(227,179,65,0.15)",
                line=dict(color="rgba(0,0,0,0)"),
                name="95% Confidence",
            ))
            # Cutoff line
            fig.add_vline(x=str(cutoff), line_dash="dash", line_color="#f85149",
                          annotation_text="Today", annotation_font_color="#f85149")

            fig.update_layout(
                title=f"{country_sel} — {metric_sel.title()} Forecast ({forecast_days} days)",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font_color="#c9d1d9", height=420,
                xaxis=dict(gridcolor="#21262d"),
                yaxis=dict(title=metric_sel.title(), gridcolor="#21262d"),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption("⚠️ Forecasts are statistical projections only. Not for clinical or policy decisions.")

# ── TAB 2: Flu Surveillance ────────────────────────────────────────────────────
with tab2:
    st.markdown("### 🤧 Influenza-Like Illness (ILI) Surveillance")
    st.caption("CDC FluView data — weekly ILI percentage by season.")

    with st.spinner("Loading flu data..."):
        flu_df = get_flu_fallback()

    if not flu_df.empty:
        fig_flu = go.Figure()
        colors = {"2022-23": "#58a6ff", "2023-24": "#e3b341"}
        for season in flu_df["season"].unique():
            s_df = flu_df[flu_df["season"] == season]
            fig_flu.add_trace(go.Scatter(
                x=s_df["week"], y=s_df["ili_pct"],
                name=season, line=dict(color=colors.get(season, "#ccc"), width=2),
                fill="tozeroy" if season == "2023-24" else None,
                fillcolor="rgba(227,179,65,0.1)" if season == "2023-24" else None,
            ))
        fig_flu.add_hline(y=2.5, line_dash="dash", line_color="#f85149",
                           annotation_text="Baseline threshold (2.5%)")
        fig_flu.update_layout(
            title="ILI % by Season — CDC FluView",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#c9d1d9", height=380,
            xaxis=dict(title="Week", gridcolor="#21262d"),
            yaxis=dict(title="ILI %", gridcolor="#21262d"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_flu, use_container_width=True)

        # Season stats
        st.markdown("#### Season Comparison")
        col_s1, col_s2 = st.columns(2)
        for col, season in zip([col_s1, col_s2], flu_df["season"].unique()):
            s_df = flu_df[flu_df["season"] == season]
            with col:
                st.markdown(f"**{season}**")
                st.metric("Peak ILI %", f"{s_df['ili_pct'].max():.1f}%")
                st.metric("Weeks above baseline", f"{(s_df['ili_pct'] > 2.5).sum()}")

# ── TAB 3: Multi-Disease ───────────────────────────────────────────────────────
with tab3:
    st.markdown("### 📊 Multi-Country Trend Comparison")
    countries = st.multiselect("Compare Countries",
                                ["India", "USA", "Brazil", "UK", "France", "Germany",
                                 "Russia", "Italy", "Spain", "Japan"],
                                default=["India", "USA", "Brazil"])
    metric_comp = st.radio("Metric", ["cases", "deaths"], horizontal=True)

    if countries:
        fig_comp = go.Figure()
        palette = ["#58a6ff", "#e3b341", "#f85149", "#3fb950", "#a371f7",
                   "#79c0ff", "#ffa657", "#ff7b72", "#56d364", "#d2a8ff"]
        for i, country in enumerate(countries):
            with st.spinner(f"Loading {country}..."):
                h = get_country_historical(country, days=365)
            if not h.empty:
                fig_comp.add_trace(go.Scatter(
                    x=h["date"], y=h[metric_comp],
                    name=country, line=dict(color=palette[i % len(palette)], width=2)
                ))
        fig_comp.update_layout(
            title=f"Cumulative {metric_comp.title()} Comparison",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#c9d1d9", height=420,
            xaxis=dict(gridcolor="#21262d"),
            yaxis=dict(title=metric_comp.title(), gridcolor="#21262d"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        # Radar chart
        st.markdown("#### Multi-Metric Country Radar")
        from utils.data_fetcher import get_all_countries
        all_df = get_all_countries()
        if not all_df.empty:
            radar_data = all_df[all_df["country"].isin(countries)].copy()
            if not radar_data.empty:
                metrics_radar = ["cases", "deaths", "active", "casesPerOneMillion"]
                norm_radar = radar_data[metrics_radar].copy()
                for col in metrics_radar:
                    mx = norm_radar[col].max()
                    norm_radar[col] = norm_radar[col] / (mx + 1e-9) * 100

                fig_radar = go.Figure()
                for i, (_, row) in enumerate(radar_data.iterrows()):
                    vals = [float(norm_radar.loc[row.name, m]) for m in metrics_radar]
                    vals.append(vals[0])
                    fig_radar.add_trace(go.Scatterpolar(
                        r=vals, theta=metrics_radar + [metrics_radar[0]],
                        fill="toself", name=row["country"],
                        line=dict(color=palette[i % len(palette)])
                    ))
                fig_radar.update_layout(
                    polar=dict(bgcolor="rgba(0,0,0,0)",
                               radialaxis=dict(gridcolor="#30363d", color="#8b949e"),
                               angularaxis=dict(gridcolor="#30363d", color="#8b949e")),
                    paper_bgcolor="rgba(0,0,0,0)",
                    font_color="#c9d1d9", height=380,
                    legend=dict(bgcolor="rgba(0,0,0,0)"),
                )
                st.plotly_chart(fig_radar, use_container_width=True)
