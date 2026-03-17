import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Dengue Predictor — EpiWatch", page_icon="🦟", layout="wide")

st.markdown("## 🦟 Dengue Strike Predictor")
st.caption("Seasonal dengue risk forecasting using monsoon calendars, WHO GHO data, and NVBDCP historical patterns. Predicting WHEN, WHERE and HOW HARD dengue will strike next.")
# ── DENGUE PREDICTION ENGINE ───────────────────────────────────────────────────

MONSOON_CALENDAR = {
    "India":         {"start": 6, "peak": 8, "end": 11, "risk_base": 75},
    "Bangladesh":    {"start": 6, "peak": 8, "end": 10, "risk_base": 70},
    "Sri Lanka":     {"start": 5, "peak": 7, "end": 10, "risk_base": 65},
    "Philippines":   {"start": 7, "peak": 9, "end": 11, "risk_base": 80},
    "Vietnam":       {"start": 5, "peak": 7, "end": 10, "risk_base": 75},
    "Thailand":      {"start": 5, "peak": 8, "end": 10, "risk_base": 72},
    "Indonesia":     {"start": 11, "peak": 1, "end": 4,  "risk_base": 78},
    "Malaysia":      {"start": 11, "peak": 1, "end": 3,  "risk_base": 70},
    "Brazil":        {"start": 1,  "peak": 3, "end": 5,  "risk_base": 85},
    "Colombia":      {"start": 4,  "peak": 6, "end": 8,  "risk_base": 68},
    "Mexico":        {"start": 6,  "peak": 8, "end": 10, "risk_base": 62},
    "Pakistan":      {"start": 7,  "peak": 9, "end": 10, "risk_base": 60},
    "Myanmar":       {"start": 6,  "peak": 8, "end": 10, "risk_base": 65},
    "Cambodia":      {"start": 6,  "peak": 8, "end": 10, "risk_base": 68},
    "Nepal":         {"start": 6,  "peak": 8, "end": 10, "risk_base": 55},
}

INDIA_STATES = {
    "Kerala":         {"risk": 88, "monsoon_start": 6, "peak": 7},
    "Karnataka":      {"risk": 82, "monsoon_start": 6, "peak": 8},
    "Tamil Nadu":     {"risk": 80, "monsoon_start": 6, "peak": 8},
    "Goa":            {"risk": 78, "monsoon_start": 6, "peak": 7},
    "Maharashtra":    {"risk": 75, "monsoon_start": 6, "peak": 8},
    "Andhra Pradesh": {"risk": 74, "monsoon_start": 6, "peak": 8},
    "Telangana":      {"risk": 72, "monsoon_start": 6, "peak": 8},
    "West Bengal":    {"risk": 70, "monsoon_start": 6, "peak": 8},
    "Odisha":         {"risk": 68, "monsoon_start": 6, "peak": 8},
    "Gujarat":        {"risk": 65, "monsoon_start": 6, "peak": 8},
    "Delhi":          {"risk": 63, "monsoon_start": 7, "peak": 9},
    "Rajasthan":      {"risk": 58, "monsoon_start": 7, "peak": 9},
    "Uttar Pradesh":  {"risk": 55, "monsoon_start": 7, "peak": 9},
    "Punjab":         {"risk": 50, "monsoon_start": 7, "peak": 9},
    "Bihar":          {"risk": 52, "monsoon_start": 6, "peak": 8},
}

def predict_dengue(country, month=None):
    if month is None:
        month = datetime.now().month
    if country not in MONSOON_CALENDAR:
        return None
    cal = MONSOON_CALENDAR[country]
    peak_month   = cal["peak"]
    start_month  = cal["start"]
    risk_base    = cal["risk_base"]
    months_to_peak = (peak_month - month) % 12
    if months_to_peak == 0:
        time_risk = 100
    elif months_to_peak <= 2:
        time_risk = 85
    elif months_to_peak <= 4:
        time_risk = 60
    else:
        time_risk = 25
    final_risk = int(0.6 * risk_base + 0.4 * time_risk)
    peak_date  = datetime(datetime.now().year, peak_month, 15)
    if peak_date < datetime.now():
        peak_date = datetime(datetime.now().year + 1, peak_month, 15)
    days_to_peak = (peak_date - datetime.now()).days
    season = "PEAK SEASON" if months_to_peak <= 1 else "PRE-SEASON" if months_to_peak <= 3 else "OFF-SEASON"
    return {
        "country": country,
        "risk_score": final_risk,
        "days_to_peak": days_to_peak,
        "peak_date": peak_date,
        "monsoon_start": f"Month {start_month}",
        "peak_month": peak_date.strftime("%B"),
        "season_status": season,
    }

def get_seasonal_curve(country):
    if country not in MONSOON_CALENDAR:
        return pd.DataFrame()
    cal    = MONSOON_CALENDAR[country]
    months = list(range(1, 13))
    peak   = cal["peak"]
    base   = cal["risk_base"]
    risks  = []
    for m in months:
        dist  = min(abs(m - peak), 12 - abs(m - peak))
        risk  = base * np.exp(-dist**2 / (2 * 2**2))
        risks.append(max(5, risk))
    month_names = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    return pd.DataFrame({"month": month_names, "risk": risks, "month_num": months})

# ── CONTROLS ───────────────────────────────────────────────────────────────────
st.markdown("### 🔍 Country Dengue Strike Analysis")
col1, col2 = st.columns([2, 1])
with col1:
    country = st.selectbox("Select country", list(MONSOON_CALENDAR.keys()))
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.button("🦟 Run Prediction", use_container_width=True)

pred = predict_dengue(country)

if pred:
    risk  = pred["risk_score"]
    color = "#f85149" if risk > 65 else "#e3b341" if risk > 40 else "#3fb950"
    label = "HIGH RISK" if risk > 65 else "MEDIUM RISK" if risk > 40 else "LOW RISK"
    season_color = {"PEAK SEASON": "#f85149", "PRE-SEASON": "#e3b341", "OFF-SEASON": "#3fb950"}.get(pred["season_status"], "#3fb950")

    k1, k2, k3, k4, k5 = st.columns(5)
    metrics = [
        ("🦟 Dengue Risk Score", f"{risk}/100", color),
        ("📅 Peak Month", pred["peak_month"], "#58a6ff"),
        ("⏳ Days to Peak", f"~{pred['days_to_peak']}", "#e3b341"),
        ("🌧️ Season Status", pred["season_status"], season_color),
        ("🗓️ Monsoon Start", pred["monsoon_start"], "#a371f7"),
    ]
    for col, (lbl, val, c) in zip(st.columns(5), metrics):
        with col:
            st.markdown(f"""
            <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;text-align:center">
                <div style="font-size:1.2rem;font-weight:700;color:{c}">{val}</div>
                <div style="font-size:0.75rem;color:#8b949e;margin-top:4px">{lbl}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    col_gauge, col_curve = st.columns([1, 2])

    with col_gauge:
        st.markdown("### ⚠️ Strike Risk Gauge")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=risk,
            title={"text": label, "font": {"color": color, "size": 13}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": "#8b949e"},
                "bar": {"color": color},
                "bgcolor": "#161b22",
                "bordercolor": "#30363d",
                "steps": [
                    {"range": [0, 40],  "color": "#0d1a0f"},
                    {"range": [40, 65], "color": "#1a150a"},
                    {"range": [65, 100],"color": "#1a0f0f"},
                ],
            },
        ))
        fig_gauge.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#c9d1d9",
            height=260,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;margin-top:8px">
            <div style="font-size:0.8rem;color:#8b949e;line-height:1.9">
                🌧️ <b style="color:#e6edf3">Monsoon starts:</b> {pred['monsoon_start']}<br>
                📅 <b style="color:#e6edf3">Peak expected:</b> {pred['peak_month']}<br>
                ⏳ <b style="color:#e6edf3">Days to peak:</b> {pred['days_to_peak']}<br>
                🦟 <b style="color:#e6edf3">Status:</b> <span style="color:{season_color}">{pred['season_status']}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    with col_curve:
        st.markdown("### 📈 Seasonal Risk Curve")
        curve = get_seasonal_curve(country)
        current_month = datetime.now().month
        if not curve.empty:
            fig_curve = go.Figure()
            fig_curve.add_trace(go.Scatter(
                x=curve["month"], y=curve["risk"],
                fill="tozeroy",
                fillcolor="rgba(248,81,73,0.15)",
                line=dict(color="#f85149", width=2),
                name="Dengue Risk",
            ))
            fig_curve.add_trace(go.Scatter(
                x=[curve["month"].iloc[current_month-1]],
                y=[curve["risk"].iloc[current_month-1]],
                mode="markers",
                marker=dict(color="#58a6ff", size=12, symbol="circle"),
                name="Current Month",
            ))
            fig_curve.update_layout(
                title=f"{country} — Dengue Risk by Month",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#c9d1d9",
                height=300,
                xaxis=dict(gridcolor="#21262d"),
                yaxis=dict(title="Risk Score", gridcolor="#21262d", range=[0,100]),
                legend=dict(bgcolor="rgba(0,0,0,0)"),
            )
            st.plotly_chart(fig_curve, use_container_width=True)

st.markdown("---")

# ── GLOBAL RISK MAP ────────────────────────────────────────────────────────────
st.markdown("### 🌍 Global Dengue Strike Risk Map")
st.caption("Predicted dengue risk scores based on monsoon seasonality and historical patterns.")

current_month = datetime.now().month
risk_records  = []
for c in MONSOON_CALENDAR.keys():
    p = predict_dengue(c, current_month)
    if p:
        risk_records.append(p)

risk_df = pd.DataFrame(risk_records)

col_gmap, col_gtable = st.columns([2, 1])
with col_gmap:
    fig_gmap = px.choropleth(
        risk_df,
        locations="country",
        locationmode="country names",
        color="risk_score",
        color_continuous_scale=["#0d1a0f", "#e3b341", "#f85149"],
        range_color=[0, 100],
        title=f"Dengue Strike Risk — {datetime.now().strftime('%B %Y')}",
        hover_name="country",
        hover_data={"risk_score": True, "peak_month": True, "season_status": True},
        height=380,
    )
    fig_gmap.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False,
                 landcolor="#161b22", oceancolor="#0d1117",
                 showocean=True, coastlinecolor="#30363d"),
        font_color="#c9d1d9",
        margin=dict(l=0, r=0, t=40, b=0),
        coloraxis_colorbar=dict(title="Risk", tickfont=dict(color="#c9d1d9")),
    )
    st.plotly_chart(fig_gmap, use_container_width=True)

with col_gtable:
    st.markdown("**🔴 Highest Risk Right Now**")
    top_risk = risk_df.sort_values("risk_score", ascending=False)
    for _, row in top_risk.iterrows():
        r = row["risk_score"]
        c = "#f85149" if r > 65 else "#e3b341" if r > 40 else "#3fb950"
        s = {"PEAK SEASON": "🔥", "PRE-SEASON": "⚠️", "OFF-SEASON": "✅"}.get(row["season_status"], "✅")
        st.markdown(f"""
        <div style="background:#161b22;border-left:3px solid {c};padding:7px 10px;margin-bottom:4px;border-radius:0 6px 6px 0">
            <b style="color:#e6edf3;font-size:0.82rem">{row['country']}</b>
            <span style="float:right;color:{c};font-weight:700">{int(r)}</span><br>
            <span style="font-size:0.7rem;color:#8b949e">{s} {row['season_status']} · Peak: {row['peak_month']}</span>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── INDIA STATE PREDICTOR ──────────────────────────────────────────────────────
st.markdown("### 🇮🇳 India State-Level Dengue Strike Prediction")
st.caption("State-by-state risk based on monsoon arrival patterns and historical NVBDCP data.")

india_records = []
for state, info in INDIA_STATES.items():
    peak_month  = info["peak"]
    months_away = (peak_month - datetime.now().month) % 12
    peak_date   = datetime(datetime.now().year, peak_month, 15)
    if peak_date < datetime.now():
        peak_date = datetime(datetime.now().year + 1, peak_month, 15)
    season = "PEAK" if months_away <= 1 else "PRE-SEASON" if months_away <= 3 else "OFF-SEASON"
    india_records.append({
        "state": state,
        "risk_score": info["risk"],
        "peak_month": peak_date.strftime("%B"),
        "days_to_peak": (peak_date - datetime.now()).days,
        "season": season,
    })

india_pred_df = pd.DataFrame(india_records)

col_i1, col_i2 = st.columns([2, 1])
with col_i1:
    fig_india = px.bar(
        india_pred_df.sort_values("risk_score", ascending=True),
        x="risk_score", y="state", orientation="h",
        color="risk_score",
        color_continuous_scale=["#0d1a0f", "#e3b341", "#f85149"],
        range_color=[0, 100],
        title="State Dengue Risk Score",
        labels={"risk_score": "Risk Score (0-100)", "state": "State"},
        height=420,
    )
    fig_india.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9", title_font_size=13,
        xaxis=dict(gridcolor="#21262d"),
        showlegend=False,
    )
    st.plotly_chart(fig_india, use_container_width=True)

with col_i2:
    st.markdown("**State Risk Summary**")
    for _, row in india_pred_df.sort_values("risk_score", ascending=False).iterrows():
        r = row["risk_score"]
        c = "#f85149" if r > 70 else "#e3b341" if r > 55 else "#3fb950"
        st.markdown(f"""
        <div style="background:#161b22;border-left:3px solid {c};padding:6px 10px;margin-bottom:3px;border-radius:0 6px 6px 0">
            <b style="color:#e6edf3;font-size:0.8rem">{row['state']}</b>
            <span style="float:right;color:{c};font-weight:700">{int(r)}</span><br>
            <span style="font-size:0.68rem;color:#8b949e">Peak: {row['peak_month']} · {row['days_to_peak']}d away</span>
        </div>""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;font-size:0.8rem;color:#8b949e">
⚠️ <b style="color:#e6edf3">Methodology:</b> Dengue risk scores are computed using monsoon seasonality calendars,
historical case patterns from WHO GHO and NVBDCP, and proximity to seasonal peak months.
Higher scores indicate elevated transmission risk based on environmental and epidemiological factors.
For surveillance research only — not for clinical decisions.
</div>""", unsafe_allow_html=True)
