import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="Outbreak Alerts — EpiWatch", page_icon="🚨", layout="wide")

st.markdown("## 🚨 Real-Time Outbreak Alerts")
st.caption("Live feeds from ProMED Mail, HealthMap, and WHO via RSS/API. Auto-refreshed every 30 minutes.")

from utils.data_fetcher import get_outbreak_alerts, get_promed_alerts, get_healthmap_alerts, get_anomalies

# Refresh button
col_r, col_f1, col_f2, col_f3 = st.columns([1, 2, 2, 2])
with col_r:
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

with col_f1:
    severity_filter = st.multiselect("Severity", ["high", "medium", "low"],
                                      default=["high", "medium", "low"])
with col_f2:
    source_filter = st.multiselect("Source", ["ProMED", "HealthMap", "WHO", "CDC", "ECDC", "FAO"],
                                    default=["ProMED", "HealthMap", "WHO", "CDC", "ECDC", "FAO"])
with col_f3:
    disease_search = st.text_input("Search disease/keyword", placeholder="e.g. dengue, flu...")

with st.spinner("Fetching live alerts..."):
    all_alerts = get_outbreak_alerts()
    anomalies  = get_anomalies()

# Filter
filtered = [a for a in all_alerts
            if a.get("severity") in severity_filter
            and a.get("source") in source_filter
            and (not disease_search or disease_search.lower() in a.get("title","").lower())]

# Summary row
col_high, col_med, col_low, col_total = st.columns(4)
highs  = sum(1 for a in all_alerts if a.get("severity") == "high")
meds   = sum(1 for a in all_alerts if a.get("severity") == "medium")
lows   = sum(1 for a in all_alerts if a.get("severity") == "low")
for col, label, val, color in [
    (col_high, "🔴 High Severity", highs, "#f85149"),
    (col_med,  "🟡 Medium",        meds,  "#e3b341"),
    (col_low,  "🟢 Low",           lows,  "#3fb950"),
    (col_total,"📡 Total Alerts",  len(all_alerts), "#58a6ff"),
]:
    with col:
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 16px;text-align:center">
            <div style="font-size:1.6rem;font-weight:700;color:{color}">{val}</div>
            <div style="font-size:0.8rem;color:#8b949e">{label}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

col_feed, col_map = st.columns([1, 1])

# Alert feed
with col_feed:
    st.markdown(f"### 📋 Alert Feed ({len(filtered)} alerts)")
    if not filtered:
        st.info("No alerts match the current filters.")
    for alert in filtered:
        sev = alert.get("severity", "low")
        color_map = {"high": "#f85149", "medium": "#e3b341", "low": "#3fb950"}
        border_color = color_map.get(sev, "#3fb950")
        bg_map = {"high": "#1a0f0f", "medium": "#1a150a", "low": "#0d1a0f"}
        bg = bg_map.get(sev, "#0d1a0f")

        title   = alert.get("title", "")[:90]
        summary = alert.get("summary", "")[:400]
        source  = alert.get("source", "")
        date    = str(alert.get("date", ""))[:16]
        disease = alert.get("disease", "")
        country = alert.get("country", "")

        disease_badge = f'<span style="background:#1f2d3d;color:#79c0ff;font-size:0.68rem;padding:2px 6px;border-radius:4px;margin-right:4px">{disease}</span>' if disease else ""
        sev_badge = f'<span style="background:{bg};color:{border_color};border:1px solid {border_color};font-size:0.68rem;padding:2px 6px;border-radius:4px;margin-right:4px">{sev.upper()}</span>'
        country_badge = f'<span style="background:#1f2d3d;color:#8b949e;font-size:0.68rem;padding:2px 6px;border-radius:4px;margin-right:4px">📍 {country}</span>' if country else ""

        with st.expander(f"{sev.upper()} — {title}", expanded=False):
            st.markdown(f"""
            <div style="margin-bottom:8px">{sev_badge}{disease_badge}{country_badge}</div>
            <div style="font-size:0.85rem;font-weight:600;color:#e6edf3;margin-bottom:8px">{title}</div>
            <div style="font-size:0.82rem;color:#c9d1d9;line-height:1.7;margin-bottom:8px">{summary if summary else "No additional details available."}</div>
            <div style="font-size:0.72rem;color:#6e7681;border-top:1px solid #30363d;padding-top:8px">
              📡 <b style="color:#8b949e">Source:</b> {source} &nbsp;|&nbsp; 🕐 <b style="color:#8b949e">Date:</b> {date}
&nbsp;|&nbsp; <a href="https://promedmail.org/promed-posts/" target="_blank" style="color:#58a6ff;text-decoration:none">View on ProMED →</a>
            </div>
            """, unsafe_allow_html=True)

# Alert map
with col_map:
    st.markdown("### 🗺️ Alert Map")
    map_alerts = [a for a in filtered if a.get("lat") and a.get("lon")
                  and abs(float(a.get("lat", 0))) > 0.1]

    if map_alerts:
        map_df = pd.DataFrame(map_alerts)
        map_df["lat"] = map_df["lat"].astype(float)
        map_df["lon"] = map_df["lon"].astype(float)
        map_df["size"] = map_df["severity"].map({"high": 20, "medium": 12, "low": 7})
        map_df["color"] = map_df["severity"].map({"high": "#f85149", "medium": "#e3b341", "low": "#3fb950"})

        fig_map = go.Figure()
        for _, row in map_df.iterrows():
            fig_map.add_trace(go.Scattergeo(
                lat=[row["lat"]], lon=[row["lon"]],
                mode="markers",
                marker=dict(size=row["size"], color=row["color"], opacity=0.85,
                            line=dict(color="#0d1117", width=0.5)),
                name=row.get("source",""),
                hovertemplate=f"<b>{row.get('title','')[:50]}</b><br>{row.get('source','')}<extra></extra>",
                showlegend=False,
            ))
        fig_map.update_layout(
            geo=dict(bgcolor="rgba(0,0,0,0)", showframe=False,
                     showcoastlines=True, coastlinecolor="#30363d",
                     landcolor="#161b22", oceancolor="#0d1117",
                     showocean=True, showlakes=False,
                     projection_type="natural earth"),
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            height=380,
            font_color="#c9d1d9",
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.info("Geo-coded alerts: fetching location data... Showing text feed on the left.")
        # Fallback static world map with known disease hotspots
        hotspots = pd.DataFrame([
            {"lat": 13.7, "lon": 100.5, "disease": "Dengue", "region": "Southeast Asia"},
            {"lat": 9.0,  "lon": 43.0,  "disease": "Cholera", "region": "Horn of Africa"},
            {"lat": 38.9, "lon": -77.0, "disease": "Influenza", "region": "North America"},
            {"lat": 5.0,  "lon": 18.0,  "disease": "Mpox", "region": "West Africa"},
            {"lat": 50.0, "lon": 10.0,  "disease": "Measles", "region": "Europe"},
            {"lat": 20.5, "lon": 78.9,  "disease": "Dengue", "region": "India"},
        ])
        fig_hot = px.scatter_geo(hotspots, lat="lat", lon="lon",
                                  hover_name="disease", size_max=15,
                                  color="disease", height=380,
                                  title="Known Active Hotspots")
        fig_hot.update_layout(
            geo=dict(bgcolor="rgba(0,0,0,0)", landcolor="#161b22",
                     oceancolor="#0d1117", showocean=True, showframe=False,
                     coastlinecolor="#30363d"),
            paper_bgcolor="rgba(0,0,0,0)", font_color="#c9d1d9",
            margin=dict(l=0, r=0, t=30, b=0),
        )
        st.plotly_chart(fig_hot, use_container_width=True)

st.markdown("---")

# Anomaly detection
st.markdown("### 🔬 Statistical Anomaly Detection")
st.caption("Countries with new-case counts more than 2.5 standard deviations above the global mean today.")

if anomalies:
    anom_df = pd.DataFrame(anomalies)
    col_a, col_b = st.columns([2, 1])
    with col_a:
        fig_anom = px.bar(anom_df, x="country", y="z_score",
                          color="z_score", color_continuous_scale="Reds",
                          title="Z-Score Anomalies (Today's New Cases)",
                          labels={"z_score": "Z-Score", "country": "Country"},
                          height=300)
        fig_anom.add_hline(y=2.5, line_dash="dash", line_color="#e3b341",
                            annotation_text="Alert threshold (z=2.5)")
        fig_anom.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#c9d1d9", yaxis=dict(gridcolor="#21262d"),
            showlegend=False,
        )
        st.plotly_chart(fig_anom, use_container_width=True)
    with col_b:
        st.markdown("**Flagged Countries**")
        for a in anomalies[:8]:
            st.markdown(f"""
            <div style="background:#1a0f0f;border-left:3px solid #f85149;padding:6px 10px;margin-bottom:4px;border-radius:0 6px 6px 0;font-size:0.8rem">
                <b style="color:#e6edf3">{a['country']}</b><br>
                <span style="color:#8b949e">Z={a['z_score']} | {a['todayCases']:,} new cases</span>
            </div>""", unsafe_allow_html=True)
else:
    st.success("✅ No statistical anomalies detected in today's data.")
