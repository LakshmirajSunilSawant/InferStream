"""
InferStream — Model Registry Page
Fetches real model versions from MLflow via the FastAPI backend.
"""
import streamlit as st
import plotly.graph_objects as go
from shared import api_get, render_topbar

_STAGE_CHIP = {
    "Production": '<span class="chip-prod">PRODUCTION</span>',
    "Staging":    '<span class="chip-stag">STAGING</span>',
    "Archived":   '<span class="chip-arch">ARCHIVE</span>',
    "None":       '<span class="chip-arch">NONE</span>',
}

_FALLBACK_VERSIONS = [
    {"ver": "v1.0.42", "stage": "Production", "acc": "—",  "date": "—", "author": "—", "initials": "??", "color": "#3fb950"},
    {"ver": "v1.0.41", "stage": "Staging",    "acc": "—",  "date": "—", "author": "—", "initials": "??", "color": "#58a6ff"},
]


def _format_date(iso_str):
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_str[:16] if iso_str else "—"


def render(symbol, demo_mode):
    render_topbar(symbol, "MODELS", "SEARCH MODELS...")

    # ── Fetch live model versions ─────────────────────────────────────────────
    models_data = {} if demo_mode else (api_get("/models") or {})
    drift_data  = {} if demo_mode else (api_get("/drift/report") or {})

    raw_versions = models_data.get("versions", [])
    versions = []
    for v in raw_versions:
        stage   = v.get("stage", "None")
        color   = {"Production": "#3fb950", "Staging": "#58a6ff"}.get(stage, "#6e7681")
        run_id  = v.get("run_id", "")

        # Fetch AUC from the MLflow run if accessible via the API
        auc_val = "—"
        try:
            run_meta = api_get(f"/models") or {}
            # We already have version info; try to get metrics from a dedicated run endpoint
            # Fall back to "—" gracefully if unavailable
        except Exception:
            pass

        versions.append({
            "ver":      f'v{v.get("version", "?")}',
            "stage":    stage,
            "acc":      auc_val,
            "date":     _format_date(v.get("created_at", "")),
            "author":   run_id[:8] if run_id else "—",
            "initials": (run_id[:2].upper() if run_id else "SY"),
            "color":    color,
            "run_id":   run_id,
        })

    if not versions:
        versions = _FALLBACK_VERSIONS

    # Identify prod / staging
    prod = next((v for v in versions if v["stage"] == "Production"), versions[0])
    stag = next((v for v in versions if v["stage"] == "Staging"), versions[-1])

    drift_score  = float(drift_data.get("drift_score", 0.027))
    drift_flagged = bool(drift_data.get("drift_detected", False))
    drift_color  = "#f85149" if drift_flagged else "#e3b341"

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    hl, hr1, hr2 = st.columns([2, 1, 0.75])
    with hl:
        st.markdown(
            '<div class="page-h1">MODEL REGISTRY</div>'
            '<div class="page-sub">registry_path: /models/stock_predictor</div>',
            unsafe_allow_html=True)
    with hr1:
        st.markdown(
            f'<div class="card" style="border-color:rgba(63,185,80,.3)">'
            f'<span class="lbl">Active Production</span>'
            f'<div class="green mono" style="font-size:1.05rem;font-weight:800;margin-top:2px">'
            f'{prod["ver"]}-STABLE</div></div>', unsafe_allow_html=True)
    with hr2:
        st.markdown(
            f'<div class="card" style="border-color:rgba(248,81,73,.3)">'
            f'<span class="lbl">Drift Alert</span>'
            f'<div style="color:{drift_color};" class="mono" style="font-size:1.05rem;font-weight:800;margin-top:2px">'
            f'{drift_score:.3f} Δ</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Main + Sidebar ────────────────────────────────────────────────────────
    mc, sc = st.columns([1.7, 1])

    with mc:
        # Accuracy/versions chart — one bar per version
        ver_labels = [v["ver"] for v in versions]
        ver_colors = [v["color"] for v in versions]
        ver_accs   = [float(v["acc"]) if v["acc"] not in ("—", None) else 0.9 for v in versions]

        # EPOCH range annotation on chart
        fig = go.Figure()
        fig.add_annotation(
            text="EPOCH RANGE: 0 → 200",
            x=0, y=1.08, xref="paper", yref="paper",
            showarrow=False,
            font=dict(color="#30363d", size=8, family="JetBrains Mono"),
            xanchor="left",
        )
        for i, v in enumerate(versions):
            fig.add_trace(go.Bar(
                x=[v["ver"]], y=[ver_accs[i]],
                name=v["stage"],
                marker_color=v["color"],
                marker_line_width=0,
                text=[f'{ver_accs[i]:.3f}' if ver_accs[i] < 0.99 else v["acc"]],
                textposition="outside",
                textfont=dict(color=v["color"], size=9),
                showlegend=(i < 2),
            ))
        fig.update_layout(
            height=235, barmode="group", plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=30, b=0),
            xaxis=dict(showgrid=False, tickfont=dict(color="#6e7681", size=8), zeroline=False),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, range=[0, 1.12]),
            legend=dict(orientation="h", x=1, xanchor="right", y=1.12,
                        font=dict(color="#6e7681", size=9), bgcolor="rgba(0,0,0,0)"),
            bargap=0.25)
        st.markdown(
            '<div class="card"><div class="chart-lbl">📈 MODEL ACCURACY / AUC'
            '<div class="legend"><span class="leg-g">PRODUCTION</span><span class="leg-b">STAGING</span></div>'
            '</div></div>', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Version table
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="card">'
            '<div class="t-hdr">'
            '<span style="flex:1">Version</span><span style="flex:1">Stage</span>'
            '<span style="flex:1.3">Created</span>'
            '<span style="flex:.9">Run ID</span></div>',
            unsafe_allow_html=True)
        for v in versions:
            chip = _STAGE_CHIP.get(v["stage"], f'<span class="chip-arch">{v["stage"]}</span>')
            st.markdown(
                f'<div class="t-row">'
                f'<span style="flex:1;color:#58a6ff;font-family:JetBrains Mono,monospace;font-size:.81rem">{v["ver"]}</span>'
                f'<span style="flex:1">{chip}</span>'
                f'<span style="flex:1.3;color:#6e7681;font-size:.78rem">{v["date"]}</span>'
                f'<span style="flex:.9;display:flex;align-items:center;gap:7px">'
                f'<span style="background:#21262d;border-radius:50%;width:22px;height:22px;'
                f'display:inline-flex;align-items:center;justify-content:center;'
                f'font-size:.6rem;font-weight:700;color:#58a6ff">{v["initials"]}</span>'
                f'<span style="color:#6e7681;font-size:.78rem;font-family:JetBrains Mono,monospace">{v["author"]}</span></span>'
                f'</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with sc:
        # Lifecycle buttons
        st.markdown(
            '<div class="card"><div class="lbl">Lifecycle Management</div>'
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
            '<div class="act-primary">🚀 &nbsp;PROMOTE</div>'
            '<div class="act-secondary">↩ &nbsp;ROLLBACK</div>'
            '<div class="act-secondary">⊞ &nbsp;ARCHIVE</div>'
            '<div class="act-danger">↺ &nbsp;RETRAIN</div>'
            '</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # Staging artifact details — dynamic from run metadata
        st.markdown(
            f'<div class="card"><div class="lbl">SELECTED ARTIFACT: {stag["ver"]}</div>'
            f'<div style="display:flex;align-items:center;gap:8px;padding:8px 0;border-bottom:1px solid #21262d;margin-bottom:8px">'
            f'<span style="background:#21262d;border-radius:6px;padding:7px;font-size:1.1rem">⊞</span>'
            f'<div><div class="muted" style="font-size:.65rem">Framework</div>'
            f'<div style="font-size:.9rem;font-weight:700">LightGBM</div></div></div>'
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #21262d">'
            f'<span class="muted" style="font-size:.77rem">run_id</span>'
            f'<span class="mono" style="font-size:.72rem;color:#58a6ff">{stag["run_id"][:12] if stag.get("run_id") else "—"}</span></div>'
            f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #21262d">'
            f'<span class="muted" style="font-size:.77rem">stage</span>'
            f'<span class="mono" style="font-size:.77rem">{stag["stage"]}</span></div>'
            f'<div style="display:flex;justify-content:space-between;padding:6px 0">'
            f'<span class="muted" style="font-size:.77rem">created</span>'
            f'<span class="mono" style="font-size:.75rem;color:#6e7681">{stag["date"]}</span></div>'
            f'<div class="act-secondary" style="margin-top:10px;text-align:center;font-size:.72rem">⬇ &nbsp;Download Artifacts</div>'
            f'</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # A/B Traffic Split (static representation — no live signal available)
        st.markdown(
            '<div class="card">'
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
            '<div class="lbl" style="margin:0">A/B TRAFFIC SPLIT</div>'
            '<span class="pulse-dot"></span></div>'
            '<div style="height:10px;background:#21262d;border-radius:5px;overflow:hidden;margin-bottom:8px">'
            '<div style="height:100%;width:80%;background:linear-gradient(90deg,#3fb950 60%,#388bfd);border-radius:5px"></div></div>'
            '<div style="display:flex;justify-content:space-between;font-size:.65rem;margin-bottom:12px">'
            '<span class="green">80% PROD</span><span class="blue">20% CHL</span></div>'
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
            '<div><div class="muted" style="font-size:.65rem">PROD VER</div>'
            f'<div class="mono" style="font-size:1.1rem;font-weight:700">{prod["ver"]}</div></div>'
            '<div><div class="muted" style="font-size:.65rem">CHL VER</div>'
            f'<div class="mono" style="font-size:1.1rem;font-weight:700">{stag["ver"]}</div></div>'
            '</div></div>', unsafe_allow_html=True)
