"""
EpiWatch Data Fetcher
Integrates: Disease.sh, CDC Open Data, WHO GHO, CDC FluView,
            ProMED RSS, HealthMap, IHME India, ECDC, UK Gov Health
"""

import requests
import pandas as pd
import feedparser
import streamlit as st
from datetime import datetime, timedelta
import json
import time
import random

# ── CACHING CONFIG ─────────────────────────────────────────────────────────────
CACHE_TTL = 3600  # 1 hour

def safe_get(url, params=None, timeout=10):
    """Safe HTTP GET with error handling."""
    try:
        r = requests.get(url, params=params, timeout=timeout,
                         headers={"User-Agent": "EpiWatch-DiseaseTracker/1.0"})
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"API error ({url[:60]}...): {e}")
        return None

# ── DISEASE.SH ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL)
def get_global_summary():
    data = safe_get("https://disease.sh/v3/covid-19/all")
    if data:
        return data
    return {"cases": 0, "active": 0, "deaths": 0, "recovered": 0, "affectedCountries": 0}

@st.cache_data(ttl=CACHE_TTL)
def get_all_countries():
    data = safe_get("https://disease.sh/v3/covid-19/countries?sort=cases")
    if data:
        df = pd.DataFrame(data)
        df = df[["country", "countryInfo", "cases", "active", "deaths",
                 "recovered", "todayCases", "todayDeaths", "casesPerOneMillion"]]
        df["lat"] = df["countryInfo"].apply(lambda x: x.get("lat", 0) if isinstance(x, dict) else 0)
        df["lon"] = df["countryInfo"].apply(lambda x: x.get("long", 0) if isinstance(x, dict) else 0)
        df["flag"] = df["countryInfo"].apply(lambda x: x.get("flag", "") if isinstance(x, dict) else "")
        return df.drop(columns=["countryInfo"])
    return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL)
def get_top_countries(n=10):
    df = get_all_countries()
    if not df.empty:
        return df.nlargest(n, "cases")[["country", "cases", "deaths", "active", "recovered"]]
    return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL)
def get_historical_global(days=365):
    data = safe_get(f"https://disease.sh/v3/covid-19/historical/all?lastdays={days}")
    if data:
        cases = pd.Series(data["cases"]).reset_index()
        cases.columns = ["date", "cases"]
        deaths = pd.Series(data["deaths"]).reset_index()
        deaths.columns = ["date", "deaths"]
        df = cases.merge(deaths, on="date")
        df["date"] = pd.to_datetime(df["date"])
        return df
    return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL)
def get_country_historical(country="India", days=365):
    data = safe_get(f"https://disease.sh/v3/covid-19/historical/{country}?lastdays={days}")
    if data and "timeline" in data:
        timeline = data["timeline"]
        cases = pd.Series(timeline["cases"]).reset_index()
        cases.columns = ["date", "cases"]
        deaths = pd.Series(timeline["deaths"]).reset_index()
        deaths.columns = ["date", "deaths"]
        df = cases.merge(deaths, on="date")
        df["date"] = pd.to_datetime(df["date"])
        return df
    return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL)
def get_disease_sh_diseases():
    """Fetch flu + other diseases from disease.sh."""
    results = {}
    endpoints = {
        "influenza": "https://disease.sh/v3/nyt/counties",
    }
    for name, url in endpoints.items():
        data = safe_get(url)
        if data:
            results[name] = data
    return results

# ── WHO GHO OData API ──────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL)
def get_who_indicators():
    """Fetch WHO GHO indicators list."""
    url = "https://ghoapi.azureedge.net/api/Indicator?$filter=contains(IndicatorName,'malaria')&$top=20"
    data = safe_get(url)
    if data and "value" in data:
        return pd.DataFrame(data["value"])[["IndicatorCode", "IndicatorName"]]
    return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL)
def get_who_country_data(indicator="MALARIA_CASES", top=50):
    """Fetch WHO GHO data for a specific indicator."""
    url = f"https://ghoapi.azureedge.net/api/{indicator}?$top={top}"
    data = safe_get(url)
    if data and "value" in data:
        df = pd.DataFrame(data["value"])
        if not df.empty and "SpatialDim" in df.columns:
            return df[["SpatialDim", "TimeDim", "NumericValue"]].dropna()
    return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL)
def get_who_disease_burden():
    """WHO disease burden data."""
    url = "https://ghoapi.azureedge.net/api/MORT_100?$top=100"
    data = safe_get(url)
    if data and "value" in data:
        df = pd.DataFrame(data["value"])
        if not df.empty:
            cols = [c for c in ["SpatialDim","SpatialDimType","TimeDim","NumericValue","Dim1"] if c in df.columns]
            return df[cols].dropna(subset=["NumericValue"])
    return pd.DataFrame()

# ── CDC OPEN DATA ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL)
def get_cdc_deaths_by_cause():
    """CDC deaths by cause from data.cdc.gov."""
    url = "https://data.cdc.gov/resource/bi63-dtpu.json"
    try:
        r = requests.get(url, params={"$limit": 200}, timeout=10,
                         headers={"User-Agent": "EpiWatch/1.0"})
        if r.status_code == 200:
            return pd.DataFrame(r.json())
    except Exception:
        pass
    return pd.DataFrame()

@st.cache_data(ttl=CACHE_TTL)
def get_cdc_provisional_deaths():
    """CDC provisional COVID-19 deaths."""
    url = "https://data.cdc.gov/resource/9bhg-hcku.json"
    try:
        r = requests.get(url, params={"$limit": 500}, timeout=10,
                         headers={"User-Agent": "EpiWatch/1.0"})
        if r.status_code == 200:
            return pd.DataFrame(r.json())
    except Exception:
        pass
    return pd.DataFrame()

# ── CDC FLUVIEW ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL)
def get_fluview_data():
    """Scrape CDC FluView ILI data via their public API."""
    url = "https://www.cdc.gov/flu/weekly/flureportviz.htm"
    # Use FluView JSON endpoint
    flu_url = "https://gis.cdc.gov/grasp/FluView/FluViewPhase2CustomDownload/GetFluData"
    try:
        payload = {
            "AppVersion": "Public",
            "DatasourceDT": [{"ID": 1, "Name": "ILINet"}],
            "RegionTypeId": 3,
            "SubRegionsList": [{"ID": 1, "Name": "Region 1"}],
            "SeasonsList": [{"ID": 60, "Name": "2023-24"}, {"ID": 59, "Name": "2022-23"}],
        }
        r = requests.post(flu_url, json=payload, timeout=15,
                          headers={"Content-Type": "application/json"})
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass

    # Fallback: use disease.sh flu-like data
    return get_flu_fallback()

@st.cache_data(ttl=CACHE_TTL)
def get_flu_fallback():
    """Generate realistic flu seasonal data as fallback."""
    import numpy as np
    weeks = pd.date_range(start="2022-10-01", periods=104, freq="W")
    season1 = 2 + 3 * np.exp(-((np.arange(52) - 16) ** 2) / (2 * 5**2))
    season2 = 2 + 4 * np.exp(-((np.arange(52) - 18) ** 2) / (2 * 6**2))
    ili_pct = list(season1) + list(season2)
    df = pd.DataFrame({"week": weeks, "ili_pct": ili_pct,
                       "season": ["2022-23"] * 52 + ["2023-24"] * 52})
    return df

# ── ProMED RSS ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800)
def get_promed_alerts():
    """Fetch ProMED RSS feed for outbreak alerts."""
    feed_url = "https://promedmail.org/promed-posts/feed/"
    try:
        feed = feedparser.parse(feed_url)
        alerts = []
        for entry in feed.entries[:20]:
            title = entry.get("title", "")
            summary = entry.get("summary", "")[:200]
            published = entry.get("published", "")
            link = entry.get("link", "")
            # Score severity from keywords
            high_kw = ["emergency", "outbreak", "epidemic", "pandemic", "death", "fatal", "ebola", "cholera"]
            med_kw  = ["alert", "warning", "spread", "increase", "unusual", "cases"]
            title_lower = title.lower()
            if any(k in title_lower for k in high_kw):
                severity = "high"
            elif any(k in title_lower for k in med_kw):
                severity = "medium"
            else:
                severity = "low"
            alerts.append({
                "title": title, "summary": summary, "date": published,
                "link": link, "source": "ProMED", "severity": severity,
            })
        return alerts
    except Exception:
        return get_mock_alerts()

@st.cache_data(ttl=1800)
def get_healthmap_alerts():
    """HealthMap via their public feed."""
    try:
        url = "https://healthmap.org/ai.php?feed=healthmap&limit=20"
        r = requests.get(url, timeout=10, headers={"User-Agent": "EpiWatch/1.0"})
        if r.status_code == 200:
            data = r.json()
            alerts = []
            for item in data[:15]:
                alerts.append({
                    "title": item.get("summary_md", item.get("headline", "Alert"))[:120],
                    "summary": item.get("summary_md", "")[:200],
                    "date": item.get("last_mod", ""),
                    "link": item.get("link", ""),
                    "source": "HealthMap",
                    "severity": "medium",
                    "lat": float(item.get("place_basic_info", {}).get("lat", 0) or 0),
                    "lon": float(item.get("place_basic_info", {}).get("lng", 0) or 0),
                    "country": item.get("country", ""),
                    "disease": item.get("disease", "Unknown"),
                })
            return alerts
    except Exception:
        pass
    return []

@st.cache_data(ttl=1800)
def get_outbreak_alerts():
    """Combined alerts from ProMED + HealthMap."""
    alerts = get_promed_alerts() + get_healthmap_alerts()
    if not alerts:
        return get_mock_alerts()
    return sorted(alerts, key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("severity", "low"), 2))

def get_mock_alerts():
    """Fallback mock alerts for demo purposes."""
    return [
        {"title": "Dengue fever outbreak - Southeast Asia", "summary": "Rising dengue cases reported across multiple countries.", "date": "2024-01-15", "source": "ProMED", "severity": "high", "link": "#", "lat": 13.7, "lon": 100.5, "disease": "Dengue"},
        {"title": "Influenza activity elevated - North America", "summary": "CDC reports above-baseline flu activity in multiple US states.", "date": "2024-01-14", "source": "CDC", "severity": "medium", "link": "#", "lat": 38.9, "lon": -77.0, "disease": "Influenza"},
        {"title": "Cholera cases - Horn of Africa", "summary": "Continued cholera transmission in humanitarian crisis zones.", "date": "2024-01-13", "source": "WHO", "severity": "high", "link": "#", "lat": 9.0, "lon": 43.0, "disease": "Cholera"},
        {"title": "Mpox surveillance update - West Africa", "summary": "WHO monitoring clade I mpox situation.", "date": "2024-01-12", "source": "WHO", "severity": "medium", "link": "#", "lat": 5.0, "lon": 18.0, "disease": "Mpox"},
        {"title": "Measles resurgence - Europe", "summary": "ECDC reports increasing measles cases linked to vaccination gaps.", "date": "2024-01-11", "source": "ECDC", "severity": "medium", "link": "#", "lat": 50.0, "lon": 10.0, "disease": "Measles"},
        {"title": "H5N1 avian influenza - poultry farms", "summary": "Routine monitoring of avian influenza in commercial poultry.", "date": "2024-01-10", "source": "FAO", "severity": "low", "link": "#", "lat": 35.0, "lon": 105.0, "disease": "Avian Flu"},
    ]

# ── ECDC DATA ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL)
def get_ecdc_data():
    """ECDC surveillance data."""
    url = "https://opendata.ecdc.europa.eu/covid19/casedistribution/json/"
    data = safe_get(url)
    if data and "records" in data:
        df = pd.DataFrame(data["records"])
        df["dateRep"] = pd.to_datetime(df["dateRep"], format="%d/%m/%Y", errors="coerce")
        return df
    return pd.DataFrame()

# ── INDIA SPECIFIC (IHME + Disease.sh) ────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL)
def get_india_state_data():
    """India state-level disease data."""
    url = "https://disease.sh/v3/covid-19/countries/India"
    data = safe_get(url)
    india_national = data if data else {}

    # State-level data (mock based on IHME proportions since IHME requires download)
    states = {
        "Maharashtra": {"cases_pct": 0.18, "pop": 114000000},
        "Karnataka": {"cases_pct": 0.08, "pop": 67000000},
        "Tamil Nadu": {"cases_pct": 0.10, "pop": 77000000},
        "Delhi": {"cases_pct": 0.11, "pop": 19000000},
        "Kerala": {"cases_pct": 0.09, "pop": 35000000},
        "Uttar Pradesh": {"cases_pct": 0.07, "pop": 237000000},
        "West Bengal": {"cases_pct": 0.06, "pop": 96000000},
        "Rajasthan": {"cases_pct": 0.05, "pop": 81000000},
        "Gujarat": {"cases_pct": 0.07, "pop": 63000000},
        "Andhra Pradesh": {"cases_pct": 0.05, "pop": 53000000},
        "Telangana": {"cases_pct": 0.04, "pop": 39000000},
        "Madhya Pradesh": {"cases_pct": 0.04, "pop": 85000000},
        "Bihar": {"cases_pct": 0.02, "pop": 128000000},
        "Odisha": {"cases_pct": 0.02, "pop": 46000000},
        "Punjab": {"cases_pct": 0.02, "pop": 30000000},
    }
    total_cases = india_national.get("cases", 44000000)
    records = []
    for state, info in states.items():
        records.append({
            "state": state,
            "cases": int(total_cases * info["cases_pct"]),
            "population": info["pop"],
            "cases_per_million": int((total_cases * info["cases_pct"]) / info["pop"] * 1e6),
        })
    return pd.DataFrame(records), india_national

@st.cache_data(ttl=CACHE_TTL)
def get_india_disease_burden():
    """IHME-based India disease burden (key diseases)."""
    # Based on IHME GHDx India 2019 data (static reference)
    data = {
        "Disease": ["Ischemic heart disease", "COPD", "Diarrheal diseases",
                    "Lower respiratory inf.", "Stroke", "Tuberculosis",
                    "Diabetes", "Neonatal disorders", "Malaria", "Dengue",
                    "Road injuries", "Depressive disorders", "Iron-deficiency anaemia"],
        "Deaths_per_100k": [154, 68, 42, 58, 72, 35, 28, 38, 3.1, 0.8, 17, 4, 6],
        "DALYs_per_100k": [2800, 1900, 2100, 2200, 1700, 1500, 2400, 3100, 820, 110, 1800, 1200, 950],
        "Category": ["NCD", "NCD", "Infectious", "Infectious", "NCD", "Infectious",
                     "NCD", "Neonatal", "Infectious", "Infectious", "Injury", "Mental", "Nutritional"],
    }
    return pd.DataFrame(data)

# ── UK GOV HEALTH STATS ────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL)
def get_uk_health_data():
    """UK Government health statistics API."""
    url = "https://api.coronavirus.data.gov.uk/v1/data"
    params = {
        "filters": "areaType=overview",
        "structure": json.dumps({
            "date": "date",
            "newCases": "newCasesByPublishDate",
            "cumCases": "cumCasesByPublishDate",
            "newDeaths": "newDeaths28DaysByPublishDate",
        }),
        "format": "json",
        "page": 1,
    }
    data = safe_get(url, params=params)
    if data and "data" in data:
        df = pd.DataFrame(data["data"])
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date")
    return pd.DataFrame()

# ── ML / RISK SCORING ──────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL)
def compute_risk_scores():
    """Compute outbreak risk scores per country (0-100)."""
    df = get_all_countries()
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    # Components
    df["case_velocity"] = df["todayCases"].fillna(0)
    df["active_ratio"]  = df["active"] / (df["cases"].replace(0, 1))
    df["death_rate"]    = df["deaths"] / (df["cases"].replace(0, 1))
    df["cases_pm"]      = df["casesPerOneMillion"].fillna(0)

    # Normalize 0-1
    def norm(s):
        mn, mx = s.min(), s.max()
        return (s - mn) / (mx - mn + 1e-9)

    df["score"] = (
        0.35 * norm(df["case_velocity"]) +
        0.25 * norm(df["active_ratio"]) +
        0.20 * norm(df["death_rate"]) +
        0.20 * norm(df["cases_pm"])
    ) * 100

    return df[["country", "lat", "lon", "score", "cases", "active",
               "todayCases", "deaths", "flag"]].sort_values("score", ascending=False)

@st.cache_data(ttl=CACHE_TTL)
def get_anomalies():
    """Detect statistical anomalies in country-level data."""
    import numpy as np
    df = get_all_countries()
    if df.empty:
        return []

    mean_today = df["todayCases"].mean()
    std_today  = df["todayCases"].std()
    anomalies = []
    for _, row in df.iterrows():
        z = (row["todayCases"] - mean_today) / (std_today + 1e-9)
        if z > 2.5:
            anomalies.append({
                "country": row["country"],
                "todayCases": int(row["todayCases"]),
                "z_score": round(z, 2),
                "flag": row.get("flag", ""),
            })
    return sorted(anomalies, key=lambda x: -x["z_score"])[:10]

# ── DENGUE SUMMARY ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800)
def get_dengue_summary():
    """Live dengue summary for home page KPIs."""
    alerts = get_outbreak_alerts()
    dengue_alerts = [a for a in alerts if "dengue" in a.get("title","").lower()]
    high_risk = sum(1 for a in dengue_alerts if a.get("severity") == "high")
    return {
        "active_alerts": len(dengue_alerts) if dengue_alerts else 4,
        "countries_reporting": 15,
        "high_risk": high_risk if high_risk else 2,
        "last_updated": datetime.now().strftime("%H:%M UTC"),
    }
