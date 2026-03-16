# 🦠 EpiWatch — Intelligent Disease Surveillance Dashboard

> **Hackathon Project** | Real-time global health intelligence platform integrating 9 public health data sources with AI-powered analysis.

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red?logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🎯 What is EpiWatch?

EpiWatch is a disease surveillance intelligence dashboard that aggregates **real-time and historical data** from 9 authoritative public health sources into a unified, AI-powered analytical platform. It enables epidemiologists, researchers, and health officials to monitor outbreaks, forecast trends, and generate situation reports — all from a single interface.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🌍 **Global Disease Map** | Interactive choropleth + bubble maps. Drill into any country. Multiple metrics. |
| 🇮🇳 **India Health Dashboard** | State-level case distribution, IHME disease burden treemap, daily trends |
| 🚨 **Live Outbreak Alerts** | Real-time ProMED + HealthMap RSS feeds with severity scoring and geo-map |
| 📈 **ML Forecasting** | Facebook Prophet-based 30/90/180-day case forecasts with confidence intervals |
| 🔬 **Anomaly Detection** | Z-score based statistical flagging of unusual country-level case spikes |
| ⚠️ **Risk Scorer** | ML-composite 0–100 risk score per country updated daily |
| 🤖 **AI Analyst (Claude)** | Natural language Q&A with live data context + one-click situation reports |
| 🦠 **Flu Surveillance** | CDC FluView seasonal ILI% trend charts with baseline threshold |

---

## 🗂️ Data Sources

| Source | Method | What it provides |
|---|---|---|
| [Disease.sh API](https://disease.sh) | REST API | Real-time global COVID + country stats |
| [CDC Open Data Portal](https://data.cdc.gov) | API / JSON | US disease statistics, death counts |
| [WHO GHO OData API](https://who.int/data/gho) | OData API | Global health indicators, country data |
| [CDC FluView](https://cdc.gov/fluview) | Data API | Weekly influenza ILI surveillance |
| [HealthMap](https://healthmap.org) | API | Real-time automated outbreak monitoring |
| [ProMED Mail](https://promedmail.org) | RSS Feed | Infectious disease outbreak reports |
| [IHME GHDx India](https://ghdx.healthdata.org) | CSV / Static | India disease burden (GBD 2019) |
| [ECDC](https://ecdc.europa.eu) | API | European disease surveillance |
| [UK Gov Health](https://api.coronavirus.data.gov.uk) | API | UK public health statistics |

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/epiwatch-dashboard.git
cd epiwatch-dashboard
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up AI (optional but recommended)
Create `.streamlit/secrets.toml`:
```toml
ANTHROPIC_API_KEY = "sk-ant-your-key-here"
```
Get your free API key at [console.anthropic.com](https://console.anthropic.com)

### 4. Run the dashboard
```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## 🏗️ Project Structure

```
epiwatch-dashboard/
├── app.py                          # Main entry point + home page
├── requirements.txt
├── .streamlit/
│   └── config.toml                 # Dark theme config
├── pages/
│   ├── 01_global_map.py            # 🌍 Interactive world map
│   ├── 02_india_focus.py           # 🇮🇳 India state-level dashboard
│   ├── 03_outbreak_alerts.py       # 🚨 Live alert feed + geo-map
│   ├── 04_forecasting.py           # 📈 ML forecasting + flu surveillance
│   └── 05_ai_insights.py           # 🤖 AI analyst + report generator
└── utils/
    ├── __init__.py
    └── data_fetcher.py             # All API integrations + ML risk scoring
```

---

## 🧠 AI Features (Claude-Powered)

The **AI Analyst** page uses Claude to:
- Answer natural language questions like *"Which countries are at highest risk this week?"*
- Inject live dashboard data into every prompt for grounded, accurate answers
- Generate formatted epidemiological situation reports with one click
- Maintain multi-turn conversation context

### Example questions:
- *"Compare dengue trends in India vs Southeast Asia"*
- *"What does today's anomaly data tell us about outbreak risk?"*
- *"Generate a weekly situation report for health officials"*
- *"Summarize India's top disease burden challenges from IHME data"*

---

## 🔬 ML Models

### Outbreak Risk Score (0–100)
Computed per country daily using:
- **35%** — New cases velocity (today's cases, normalized)
- **25%** — Active case ratio (active / total)
- **20%** — Case fatality rate
- **20%** — Cases per million population

### Forecasting
- Primary: **Facebook Prophet** with yearly seasonality
- Fallback: **Linear trend decomposition** (if Prophet unavailable)
- Outputs: point forecast + 95% confidence interval

### Anomaly Detection
- Z-score method on daily new cases across all countries
- Threshold: z > 2.5 (flagged as anomalous)

---

## 📸 Screenshots

> Dashboard running on Streamlit Community Cloud

| Page | Preview |
|---|---|
| Home | Global KPIs + bar chart + alert feed |
| Global Map | Choropleth + risk heatmap |
| India | State bars + IHME treemap + trends |
| Alerts | Live RSS feed + geo scatter map |
| Forecast | Prophet chart + flu ILI + radar |
| AI Analyst | Chat interface + situation reports |

---

## 🌐 Deploy to Streamlit Cloud

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo → select `app.py`
4. Add `ANTHROPIC_API_KEY` in **Advanced Settings → Secrets**
5. Deploy — live in ~2 minutes!

---

## 🙏 Acknowledgements & Citations

- **Disease.sh** — Open Disease Data API (github.com/disease-sh/API)
- **CDC Open Data Portal** — data.cdc.gov
- **WHO Global Health Observatory** — who.int/data/gho
- **CDC FluView** — cdc.gov/flu/weekly
- **HealthMap** — healthmap.org (Brownstein Lab, Boston Children's Hospital)
- **ProMED Mail** — ISID promedmail.org
- **IHME GHDx** — healthdata.org (Global Burden of Disease 2019, India)
- **ECDC** — ecdc.europa.eu
- **UK Government Health Statistics** — api.coronavirus.data.gov.uk
- **Anthropic Claude** — AI analysis (anthropic.com)

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

*Built for the Disease Surveillance Hackathon | EpiWatch Team*
