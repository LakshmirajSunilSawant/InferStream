"""InferStream — Multi-Page ML Dashboard"""
import time
import streamlit as st
from shared import inject_css, render_sidebar, SYMBOLS

st.set_page_config(
    page_title="InferStream",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

# ── Session defaults ──────────────────────────────────────────────────────────
for k, v in [("active_nav","Dashboard"),("selected_symbol","BTCUSDT"),
              ("refresh_rate",2),("demo_mode",False)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar (returns updated values) ─────────────────────────────────────────
new_nav, sym, rate, demo = render_sidebar(
    st.session_state.active_nav,
    st.session_state.selected_symbol,
    st.session_state.refresh_rate,
    st.session_state.demo_mode,
)
st.session_state.active_nav      = new_nav
st.session_state.selected_symbol = sym
st.session_state.refresh_rate    = rate
st.session_state.demo_mode       = demo

nav = st.session_state.active_nav

# ── Router ────────────────────────────────────────────────────────────────────
if nav == "Dashboard":
    import page_dashboard
    page_dashboard.render(sym, demo)

elif nav == "Feature Store":
    import page_feature_store
    page_feature_store.render(sym, demo)

elif nav == "Model Registry":
    import page_model_registry
    page_model_registry.render(sym, demo)

elif nav == "Monitoring":
    import page_monitoring
    page_monitoring.render(sym, demo)

elif nav == "API Docs":
    from shared import render_topbar
    render_topbar(sym, "LOGS")
    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="text-align:center;padding:60px 40px">'
        '<div style="font-size:2.5rem">📖</div>'
        '<div style="font-size:1.5rem;font-weight:800;font-style:italic;color:#58a6ff;margin-top:12px">API DOCUMENTATION</div>'
        '<div style="font-size:.82rem;color:#6e7681;margin-top:8px">Interactive Swagger docs via the InferStream FastAPI gateway</div>'
        '<div style="margin-top:24px;display:flex;justify-content:center;gap:12px">'
        '<a href="http://localhost:8000/docs" target="_blank" style="background:#1f6feb;color:#fff;border-radius:6px;'
        'padding:10px 22px;font-weight:600;text-decoration:none;font-size:.86rem">Open Swagger UI</a>'
        '<a href="http://localhost:8000/redoc" target="_blank" style="background:#21262d;color:#e6edf3;border:1px solid #30363d;'
        'border-radius:6px;padding:10px 22px;font-weight:600;text-decoration:none;font-size:.86rem">Open ReDoc</a>'
        '</div></div>',
        unsafe_allow_html=True)

# ── Auto-rerun: Dashboard only ────────────────────────────────────────────────
if nav == "Dashboard":
    time.sleep(rate)
    st.rerun()
