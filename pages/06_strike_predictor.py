import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Strike Predictor — EpiWatch", page_icon="🎯", layout="wide")

st.markdown("## 🎯 COVID Epidemic Cycle Analyser")
st.caption("Statistical wave pattern analysis using 2 years of historical COVID-19 data (2020–2023). Detects epidemic cycles and estimates when the next outbreak window may occur.")

from utils.data_fetcher import get_all_countries, get_country_historical

# ── PREDICTION ENGINE ──────────────────────────────────────────────────────────
def predict_strike(country_hist, country_name):
    if country_hist.empty or len(country_hist) < 60:
        return None
    df = country_hist.copy().sort_values("date")
    df["daily"] = df["cases"].diff().clip(lower=0)
    df["7day"]  = df["daily"].rolling(7).mean().fillna(0)

    try:
        from scipy.signal import find_peaks
        signal = df["7day"].values
        peaks, props = find_peaks(signal, distance=60, prominence=signal.max()*0.08)
        scipy_ok = True
    except ImportError:
        peaks = []
        scipy_ok = False

    if len(peaks) >= 2:
        intervals    = np.diff(peaks)
        avg_interval = int(np.mean(intervals))
    else:
        avg_interval = 180

    last_peak_idx   = peaks[-1] if len(peaks) > 0 else len(df) - 90
    last_peak_date  = df["date"].iloc[last_peak_idx]
    days_since_peak = (df["date"].iloc[-1] - last_peak_date).days
    days_to_next    = avg_interval - days_since_peak
    if days_to_next <= 60:
        days_to_next = avg_interval + max(30, avg_interval - days_since_peak)
    days_to_next    = max(30, days_to_next)
    next_strike     = datetime.now() + timedelta(days=days_to_next)

    recent = df["7day"].iloc[-14:].mean()
    older  = df["7day"].iloc[-30:-14].mean()
    if recent < 100 and older < 100:
        trend = "Stable"
    elif recent > older * 1.1:
        trend = "Rising"
    elif recent < older * 0.9:
        trend = "Falling"
    else:
        trend = "Stable"

    trend_score = {"Rising": 70, "Stable": 40, "Falling": 20}.get(trend, 40)
    time_score  = max(0, 100 - days_to_next) if days_to_next < 100 else 0
    current_avg = int(df["7day"].iloc[-1])
    if current_avg < 100:
        risk_score = max(10, int(time_score * 0.3))
    else:
        risk_score = int(0.6 * trend_score + 0.4 * time_score)

    projected = int(df["7day"].max() * 0.75) if len(peaks) == 0 else int(np.mean(df["7day"].values[peaks]) * 0.8)

    return {
        "country": country_name,
        "next_strike_date": next_strike,
        "days_to_strike": days_to_next,
        "risk_score": risk_score,
        "trend": trend,
        "avg_wave_interval_days": avg_interval,
        "waves_detected": len(peaks),
        "projected_daily_peak": max(projected, 100),
        "current_7day_avg": int(df["7day"].iloc[-1]),
        "days_since_last_peak": days_since_peak,
        "peak_indices": list(peaks),
        "df": df,
    }

@st.cache_data(ttl=3600)
def get_global_risk():
    countries = ["USA", "India", "France", "Germany", "Brazil", "UK",
                 "Italy", "Russia", "Spain", "Japan", "Australia",
                 "Canada", "South Korea", "Argentina", "Mexico"]
    results = []
    for c in countries:
        hist = get_country_historical(c, days=730)
        pred = predict_strike(hist, c)
        if pred:
            results.append({
                "country": pred["country"],
                "risk_score": pred["risk_score"],
                "trend": pred["trend"],
                "days_to_strike": pred["days_to_strike"],
                "waves_detected": pred["waves_detected"],
            })
    return pd.DataFrame(results) if results else pd.DataFrame()

# ── COUNTRY SELECTOR ───────────────────────────────────────────────────────────
st.markdown("### 🔍 Country Deep Analysis")
col1, col2 = st.columns([3, 1])
with col1:
    country = st.selectbox("Select country to analyse", [
        "India", "USA", "UK", "France", "Germany", "Brazil",
        "Italy", "Japan", "Australia", "South Korea", "Russia", "Spain"
    ])
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    run = st.button("🎯 Analyse Now", use_container_width=True)

with st.spinner(f"Analysing {country} epidemic wave patterns..."):
    hist = get_country_historical(country, days=730)

pred = predict_strike(hist, country)

if not pred:
    st.error("Not enough data for this country.")
    st.stop()

risk  = pred["risk_score"]
color = "#f85149" if risk > 60 else "#e3b341" if risk > 35 else "#3fb950"
label = "HIGH RISK" if risk > 60 else "MEDIUM RISK" if risk > 35 else "LOW RISK"
trend_emoji = {"Rising": "📈", "Falling": "📉", "Stable": "➡️"}.get(pred["trend"], "➡️")
trend_color = {"Rising": "#f85149", "Falling": "#3fb950", "Stable": "#e3b341"}.get(pred["trend"], "#e3b341")

# ── KPI ROW ────────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
metrics = [
    ("🎯 Risk Score", f"{risk}/100", color),
    ("📅 Next Strike", pred["next_strike_date"].strftime("%b %Y"), "#58a6ff"),
    ("⏳ Days Away", f"~{pred['days_to_strike']}", "#e3b341"),
    ("🌊 Waves Found", f"{pred['waves_detected']}", "#a371f7"),
    ("📊 Trend", f"{trend_emoji} {pred['trend']}", trend_color),
]
for col, (lbl, val, c) in zip([k1,k2,k3,k4,k5], metrics):
    with col:
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;text-align:center">
            <div style="font-size:1.3rem;font-weight:700;color:{c}">{val}</div>
            <div style="font-size:0.75rem;color:#8b949e;margin-top:4px">{lbl}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

col_left, col_right = st.columns([1, 2])

# ── GAUGE ──────────────────────────────────────────────────────────────────────
with col_left:
    st.markdown("### ⚠️ Strike Risk Gauge")
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=risk,
        title={"text": f"{label}", "font": {"color": color, "size": 13}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#8b949e", "tickwidth": 1},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "#161b22",
            "bordercolor": "#30363d",
            "steps": [
                {"range": [0,  35], "color": "#0d1a0f"},
                {"range": [35, 65], "color": "#1a150a"},
                {"range": [65,100], "color": "#1a0f0f"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 3},
                "thickness": 0.75,
                "value": risk,
            },
        },
    ))
    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        height=260,
        margin=dict(l=20, r=20, t=50, b=10),
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    # Risk breakdown
    st.markdown("#### 📋 Risk Breakdown")
    factors = [
        ("Case trend", {"Rising": 70, "Stable": 40, "Falling": 20}.get(pred["trend"], 40), "#f85149"),
        ("Time since peak", min(100, pred["days_since_last_peak"]), "#e3b341"),
        ("Wave frequency", min(100, pred["waves_detected"] * 20), "#58a6ff"),
        ("Overall score", risk, color),
    ]
    for fname, fval, fc in factors:
        st.markdown(f"""
        <div style="margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:3px">
                <span style="color:#8b949e">{fname}</span>
                <span style="color:{fc};font-weight:500">{fval}/100</span>
            </div>
            <div style="background:#21262d;border-radius:4px;height:6px">
                <div style="background:{fc};width:{fval}%;height:6px;border-radius:4px"></div>
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;margin-top:12px;font-size:0.8rem;color:#8b949e;line-height:1.9">
        🌊 <b style="color:#e6edf3">Avg wave interval:</b> {pred['avg_wave_interval_days']} days<br>
        📅 <b style="color:#e6edf3">Days since last peak:</b> {pred['days_since_last_peak']}<br>
        📊 <b style="color:#e6edf3">Current 7-day avg:</b> {pred['current_7day_avg']:,}/day<br>
        🔺 <b style="color:#e6edf3">Projected next peak:</b> {pred['projected_daily_peak']:,}/day
    </div>""", unsafe_allow_html=True)

# ── WAVE CHART ─────────────────────────────────────────────────────────────────
with col_right:
    st.markdown("### 📈 Historical Waves + Strike Forecast")
    df_plot = pred["df"].copy()

    last_date    = df_plot["date"].max()
    future_dates = pd.date_range(start=last_date, periods=91, freq="D")
    curr_val     = pred["current_7day_avg"]
    target_val   = pred["projected_daily_peak"]
    days_to      = max(pred["days_to_strike"], 1)

    future_vals = []
    for i in range(91):
        if i <= days_to:
            v = curr_val + (target_val - curr_val) * (i / days_to)
        else:
            v = target_val * max(0, 1 - (i - days_to) / 60)
        future_vals.append(max(0, v))

    fig_wave = go.Figure()

    # Historical
    fig_wave.add_trace(go.Scatter(
        x=df_plot["date"], y=df_plot["7day"],
        name="Historical (7-day avg)",
        line=dict(color="#58a6ff", width=2),
        fill="tozeroy", fillcolor="rgba(88,166,255,0.08)"
    ))

    # Mark detected peaks
    if pred["peak_indices"]:
        peak_dates = df_plot["date"].iloc[pred["peak_indices"]]
        peak_vals  = df_plot["7day"].iloc[pred["peak_indices"]]
        fig_wave.add_trace(go.Scatter(
            x=peak_dates, y=peak_vals,
            mode="markers",
            marker=dict(color="#e3b341", size=10, symbol="triangle-up"),
            name="Detected wave peaks",
        ))

    # Forecast
    fig_wave.add_trace(go.Scatter(
        x=future_dates, y=future_vals,
        name="Predicted next strike",
        line=dict(color=color, width=2, dash="dot"),
        fill="tozeroy", fillcolor="rgba(248,81,73,0.08)"
    ))

    # Today line
    max_y = max(future_vals + list(df_plot["7day"].fillna(0)))
    fig_wave.add_trace(go.Scatter(
        x=[datetime.now(), datetime.now()],
        y=[0, max_y],
        mode="lines", name="Today",
        line=dict(color="#8b949e", dash="dash", width=1),
    ))

    # Next strike line
    fig_wave.add_trace(go.Scatter(
        x=[pred["next_strike_date"], pred["next_strike_date"]],
        y=[0, max_y],
        mode="lines", name="Predicted strike",
        line=dict(color=color, dash="dash", width=2),
    ))

    # Annotation for flat post-2023 region
    fig_wave.add_annotation(
        x=pd.Timestamp("2024-06-01"), y=max_y * 0.85,
        text="COVID reporting ended 2023<br>Forecast based on wave patterns",
        showarrow=False,
        font=dict(color="#8b949e", size=10),
        bgcolor="#161b22",
        bordercolor="#30363d",
        borderwidth=1,
    )

    fig_wave.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        height=380,
        xaxis=dict(gridcolor="#21262d", title="Date"),
        yaxis=dict(gridcolor="#21262d", title="Daily Cases (7-day avg)"),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_wave, use_container_width=True)

    # Authority recommendation
    if risk > 65:
        rec_color = "#f85149"
        rec_bg    = "#1a0f0f"
        rec_text  = "HIGH ALERT — Activate surveillance teams. Prepare healthcare capacity. Issue public advisories."
    elif risk > 35:
        rec_color = "#e3b341"
        rec_bg    = "#1a150a"
        rec_text  = "MONITOR CLOSELY — Increase testing frequency. Review hospital capacity. Prepare response plans."
    else:
        rec_color = "#3fb950"
        rec_bg    = "#0d1a0f"
        rec_text  = "LOW RISK — Maintain routine surveillance. Continue monitoring trends."

    st.markdown(f"""
    <div style="background:{rec_bg};border-left:4px solid {rec_color};padding:12px 16px;border-radius:0 8px 8px 0;margin-top:8px">
        <b style="color:{rec_color};font-size:0.85rem">Recommended Action</b><br>
        <span style="color:#c9d1d9;font-size:0.82rem">{rec_text}</span>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── GLOBAL RISK MAP ────────────────────────────────────────────────────────────
st.markdown("### 🌍 Global Strike Risk Map")
with st.spinner("Computing global predictions..."):
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
            title="Epidemic Strike Risk by Country",
            hover_name="country",
            hover_data={"risk_score": True, "trend": True, "days_to_strike": True},
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
        for _, row in risk_df.sort_values("risk_score", ascending=False).iterrows():
            r = row["risk_score"]
            c = "#f85149" if r > 60 else "#e3b341" if r > 35 else "#3fb950"
            t = {"Rising":"📈","Falling":"📉","Stable":"➡️"}.get(row["trend"],"➡️")
            st.markdown(f"""
            <div style="background:#161b22;border-left:3px solid {c};padding:8px 12px;margin-bottom:4px;border-radius:0 6px 6px 0">
                <b style="color:#e6edf3;font-size:0.85rem">{row['country']}</b>
                <span style="float:right;color:{c};font-weight:700">{int(r)}</span><br>
                <span style="font-size:0.72rem;color:#8b949e">{t} {row['trend']} · Strike ~{int(row['days_to_strike'])}d</span>
            </div>""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;font-size:0.8rem;color:#8b949e">
⚠️ <b style="color:#e6edf3">Methodology:</b> Risk scores combine case trend velocity, time since last epidemic peak,
and historical wave interval analysis using Disease.sh + CDC data (Jan 2020 – Dec 2023).
Yellow triangles mark detected wave peaks. Dotted red line shows predicted next strike window.
For epidemiological research and surveillance only.
</div>""", unsafe_allow_html=True)
