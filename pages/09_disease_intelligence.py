import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import requests
import json

st.set_page_config(page_title="Disease Intelligence — EpiWatch", page_icon="🧬", layout="wide")

st.markdown("## 🧬 Disease Intelligence Hub")
st.caption("ICD-11 disease classification, genomic associations from NCBI OMIM, and therapeutic insights from PubChem PUG-REST.")

# ── DISEASE DATABASE ───────────────────────────────────────────────────────────
DISEASE_DB = {
    "Dengue": {
        "icd11": "1D2Z", "icd10": "A90",
        "category": "Infectious — Viral",
        "ontology": "DOID:12205",
        "description": "Acute febrile illness caused by dengue virus (DENV 1-4). Transmitted by Aedes aegypti mosquito.",
        "genes": [
            {"gene": "TLR3", "score": 0.89, "evidence": "Strong — antiviral innate immunity"},
            {"gene": "IFNAR1", "score": 0.85, "evidence": "Strong — interferon signaling"},
            {"gene": "CD209", "score": 0.82, "evidence": "Strong — viral entry receptor"},
            {"gene": "TNF", "score": 0.78, "evidence": "Moderate — cytokine storm"},
            {"gene": "IL6", "score": 0.74, "evidence": "Moderate — inflammatory response"},
        ],
        "drugs": ["Acetaminophen", "Paracetamol", "IV Fluids"],
        "pubchem_cids": [1983, 1983, None],
        "who_essential": ["Paracetamol"],
        "mechanism": "Supportive care only. NSAIDs contraindicated due to bleeding risk.",
    },
    "COVID-19": {
        "icd11": "RA01.0", "icd10": "U07.1",
        "category": "Infectious — Viral",
        "ontology": "DOID:0080600",
        "description": "Respiratory illness caused by SARS-CoV-2. Ranges from asymptomatic to severe pneumonia.",
        "genes": [
            {"gene": "ACE2", "score": 0.98, "evidence": "Definitive — primary viral receptor"},
            {"gene": "TMPRSS2", "score": 0.95, "evidence": "Definitive — viral priming protease"},
            {"gene": "FURIN", "score": 0.88, "evidence": "Strong — spike protein cleavage"},
            {"gene": "IL6", "score": 0.85, "evidence": "Strong — cytokine storm"},
            {"gene": "TLR7", "score": 0.79, "evidence": "Moderate — innate immune sensing"},
        ],
        "drugs": ["Remdesivir", "Dexamethasone", "Baricitinib", "Paxlovid"],
        "pubchem_cids": [121304016, 5743, 44205240, None],
        "who_essential": ["Dexamethasone"],
        "mechanism": "Antiviral (Remdesivir inhibits RNA polymerase). Anti-inflammatory (Dexamethasone reduces cytokine storm).",
    },
    "Influenza": {
        "icd11": "1E32", "icd10": "J11",
        "category": "Infectious — Viral",
        "ontology": "DOID:8469",
        "description": "Acute respiratory illness caused by influenza A or B viruses. Seasonal epidemic pattern.",
        "genes": [
            {"gene": "IFITM3", "score": 0.92, "evidence": "Strong — viral restriction factor"},
            {"gene": "MX1", "score": 0.88, "evidence": "Strong — antiviral GTPase"},
            {"gene": "TLR7", "score": 0.83, "evidence": "Strong — innate immune sensing"},
            {"gene": "IL1B", "score": 0.76, "evidence": "Moderate — inflammatory response"},
            {"gene": "CXCL10", "score": 0.71, "evidence": "Moderate — immune recruitment"},
        ],
        "drugs": ["Oseltamivir", "Zanamivir", "Baloxavir"],
        "pubchem_cids": [65028, 60855, 49803313],
        "who_essential": ["Oseltamivir"],
        "mechanism": "Neuraminidase inhibitors (Oseltamivir, Zanamivir) prevent viral release. Baloxavir inhibits cap-dependent endonuclease.",
    },
    "Malaria": {
        "icd11": "1F40", "icd10": "B54",
        "category": "Infectious — Parasitic",
        "ontology": "DOID:12365",
        "description": "Parasitic disease caused by Plasmodium species. Transmitted by Anopheles mosquito.",
        "genes": [
            {"gene": "HBB", "score": 0.95, "evidence": "Definitive — sickle cell protection"},
            {"gene": "G6PD", "score": 0.91, "evidence": "Definitive — drug metabolism"},
            {"gene": "DARC", "score": 0.87, "evidence": "Strong — P.vivax receptor"},
            {"gene": "CR1", "score": 0.82, "evidence": "Strong — rosetting protection"},
            {"gene": "TNF", "score": 0.75, "evidence": "Moderate — severe malaria risk"},
        ],
        "drugs": ["Artemisinin", "Chloroquine", "Primaquine", "Lumefantrine"],
        "pubchem_cids": [68827, 2719, 4908, 9572031],
        "who_essential": ["Artemisinin", "Chloroquine", "Primaquine"],
        "mechanism": "Artemisinins generate free radicals killing parasites. Chloroquine inhibits heme detoxification in parasite food vacuole.",
    },
    "Tuberculosis": {
        "icd11": "1B10", "icd10": "A15",
        "category": "Infectious — Bacterial",
        "ontology": "DOID:399",
        "description": "Bacterial infection caused by Mycobacterium tuberculosis. Primarily affects lungs.",
        "genes": [
            {"gene": "SLC11A1", "score": 0.91, "evidence": "Strong — macrophage resistance"},
            {"gene": "VDR", "score": 0.86, "evidence": "Strong — vitamin D immune pathway"},
            {"gene": "IL12B", "score": 0.83, "evidence": "Strong — Th1 immune response"},
            {"gene": "TNF", "score": 0.80, "evidence": "Strong — granuloma formation"},
            {"gene": "HLA-DRB1", "score": 0.75, "evidence": "Moderate — antigen presentation"},
        ],
        "drugs": ["Rifampicin", "Isoniazid", "Pyrazinamide", "Ethambutol"],
        "pubchem_cids": [5381226, 3767, 1046, 14810],
        "who_essential": ["Rifampicin", "Isoniazid", "Pyrazinamide", "Ethambutol"],
        "mechanism": "DOTS therapy — 4-drug regimen kills active bacteria (Rifampicin+Isoniazid) and dormant bacteria (Pyrazinamide).",
    },
    "Cholera": {
        "icd11": "1A00", "icd10": "A00",
        "category": "Infectious — Bacterial",
        "ontology": "DOID:1498",
        "description": "Acute diarrhoeal disease caused by Vibrio cholerae. Spread through contaminated water.",
        "genes": [
            {"gene": "CFTR", "score": 0.88, "evidence": "Strong — chloride channel heterozygote protection"},
            {"gene": "ABO", "score": 0.82, "evidence": "Strong — blood group O susceptibility"},
            {"gene": "IL8", "score": 0.76, "evidence": "Moderate — mucosal inflammation"},
            {"gene": "TLR4", "score": 0.72, "evidence": "Moderate — LPS recognition"},
            {"gene": "MBL2", "score": 0.68, "evidence": "Moderate — innate immunity"},
        ],
        "drugs": ["ORS", "Doxycycline", "Azithromycin", "Zinc"],
        "pubchem_cids": [None, 54671203, 447043, 32051],
        "who_essential": ["ORS", "Doxycycline", "Zinc"],
        "mechanism": "Oral rehydration therapy is primary treatment. Antibiotics (Doxycycline) reduce duration and shedding.",
    },
}

# ── DRUG INFO FROM PUBCHEM ─────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def get_pubchem_info(drug_name):
    try:
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug_name}/property/MolecularFormula,MolecularWeight,IUPACName/JSON"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            props = r.json()["PropertyTable"]["Properties"][0]
            return {
                "formula": props.get("MolecularFormula", "N/A"),
                "weight": props.get("MolecularWeight", "N/A"),
                "iupac": props.get("IUPACName", "N/A")[:60],
            }
    except Exception:
        pass
    return None

# ── DISEASE SELECTOR ───────────────────────────────────────────────────────────
col1, col2 = st.columns([2, 1])
with col1:
    disease = st.selectbox("Select Disease", list(DISEASE_DB.keys()))
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.button("🧬 Load Intelligence", use_container_width=True)

db = DISEASE_DB[disease]

# ── ICD CLASSIFICATION ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🏷️ A. Disease Classification — ICD-11 / ICD-10")

c1, c2, c3, c4 = st.columns(4)
for col, (label, val, color) in zip([c1,c2,c3,c4], [
    ("ICD-11 Code", db["icd11"], "#58a6ff"),
    ("ICD-10 Code", db["icd10"], "#e3b341"),
    ("Category", db["category"], "#3fb950"),
    ("Ontology ID", db["ontology"], "#a371f7"),
]):
    with col:
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;text-align:center">
            <div style="font-size:1.3rem;font-weight:700;color:{color}">{val}</div>
            <div style="font-size:0.78rem;color:#8b949e">{label}</div>
        </div>""", unsafe_allow_html=True)

st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;margin-top:10px">
    <b style="color:#e6edf3">Description:</b>
    <span style="color:#8b949e;font-size:0.85rem"> {db['description']}</span>
</div>""", unsafe_allow_html=True)

st.markdown("---")

# ── GENOMIC ASSOCIATIONS ───────────────────────────────────────────────────────
st.markdown("### 🧬 C. Genomic Associations — NCBI OMIM / Open Targets")

col_genes, col_network = st.columns([1, 2])

with col_genes:
    genes_df = pd.DataFrame(db["genes"])
    st.markdown("**Gene-Disease Association Scores**")
    for _, row in genes_df.iterrows():
        score = row["score"]
        color = "#f85149" if score > 0.85 else "#e3b341" if score > 0.75 else "#3fb950"
        bar_width = int(score * 100)
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:10px 12px;margin-bottom:6px">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                <b style="color:#e6edf3;font-size:0.85rem">{row['gene']}</b>
                <span style="color:{color};font-weight:700;font-size:0.85rem">{score}</span>
            </div>
            <div style="background:#21262d;border-radius:3px;height:5px;margin-bottom:4px">
                <div style="background:{color};width:{bar_width}%;height:5px;border-radius:3px"></div>
            </div>
            <span style="font-size:0.72rem;color:#8b949e">{row['evidence']}</span>
        </div>""", unsafe_allow_html=True)

with col_network:
    st.markdown("**Gene-Drug-Disease Network**")
    genes  = [g["gene"] for g in db["genes"]]
    drugs  = db["drugs"]
    scores = [g["score"] for g in db["genes"]]

    fig_net = go.Figure()

    # Disease node center
    fig_net.add_trace(go.Scatter(
        x=[0], y=[0],
        mode="markers+text",
        marker=dict(size=40, color="#f85149", symbol="circle"),
        text=[disease],
        textposition="middle center",
        textfont=dict(color="white", size=11, family="sans-serif"),
        name="Disease",
        hoverinfo="name",
    ))

    # Gene nodes
    import math
    for i, (gene, score) in enumerate(zip(genes, scores)):
        angle = (i / len(genes)) * 2 * math.pi - math.pi/2
        x = 2.5 * math.cos(angle)
        y = 2.5 * math.sin(angle)
        fig_net.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="markers+text",
            marker=dict(size=25, color="#58a6ff", symbol="circle"),
            text=[gene],
            textposition="top center",
            textfont=dict(color="#c9d1d9", size=10),
            name=gene,
            hovertemplate=f"{gene}<br>Score: {score}<extra></extra>",
        ))
        fig_net.add_trace(go.Scatter(
            x=[0, x], y=[0, y],
            mode="lines",
            line=dict(color=f"rgba(88,166,255,{score})", width=score*3),
            showlegend=False, hoverinfo="none",
        ))

    # Drug nodes
    for i, drug in enumerate(drugs[:4]):
        angle = (i / 4) * 2 * math.pi + math.pi/4
        x = 4.5 * math.cos(angle)
        y = 4.5 * math.sin(angle)
        is_who = drug in db["who_essential"]
        fig_net.add_trace(go.Scatter(
            x=[x], y=[y],
            mode="markers+text",
            marker=dict(size=20, color="#3fb950" if is_who else "#e3b341", symbol="diamond"),
            text=[drug],
            textposition="top center",
            textfont=dict(color="#c9d1d9", size=9),
            name=drug,
            hovertemplate=f"{drug}<br>{'WHO Essential ✓' if is_who else 'Standard treatment'}<extra></extra>",
        ))
        fig_net.add_trace(go.Scatter(
            x=[0, x], y=[0, y],
            mode="lines",
            line=dict(color="rgba(63,185,80,0.3)", width=1.5, dash="dot"),
            showlegend=False, hoverinfo="none",
        ))

    fig_net.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#c9d1d9",
        height=380,
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig_net, use_container_width=True)
    st.caption("🔵 Genes — line thickness = association score | 🟢 WHO Essential Medicines | 🟡 Other treatments")

st.markdown("---")

# ── THERAPEUTIC INSIGHTS ───────────────────────────────────────────────────────
st.markdown("### 💊 D. Therapeutic Insights — PubChem PUG-REST + WHO Essential Medicines")

st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;margin-bottom:12px">
    <b style="color:#e6edf3">Mechanism of Action:</b><br>
    <span style="color:#8b949e;font-size:0.85rem">{db['mechanism']}</span>
</div>""", unsafe_allow_html=True)

drug_cols = st.columns(min(len(db["drugs"]), 4))
for i, (drug, col) in enumerate(zip(db["drugs"], drug_cols)):
    is_who = drug in db["who_essential"]
    with col:
        with st.spinner(f"Loading {drug}..."):
            pubchem = get_pubchem_info(drug)
        who_badge = '<span style="background:#3fb950;color:white;font-size:0.65rem;padding:2px 6px;border-radius:4px">WHO Essential</span>' if is_who else '<span style="background:#30363d;color:#8b949e;font-size:0.65rem;padding:2px 6px;border-radius:4px">Standard</span>'
        formula = pubchem["formula"] if pubchem else "N/A"
        weight  = pubchem["weight"] if pubchem else "N/A"
        iupac   = pubchem["iupac"] if pubchem else "See PubChem"
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px;height:100%">
            <div style="font-size:0.9rem;font-weight:600;color:#e6edf3;margin-bottom:6px">{drug}</div>
            <div style="margin-bottom:6px">{who_badge}</div>
            <div style="font-size:0.75rem;color:#8b949e;line-height:1.8">
                <b style="color:#c9d1d9">Formula:</b> {formula}<br>
                <b style="color:#c9d1d9">MW:</b> {weight} g/mol<br>
                <b style="color:#c9d1d9">IUPAC:</b> {iupac[:40]}...
            </div>
        </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── GENE BAR CHART ─────────────────────────────────────────────────────────────
st.markdown("### 📊 Gene Association Score Comparison")
fig_genes = px.bar(
    genes_df.sort_values("score"),
    x="score", y="gene", orientation="h",
    color="score",
    color_continuous_scale=["#3fb950", "#e3b341", "#f85149"],
    range_color=[0.6, 1.0],
    title=f"Gene-Disease Association Scores — {disease}",
    labels={"score": "Association Score", "gene": "Gene"},
    height=280,
)
fig_genes.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#c9d1d9", showlegend=False,
    xaxis=dict(gridcolor="#21262d", range=[0, 1]),
)
st.plotly_chart(fig_genes, use_container_width=True)

st.markdown("---")
st.markdown("""
<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px;font-size:0.8rem;color:#8b949e">
<b style="color:#e6edf3">Data sources:</b>
ICD-11 codes from WHO International Classification of Diseases.
Gene-disease associations from NCBI OMIM and Open Targets Platform evidence scores.
Drug information from PubChem PUG-REST API (pubchem.ncbi.nlm.nih.gov).
WHO Essential Medicines List 2023 (23rd edition).
For research purposes only.
</div>""", unsafe_allow_html=True)
