import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Strike Predictor — EpiWatch", page_icon="🎯", layout="wide")

st.markdown("## 🎯 COVID Strike Predictor")
st.caption("AI-powered epidemic intelligence — predicting WHEN, WHERE and HOW HARD COVID will strike next.")

from utils.data_fetcher import get_all_countries, get_country_historical, get_historical_global

# ── PREDICTION ENGINE ──────────────────────────────────────────────────────────
def predict_strike(country_hist, country_name):
    """Predict next COVID strike based on wave pattern analysis."""
    if country_hist.empty or len(country_hist) < 60:
        return None

    df = country_hist.copy().sort_values("date")
    df["daily"] = df["cases"].diff().clip(lower=0)
    df["7day"] = df["daily"].rolling(7).mean()
    df["30day"] = df["daily"].rolling(30).mean()

    # Detect wave peaks
    from scipy.signal import find_peaks
    signal = df["7day"].fillna(0).values
    peaks, _ = find_peaks(signal, distance=60, prominence=signal.max()*0.1)

    # Wave interval analysis
    if len(peaks) >= 2:
        intervals = np.diff(peaks)
        avg_interval = int(np.mean(intervals))
        std_interval = int(np.std(intervals))
    else:
        avg_interval = 180
        std_interval = 30

    # Last peak
    last_peak_idx = peaks[-1] if len(peaks) > 0 else len(df) - 90
    last_peak_date = df["date"].iloc[last_peak_idx]
    days_since_peak = (df["date"].iloc[-1] - last_peak_date).days

    # Next strike prediction
    days_to_next = max(0, avg_interval - days_since_peak)
    next_strike_date = datetime.now() + timedelta(days=days_to_next)

    # Current trend
    recent = df["7day"].iloc[-14:].mean()
    older  = df["7day"].iloc[-30:-14].mean()
    trend  = "rising" if recent > older * 1.1 else "falling" if recent < older * 0.9 else "stable"

    # Risk score 0-100
    trend_score = {"rising": 70, "stable": 40, "falling": 20}.get(trend, 40)
    time_score  = max(0, 100 - days_to_next) if days_to_next < 100 else 0
    risk_score  = int(0.6 * trend_score + 0.4 * time_score)

    # Severity prediction based on past peaks
    if len(peaks) > 0:
        peak_values = signal[peaks]
        avg_peak = np.mean(peak_values)
        last_val  = df["7day"].iloc[-1]
        projected = max(avg_peak, last_val * 1.5)
    else:
        projected = df["7day"].iloc[-1] * 2

    return {
        "country": country_name,
        "next_strike_date": next_strike_date,
        "days_to_strike": days_to_next,
        "risk_score": risk_score,
        "trend": trend,
        "avg_wave_interval_days": avg_interval,
        "waves_detected": len(peaks),
        "projected_daily_peak": int(projected),
        "current_7day_avg": int(df["7day"].iloc[-1]),
        "days_since_last_peak": days_since_peak,
    }

# ── GLOBAL RISK MAP ────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_global_risk():
    """Compute strike risk for top countries."""
    countries = ["USA", "India", "France", "Germany", "Brazil", "UK",
                 "Italy", "Russia", "Spain", "Japan", "Australia",
                 "Canada", "South Korea", "Argentina", "Mexico"]
    results = []
    for c in countries:
        hist = get_country_historical(c, days=730)
        pred = predict_strike(hist, c)
        if pred:
            results.append(pred)
    return pd.DataFrame(results) if results else pd.DataFrame()

# ── HEADER METRICS ─────────────────────────────────────────────────────────────
try:
    from scipy.signal import find_peaks
    scipy_available = True
except ImportError:
    scipy_available = False
    st.warning("⚠️ scipy not installed. Using simplified prediction model.")

# Single country deep analysis
st.markdown("### 🔍 Country Strike Analysis")
col1, col2 = st.columns([2, 1])
with col1:
    country = st.selectbox("Select country to analyse", [
        "India", "USA", "UK", "France", "Germany", "Brazil",
        "Italy", "Japan", "Australia", "South Korea", "Russia", "Spain"
    ])
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze = st.button("🎯 Run Prediction", use_container_width=True)

with st.spinner(f"Analysing {country} wave patterns..."):
    hist = get_country_historical(country, days=730)

if hist.empty:
    st.error("No historical data available.")
    st.stop()

# Simple fallback prediction if scipy not available
def simple_predict(df, country_name):
    df = df.copy().sort_values("date")
    df["daily"] = df["cases"].diff().clip(lower=0)
    df["7day"]  = df["daily"].rolling(7).mean().fillna(0)

    recent = df["7day"].iloc[-14:].mean()
    older  = df["7day"].iloc[-30:-14].mean()
    trend  = "rising" if recent > older * 1.1 else "falling" if recent < older * 0.9 else "stable"
    risk   = {"rising": 65, "stable": 35, "falling": 20}.get(trend, 35)

    next_date = datetime.now() + timedelta(days=90 if trend == "falling" else 45)
    return {
        "country": country_name,
        "next_strike_date": next_date,
        "days_to_strike": 90 if trend == "falling" else 45,
        "risk_score": risk,
        "trend": trend,
        "avg_wave_interval_days": 150,
        "waves_detected": 3,
        "projected_daily_peak": int(df["7day"].max() * 0.8),
        "current_7day_avg": int(df["7day"].iloc[-1]),
        "days_since_last_peak": 120,
    }

pred = predict_strike(hist, country) if scipy_available else simple_predict(hist, country)

if pred:
    # Risk color
    risk = pred["risk_score"]
    risk_color = "#f85149" if risk > 60 else "#e3b341" if risk > 35 else "#3fb950"
    risk_label = "HIGH RISK" if risk > 60 else "MEDIUM RISK" if risk > 35 else "LOW RISK"
    trend_emoji = {"rising": "📈", "falling": "📉", "stable": "➡️"}.get(pred["trend"], "➡️")

    # KPI row
    k1, k2, k3, k4, k5 = st.columns(5)
    metrics = [
        ("🎯 Strike Risk Score", f"{pred['risk_score']}/100", risk_color),
        ("📅 Next Strike Window", pred["next_strike_date"].strftime("%b %Y"), "#58a6ff"),
        ("⏳ Days Until Strike", f"~{pred['days_to_strike']} days", "#e3b341"),
        ("🌊 Waves Detected", f"{pred['waves_detected']} waves", "#a371f7"),
        ("📊 Current Trend", f"{trend_emoji} {pred['trend'].title()}", risk_color),
    ]
    for col, (label, val, color) in zip([k1,k2,k3,k4,k5], metrics):
        with col:
            st.markdown(f"""
            <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;text-align:center">
                <div style="font-size:1.3rem;font-weight:700;color:{color}">{val}</div>
                <div style="font-size:0.75rem;color:#8b949e;margin-top:4px">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Risk gauge + wave chart
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("### ⚠️ Strike Risk Gauge")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=pred["risk_score"],
            domain={"x": [0,1], "y": [0,1]},
            title={"text": f"{risk_label}", "font": {"color": risk_color, "size": 14}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#8b949e"},
                "bar": {"color": risk_color},
                "bgcolor": "#161b22",
                "bordercolor": "#30363d",
                "steps": [
                    {"range": [0, 35],  "color": "#0d1a0f"},
                    {"range": [35, 60], "color": "#1a150a"},
                    {"range": [60, 100],"color": "#1a0f0f"},
                ],
                "threshold": {
                    "line": {"color": "#ffffff", "width": 2},
                    "thickness": 0.75,
                    "value": pred["risk_score"],
                },
            },
        ))
        fig_gauge.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#c9d1d9",
            height=280,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;margin-top:8px">
            <div style="font-size:0.8rem;color:#8b949e;line-height:1.8">
                🌊 <b style="color:#e6edf3">Avg wave interval:</b> {pred['avg_wave_interval_days']} days<br>
                📅 <b style="color:#e6edf3">Days since last peak:</b> {pred['days_since_last_peak']}<br>
                📊 <b style="color:#e6edf3">Current 7-day avg:</b> {pred['current_7day_avg']:,}/day<br>
                🔺 <b style="color:#e6edf3">Projected peak:</b> {pred['projected_daily_peak']:,}/day
            </div>
        </div>""", unsafe_allow_html=True)

    with col_right:
        st.markdown("### 📈 Wave Pattern + Strike Forecast")
        hist2 = hist.copy()
        hist2["daily"] = hist2["cases"].diff().clip(lower=0)
        hist2["7day"]  = hist2["daily"].rolling(7).mean()

        # Forecast line
        last_date = hist2["date"].max()
        future_dates = pd.date_range(start=last_date, periods=91, freq="D")
        current_val  = hist2["7day"].iloc[-1]
        target_val   = pred["projected_daily_peak"]
        days_to      = max(pred["days_to_strike"], 1)

        future_vals = []
        for i in range(91):
            if i <= days_to:
                v = current_val + (target_val - current_val) * (i / days_to)
            else:
                v = target_val * max(0, 1 - (i - days_to) / 60)
            future_vals.append(max(0, v))

        fig_wave = go.Figure()
        fig_wave.add_trace(go.Scatter(
            x=hist2["date"], y=hist2["7day"],
            name="Historical (7-day avg)",
            line=dict(color="#58a6ff", width=2),
            fill="tozeroy", fillcolor="rgba(88,166,255,0.08)"
        ))
        fig_wave.add_trace(go.Scatter(
            x=future_dates, y=future_vals,
            name="Predicted Strike",
            line=dict(color=risk_color, width=2, dash="dot"),
            fill="tozeroy", fillcolor=f"rgba(248,81,73,0.08)"
        ))
        # Strike window marker
        max_y = max(future_vals + list(hist2["7day"].fillna(0)))
fig_wave.add_trace(go.Scatter(
    x=[pred["next_strike_date"], pred["next_strike_date"]],
    y=[0, max_y],
    mode="lines", name="Predicted Strike",
    line=dict(color=risk_color, dash="dash", width=2),
))
fig_wave.add_trace(go.Scatter(
    x=[datetime.now(), datetime.now()],
    y=[0, max_y],
    mode="lines", name="Today",
    line=dict(color="#8b949e", dash="dash", width=1),
))
        )
        fig_wave.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#c9d1d9",
            height=320,
            xaxis=dict(gridcolor="#21262d"),
            yaxis=dict(title="Daily Cases (7-day avg)", gridcolor="#21262d"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_wave, use_container_width=True)

st.markdown("---")

# Global risk comparison
st.markdown("### 🌍 Global Strike Risk Map")
st.caption("Strike probability scores across major countries based on wave pattern analysis.")

with st.spinner("Computing global strike predictions..."):
    risk_df = get_global_risk()

if not risk_df.empty:
    col_map, col_table = st.columns([2, 1])

    with col_map:
        fig_map = px.choropleth(
            risk_df,
            locations="country",
            locationmode="country names",
            color="risk_score",
            color_continuous_scale=["#0d1a0f", "#e3b341", "#f85149"],
            range_color=[0, 100],
            title="Strike Risk Score by Country",
            hover_name="country",
            hover_data={"risk_score": True, "days_to_strike": True, "trend": True},
            height=380,
        )
        fig_map.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False,
                     landcolor="#161b22", oceancolor="#0d1117",
                     showocean=True, coastlinecolor="#30363d"),
            font_color="#c9d1d9",
            margin=dict(l=0, r=0, t=40, b=0),
            coloraxis_colorbar=dict(title="Risk Score", tickfont=dict(color="#c9d1d9")),
        )
        st.plotly_chart(fig_map, use_container_width=True)

    with col_table:
        st.markdown("**🔴 Highest Risk Countries**")
        top_risk = risk_df.sort_values("risk_score", ascending=False).head(10)
        for _, row in top_risk.iterrows():
            r = row["risk_score"]
            c = "#f85149" if r > 60 else "#e3b341" if r > 35 else "#3fb950"
            t = {"rising":"📈","falling":"📉","stable":"➡️"}.get(row["trend"],"➡️")
            st.markdown(f"""
            <div style="background:#161b22;border-left:3px solid {c};padding:8px 12px;margin-bottom:4px;border-radius:0 6px 6px 0">
                <b style="color:#e6edf3;font-size:0.85rem">{row['country']}</b>
                <span style="float:right;color:{c};font-weight:700">{int(r)}</span><br>
                <span style="font-size:0.72rem;color:#8b949e">{t} {row['trend']} · Strike in ~{int(row['days_to_strike'])}d</span>
            </div>""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;font-size:0.8rem;color:#8b949e">
⚠️ <b style="color:#e6edf3">Disclaimer:</b> Predictions are based on historical wave pattern analysis using Disease.sh + CDC data.
This tool is for epidemiological research and surveillance purposes only.
Not for clinical or policy decisions. Actual outbreak timing depends on many unpredictable factors.
</div>""", unsafe_allow_html=True)
