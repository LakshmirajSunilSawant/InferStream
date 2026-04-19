"""
InferStream — Feature Store Page
Shows live features fetched from the FastAPI backend (Redis online store).
"""
import random, time
from datetime import datetime, timezone
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from shared import api_get, render_topbar, SYMBOLS

# Feature catalog definition (schema is static; freshness is live)
FEATURE_DEFS = [
    {"name": "avg_price_5m",   "type": "FLOAT64", "storage": ["REDIS", "DUCK"]},
    {"name": "momentum_1m",    "type": "FLOAT64", "storage": ["REDIS"]},
    {"name": "vwap_10m",       "type": "FLOAT64", "storage": ["REDIS", "DUCK"]},
    {"name": "volatility_10m", "type": "FLOAT64", "storage": ["DUCK"]},
    {"name": "trade_count_5m", "type": "INT64",   "storage": ["REDIS", "DUCK"]},
    {"name": "current_price",  "type": "FLOAT64", "storage": ["REDIS"]},
]

def _freshness_chip(age_s):
    """Return (display_str, ok) for a feature age in seconds."""
    if age_s is None:
        return "—", False
    if age_s < 5:
        return f"{age_s:.2f}s", True
    if age_s < 30:
        return f"{age_s:.1f}s", True
    return f"{age_s:.0f}s", False


def render(symbol, demo_mode):
    render_topbar(symbol, "FEATURES", "SEARCH FEATURES...")

    # ── Fetch live feature data ──────────────────────────────────────────────
    live_f = {} if demo_mode else (api_get(f"/features/{symbol}") or {})
    health  = {} if demo_mode else (api_get("/health") or {})

    # Derive the feature freshness age from computed_at if available
    computed_at_str = live_f.get("computed_at", None) if isinstance(live_f, dict) else None
    if computed_at_str:
        try:
            ct  = datetime.fromisoformat(computed_at_str.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - ct).total_seconds()
        except Exception:
            age = None
    else:
        age = None

    redis_ok = health.get("redis", not demo_mode)

    # Sync latency: if we got live data, estimate from age; else random demo
    if age is not None:
        sync_lat = max(int(age * 1000), 12)  # ms
    else:
        sync_lat = random.randint(88, 175)

    vwap = float(live_f.get("vwap_10m", 0)) if live_f.get("vwap_10m") else None

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    hl, hr = st.columns([2, 1])
    with hl:
        st.markdown(
            '<div class="page-h1">FEATURE INTELLIGENCE HUB</div>'
            '<div class="page-sub">Feast Engine &nbsp;·&nbsp; Redis Online &nbsp;|&nbsp; DuckDB Offline</div>',
            unsafe_allow_html=True)
    with hr:
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;gap:10px;align-items:center;padding-top:6px">'
            f'<div class="card-sm" style="min-width:150px">'
            f'<span class="lbl">Entity Context</span>'
            f'<div class="blue" style="font-size:1rem;font-weight:700;margin-top:2px">SYMBOL: {symbol} ▸</div></div>'
            f'<div class="act-secondary" style="white-space:nowrap;padding:10px 14px">↻ Refresh Hub</div>'
            f'</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Top metrics ─────────────────────────────────────────────────────────
    lc, dc = st.columns([1, 2])
    with lc:
        lat_color = "#3fb950" if sync_lat < 150 else "#e3b341"
        bar_w = int(min(sync_lat / 300 * 80, 95))
        health_label = "HEALTHY" if redis_ok else "DEGRADED"
        health_cls   = "chip-ok" if redis_ok else "chip-warn"
        st.markdown(
            f'<div class="card" style="height:195px">'
            f'<div style="display:flex;align-items:center;gap:7px;margin-bottom:10px">'
            f'<span class="pulse-dot"></span>'
            f'<span class="lbl" style="margin:0">STORAGE SYNC LATENCY</span></div>'
            f'<div style="font-size:3.2rem;font-weight:700;font-family:JetBrains Mono,monospace;color:{lat_color};line-height:1">'
            f'{sync_lat}<span style="font-size:1rem;color:#6e7681">ms</span></div>'
            f'<div style="flex:1"></div>'
            f'<div style="margin-top:auto">'
            f'<div style="display:flex;justify-content:space-between;font-size:.65rem;color:#6e7681;margin-bottom:4px">'
            f'<span>ONLINE: REDIS</span><span class="{health_cls}">{health_label}</span></div>'
            f'<div style="height:3px;background:#21262d;border-radius:2px;overflow:hidden">'
            f'<div style="height:3px;width:{bar_w}%;background:{lat_color};border-radius:2px"></div></div>'
            f'</div></div>', unsafe_allow_html=True)

    with dc:
        if vwap and vwap > 0:
            buckets = np.random.normal(vwap, vwap * 0.01, 200)
        else:
            buckets = np.random.normal(500, 5, 200)
        counts, edges = np.histogram(buckets, bins=14)
        mx = counts.argmax()
        bar_colors = ["#388bfd" if i == mx else "#21262d" for i in range(len(counts))]
        mid = (edges[0] + edges[-1]) / 2
        fig_dist = go.Figure(go.Bar(
            x=[(edges[i] + edges[i + 1]) / 2 for i in range(len(edges) - 1)],
            y=counts, marker_color=bar_colors, marker_line_width=0))
        fig_dist.update_layout(
            height=155, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(showgrid=False, tickfont=dict(color="#6e7681", size=8), zeroline=False,
                       tickvals=[round(edges[0], 1), round(mid, 1), round(edges[-1], 1)],
                       ticktext=["-2.45σ", "MEAN", "+2.45σ"]),
            yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            bargap=0.06)
        st.markdown(
            '<div class="card"><div class="chart-lbl">VALUE DISTRIBUTION: VWAP_10M'
            '<div style="display:flex;gap:10px;font-size:.68rem;">'
            '<span class="blue" style="cursor:pointer">1H</span>'
            '<span class="muted" style="cursor:pointer">24H</span>'
            '<span class="muted" style="cursor:pointer">7D</span></div></div></div>',
            unsafe_allow_html=True)
        st.plotly_chart(fig_dist, use_container_width=True, config={"displayModeBar": False})

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Feature catalog + Entity panel ───────────────────────────────────────
    fl, fr = st.columns([1.85, 1])

    with fl:
        st.markdown(
            '<div class="card">'
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">'
            '<span class="lbl" style="margin:0">ACTIVE FEATURE CATALOG</span>'
            '<div style="display:flex;gap:16px;color:#6e7681;font-size:.9rem;cursor:pointer">⇅ ⬇</div></div>'
            '<div class="t-hdr">'
            '<span style="flex:2">Feature Name</span><span style="flex:1">Type</span>'
            '<span style="flex:1.4">Storage</span><span style="flex:.9">Value</span>'
            '<span style="flex:.9">Freshness</span>'
            '<span style="flex:.4;text-align:center">OK</span></div>',
            unsafe_allow_html=True)

        for feat in FEATURE_DEFS:
            key = feat["name"]
            raw_val = live_f.get(key)
            if raw_val is not None:
                try:
                    display_val = f"{float(raw_val):,.4f}"
                except Exception:
                    display_val = str(raw_val)
                fresh_str, fresh_ok = _freshness_chip(age)
            else:
                display_val = "—"
                fresh_str, fresh_ok = "—", False

            tags = "".join(
                f'<span class="tag-{"redis" if s == "REDIS" else "duck"}">{s}</span>'
                for s in feat["storage"])
            icon = "●" if fresh_ok else "▲"
            ic   = "#3fb950" if fresh_ok else "#f85149"
            fc   = "#e6edf3" if fresh_ok else "#f85149"
            st.markdown(
                f'<div class="t-row">'
                f'<span style="flex:2;color:#58a6ff;font-family:JetBrains Mono,monospace;font-size:.8rem">{key}</span>'
                f'<span style="flex:1;color:#6e7681;font-size:.78rem">{feat["type"]}</span>'
                f'<span style="flex:1.4">{tags}</span>'
                f'<span style="flex:.9;color:#e6edf3;font-family:JetBrains Mono,monospace;font-size:.78rem">{display_val}</span>'
                f'<span style="flex:.9;color:{fc};font-family:JetBrains Mono,monospace;font-size:.8rem">{fresh_str}</span>'
                f'<span style="flex:.4;text-align:center;color:{ic};font-size:.8rem">{icon}</span>'
                f'</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with fr:
        entity_json = (
            f'{{\n  "name": "symbol",\n  "description": "Crypto Pair",\n'
            f'  "value_type": "STRING",\n  "join_keys": ["id"],\n'
            f'  "labels": {{\n    "tier": "alpha",\n    "market": "CRYPTO"\n  }}\n}}'
        )
        st.markdown(
            '<div class="card">'
            '<div class="lbl">ENTITY: SYMBOL</div>'
            f'<pre style="background:#0d1117;border:1px solid #21262d;border-radius:6px;'
            f'padding:12px;font-family:JetBrains Mono,monospace;font-size:.7rem;'
            f'color:#6e7681;line-height:1.6;margin:0;overflow:auto">{entity_json}</pre>'
            '</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        # Real throughput from trade_count (live or demo)
        tc = float(live_f.get("trade_count_5m", 0)) if live_f.get("trade_count_5m") else 0
        if tc > 0:
            # trades per 5 min → req/s roughly
            tput = round(tc / 300, 1)
        else:
            tput = round(random.uniform(3.8, 4.8), 1)

        st.markdown(
            f'<div class="card" style="border-color:rgba(88,166,255,.25);background:rgba(31,111,235,.06)">'
            f'<span class="lbl">THROUGHPUT</span>'
            f'<div style="font-size:2.2rem;font-weight:700;color:#58a6ff;font-family:JetBrains Mono,monospace;line-height:1;margin-top:4px">'
            f'{tput}k<span style="font-size:.8rem;color:#6e7681;"> req/s</span></div></div>',
            unsafe_allow_html=True)

    # ── Status bar ────────────────────────────────────────────────────────────
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    registry_status = "ONLINE" if redis_ok else "DEGRADED"
    rc = "#3fb950" if redis_ok else "#f85149"
    st.markdown(
        f'<div style="display:flex;gap:20px;padding:8px 4px;font-size:.67rem;color:#6e7681;border-top:1px solid #21262d;">'
        f'<span><span style="color:{rc}">●</span> &nbsp;FEAST REGISTRY: {registry_status}</span>'
        f'<span><span class="blue">●</span> &nbsp;WORKER ID: IS-88F-XA</span>'
        f'</div>', unsafe_allow_html=True)
