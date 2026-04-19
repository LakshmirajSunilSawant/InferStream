"""
InferStream — Dashboard Page
Fetches live features and predictions from the FastAPI backend.
Falls back to demo mode if backend is unavailable.
"""
import time, pandas as pd
from datetime import datetime
from collections import deque
import streamlit as st
import plotly.graph_objects as go
from shared import demo_features, demo_prediction, api_get, api_post, render_topbar, SYMBOLS

# ── Helpers ──────────────────────────────────────────────────────────────────

def _normalize_radar(val, key, current_price):
    """Normalize feature values to [0,1] for radar chart, handling crypto prices."""
    if key == "momentum_1m":
        return min(abs(val) * 500, 1.0)
    if key in ("vwap_10m", "avg_price_5m", "current_price"):
        # normalize relative to current price so BTC/ETH/SOL all look right
        base = current_price if current_price > 1 else 100
        return min(abs(val / base), 1.0)
    if key == "volatility_10m":
        return min(val * 100, 1.0)
    if key == "trade_count_5m":
        return min(val / 5000, 1.0)
    return 0.0


def render(symbol, demo_mode):
    # ── Session state init ────────────────────────────────────────────────────
    for k, v in [("price_hist", {s: [] for s in SYMBOLS}),
                 ("lat_hist", deque(maxlen=60)), ("pred_hist", []), ("tick", 0)]:
        if k not in st.session_state:
            st.session_state[k] = v

    if symbol not in st.session_state.price_hist:
        st.session_state.price_hist[symbol] = []

    render_topbar(symbol, "MODELS")

    # ── Fetch live data ───────────────────────────────────────────────────────
    if demo_mode:
        f = demo_features(symbol)
        p = demo_prediction(symbol, f)
        health = {"redis": True, "mlflow": True, "bentoml": False, "model": "v1.0.42"}
        drift = {"drift_detected": False, "drift_score": 0.042}
    else:
        f = api_get(f"/features/{symbol}") or demo_features(symbol)
        p = api_post("/predict", {"symbol": symbol}) or demo_prediction(symbol, f)
        health = api_get("/health") or {}
        drift = api_get("/drift/report") or {"drift_detected": False, "drift_score": 0.0}

    px_now = float(f.get("current_price", f.get("avg_price_5m", 0)))
    mom    = float(f.get("momentum_1m", 0))
    lat    = float(p.get("latency_ms", 0))
    conf   = float(p.get("confidence", 0))
    pred   = str(p.get("prediction", "UP"))
    vwap   = float(f.get("vwap_10m", 0))
    ds     = float(drift.get("drift_score", 0.0))
    dflag  = bool(drift.get("drift_detected", False))
    model_ver = str(health.get("model", "unknown"))

    # ── Append to history ─────────────────────────────────────────────────────
    if px_now > 0:
        st.session_state.price_hist[symbol].append({"price": px_now})
    if len(st.session_state.price_hist[symbol]) > 120:
        st.session_state.price_hist[symbol].pop(0)
    st.session_state.lat_hist.append(lat)
    st.session_state.pred_hist.append({
        "symbol": symbol, "prediction": pred, "confidence": conf,
        "latency_ms": lat, "ts": datetime.now().strftime("%H:%M:%S")
    })
    if len(st.session_state.pred_hist) > 40:
        st.session_state.pred_hist.pop(0)
    st.session_state.tick += 1

    # ── Derived display values ────────────────────────────────────────────────
    pc   = "#69f6b8" if pred == "UP" else "#fc4563"
    sig  = "STRONG" if conf > 0.65 else "MODERATE"
    cpct = round(conf * 100, 1)
    ms   = ("+{:.3f}%".format(abs(mom * 100)) if mom >= 0 else "-{:.3f}%".format(abs(mom * 100)))
    dc   = "#fc4563" if dflag else "#69f6b8"

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── HUD Row ──────────────────────────────────────────────────────────────
    c_hud, c_px, c_lat, c_vwap, c_ds = st.columns([2.3, 1, 1, 1, 1])

    with c_hud:
        st.markdown(
            f'<div class="card" style="height:130px">'
            f'<div class="hud-header">'
            f'<span class="lbl" style="margin-bottom:0">INFERENCE HUD // {symbol}</span>'
            f'<span class="live-badge"><span class="pulse-dot"></span>{"LIVE" if not demo_mode else "DEMO"}</span></div>'
            f'<div class="hud-body">'
            f'<div class="hud-body-main">'
            f'<div class="pred-word" style="color:{pc}">{pred}</div>'
            f'<div class="signal-row" style="color:{pc}">'
            f'<span class="pulse-dot" style="background:{pc}"></span>SIGNAL: {sig}</div>'
            f'<div class="conf-bar-bg" style="margin-top:10px;">'
            f'<div class="conf-bar-fill" style="width:{cpct:.0f}%;background:{pc}"></div></div></div>'
            f'<div class="hud-body-aside">'
            f'<div class="conf-lbl">CONFIDENCE</div>'
            f'<div class="conf-num">{cpct}<span class="conf-pct">%</span></div></div>'
            f'</div></div>',
            unsafe_allow_html=True)

    cells = [
        ("PRICE (USD)",  f"{px_now:,.2f}", "",   ms,                                      "badge-green" if mom >= 0 else "badge-red"),
        ("P99 LATENCY",  f"{lat:.0f}",     "ms", "NOMINAL" if lat < 100 else "SLA BREACH","badge-grey" if lat < 100 else "badge-red"),
        ("VWAP (10M)",   f"{vwap:,.2f}",   "",   "WEIGHTED",                              "badge-grey"),
        ("DRIFT SCORE",  f"{ds:.3f}",      "",   "STABLE" if not dflag else "⚠ DRIFT",   "badge-green" if not dflag else "badge-red"),
    ]
    val_colors = ["#ECEDF6", "#ECEDF6", "#ECEDF6", dc]
    for col, ((lbl, val, unit, sub, sub_cls), vc) in zip([c_px, c_lat, c_vwap, c_ds], zip(cells, val_colors)):
        with col:
            st.markdown(
                f'<div class="card" style="height:130px">'
                f'<span class="lbl">{lbl}</span>'
                f'<div class="metric-spacer"></div>'
                f'<div class="metric-big" style="color:{vc}">'
                f'{val}<span class="metric-unit">{unit}</span></div>'
                f'<div class="{sub_cls}">{sub}</div></div>',
                unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Charts Row ────────────────────────────────────────────────────────────
    c_left, c_right = st.columns([1.45, 1])

    with c_left:
        ph = st.session_state.price_hist[symbol]
        fig = go.Figure()
        if len(ph) >= 2:
            prices = [x["price"] for x in ph]
            pred_l = pd.Series(prices).ewm(span=6).mean().tolist()
            fig.add_trace(go.Scatter(y=prices, mode="lines",
                                     line=dict(color="#69f6b8", width=1.8), name="ACTUAL",
                                     hovertemplate="$%{y:,.2f}<extra></extra>"))
            fig.add_trace(go.Scatter(y=pred_l, mode="lines",
                                     line=dict(color="#85adff", width=1.5, dash="dot"), name="EMA",
                                     hovertemplate="$%{y:,.2f}<extra></extra>"))
        fig.update_layout(
            height=185, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(69,72,79,0.2)",
                       tickfont=dict(color="#a9abb3", size=8), zeroline=False, tickprefix="$"),
            legend=dict(orientation="h", x=1, xanchor="right", y=1.18,
                        font=dict(color="#a9abb3", size=9), bgcolor="rgba(0,0,0,0)"),
            hoverdistance=20)
        st.markdown(
            '<div class="card"><div class="chart-lbl">REAL-TIME PRICE STREAM'
            '<div class="legend"><span class="leg-g">ACTUAL</span><span class="leg-b">EMA</span></div></div>'
            '<div style="position:relative;display:inline-block;width:100%">'
            '<div style="position:absolute;top:8px;left:12px;z-index:2;'
            'font-family:\'JetBrains Mono\',monospace;font-size:0.55rem;font-weight:700;'
            'color:rgba(133,173,255,0.35);letter-spacing:0.12em;pointer-events:none;">'
            'OSCILLOSCOPE LAYER ACTIVE</div>'
            '</div></div>',
            unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Latency sparkline
        ld = list(st.session_state.lat_hist)
        if ld:
            fl = go.Figure(go.Scatter(y=ld, mode="lines",
                                      line=dict(color="#85adff", width=1.4),
                                      fill="tozeroy", fillcolor="rgba(133,173,255,.05)"))
            fl.add_hline(y=100, line_dash="dot", line_color="#fc4563",
                         annotation_text="SLA", annotation_font_color="#fc4563", annotation_font_size=8)
            fl.update_layout(
                height=82, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(69,72,79,0.2)",
                           tickfont=dict(color="#a9abb3", size=7), zeroline=False))
            st.markdown('<div class="card" style="margin-top:10px"><div class="chart-lbl">P99 LATENCY HISTORY (ms)</div></div>',
                        unsafe_allow_html=True)
            st.plotly_chart(fl, use_container_width=True, config={"displayModeBar": False})

    with c_right:
        cats = ["MOMENTUM", "VWAP", "AVG PRICE", "VOLATILITY", "TRADE COUNT"]
        keys = ["momentum_1m", "vwap_10m", "avg_price_5m", "volatility_10m", "trade_count_5m"]
        vals = [_normalize_radar(float(f.get(k, 0)), k, px_now) for k in keys]
        fr = go.Figure(go.Scatterpolar(r=vals + [vals[0]], theta=cats + [cats[0]], fill="toself",
                                       fillcolor="rgba(133,173,255,.08)",
                                       line=dict(color="#85adff", width=1.8)))
        fr.update_layout(
            height=270,
            polar=dict(bgcolor="rgba(0,0,0,0)",
                       radialaxis=dict(visible=True, range=[0, 1],
                                       tickfont=dict(color="#a9abb3", size=7),
                                       gridcolor="rgba(69,72,79,0.2)", linecolor="rgba(69,72,79,0.2)"),
                       angularaxis=dict(tickfont=dict(color="#a9abb3", size=8),
                                        gridcolor="rgba(69,72,79,0.2)", linecolor="rgba(69,72,79,0.2)")),
            paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=24, r=24, t=24, b=24), showlegend=False)
        st.markdown('<div class="card"><div class="chart-lbl">FEATURE VECTOR ANALYSIS</div></div>',
                    unsafe_allow_html=True)
        st.plotly_chart(fr, use_container_width=True, config={"displayModeBar": False})

        # Momentum badge
        mom_lbl   = "AGGRESSIVE" if abs(mom) > 0.003 else ("MODERATE" if abs(mom) > 0.001 else "NEUTRAL")
        mom_score = min(int(abs(mom) * 20000), 99)
        st.markdown(
            f'<div class="card momentum-card" style="margin-top:10px;">'
            f'<div><span class="lbl" style="margin-bottom:4px">MOMENTUM</span>'
            f'<div class="momentum-word" style="color:{pc}">{mom_lbl}</div></div>'
            f'<div class="momentum-ring" style="border:2.5px solid {pc};color:{pc}">{mom_score}</div>'
            f'</div>', unsafe_allow_html=True)

    # ── System footer bar ──────────────────────────────────────────────────────
    _ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    _tick = st.session_state.get("tick", 0)
    st.markdown(
        f'<div class="footer-bar">'
        f'<span>BUILD v1.0.1-prod · INFERSTREAM INFERSTREAM</span>'
        f'<span>RUNTIME: PYTHON 3.11 · FASTAPI / UVICORN</span>'
        f'<span>REGION: LOCAL · SYS-882 · TICK #{_tick:,}</span>'
        f'<span>{_ts}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
