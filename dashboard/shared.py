import os
import random
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
APP_NAME = "InferStream"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;0,900;1,700;1,900&family=JetBrains+Mono:wght@400;500;600;700&family=Space+Grotesk:wght@500;700;900&display=swap');

/* ── Design Tokens (DESIGN.md §7) ─────────────────────────────────────── */
:root {
  /* ── Primary ── */
  --color-primary: #85ADFF;
  --color-primary-container: #6E9FFF;
  --color-primary-dim: #699CFF;
  --color-primary-fixed: #6E9FFF;
  --color-primary-fixed-dim: #5391FF;
  --color-on-primary: #002C66;
  --color-on-primary-container: #002150;
  --color-inverse-primary: #005BC4;

  /* ── Secondary ── */
  --color-secondary: #69F6B8;
  --color-secondary-container: #006C49;
  --color-secondary-dim: #58E7AB;
  --color-on-secondary: #005A3C;
  --color-on-secondary-container: #E1FFEC;

  /* ── Tertiary ── */
  --color-tertiary: #FF6F7E;
  --color-tertiary-container: #FC4563;
  --color-tertiary-dim: #FF6F7E;
  --color-on-tertiary: #490010;
  --color-on-tertiary-container: #100001;

  /* ── Error ── */
  --color-error: #FF716C;
  --color-error-container: #9F0519;
  --color-error-dim: #D7383B;
  --color-on-error: #490006;
  --color-on-error-container: #FFA8A3;

  /* ── Surface ── */
  --color-surface: #0B0E14;
  --color-surface-dim: #0B0E14;
  --color-surface-bright: #282C36;
  --color-surface-container-lowest: #000000;
  --color-surface-container-low: #10131A;
  --color-surface-container: #161A21;
  --color-surface-container-high: #1C2028;
  --color-surface-container-highest: #22262F;
  --color-surface-variant: #22262F;
  --color-surface-tint: #85ADFF;

  /* ── Background & Foreground ── */
  --color-background: #0B0E14;
  --color-on-background: #ECEDF6;
  --color-on-surface: #ECEDF6;
  --color-on-surface-variant: #A9ABB3;
  --color-inverse-surface: #F9F9FF;
  --color-inverse-on-surface: #52555C;

  /* ── Outline ── */
  --color-outline: #73757D;
  --color-outline-variant: #45484F;

  /* ── Warning ── */
  --color-warning: #E3B341;

  /* ── Typography ── */
  --font-display: 'Space Grotesk', sans-serif;
  --font-body: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  /* ── Border Radius ── */
  --radius-sm: 0.125rem;
  --radius-default: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-full: 9999px;

  /* ── Shadows ── */
  --shadow-ambient: 0 0 40px rgba(236, 237, 246, 0.08);
  --shadow-glow-primary: 0 0 4px rgba(133, 173, 255, 0.2);
  --shadow-glow-primary-hover: 0 0 8px rgba(133, 173, 255, 0.35);

  /* ── Ghost Border ── */
  --border-ghost: 1px solid rgba(69, 72, 79, 0.2);
}

/* ── Reset & Base ─────────────────────────────────────────────────────── */
*{box-sizing:border-box;}
html,body,.stApp{background:var(--color-surface)!important;font-family:var(--font-body)!important;color:var(--color-on-surface)!important;}
.block-container{padding:0!important;max-width:100%!important;}
#MainMenu,footer,header{visibility:hidden!important;}
.stDeployButton,.viewerBadge_container__1QSob{display:none!important;}

/* ── Scrollbar ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:#0b0e14;}
::-webkit-scrollbar-thumb{background:#161a21;border-radius:4px;}

/* ── Sidebar ────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"]{background:#0b0e14!important;border-right:1px solid rgba(69,72,79,0.2)!important;min-width:220px!important;max-width:220px!important;}
[data-testid="stSidebar"]>div:first-child{padding-top:0!important;}

/* Nav buttons — active state indicator with smooth slide-in */
.stButton>button{
    background:transparent!important;border:none!important;color:#a9abb3!important;
    text-align:left!important;padding:9px 18px!important;font-size:0.84rem!important;
    font-weight:500!important;border-radius:0!important;letter-spacing:0.01em!important;
    border-left:3px solid transparent!important;width:100%!important;
    justify-content:flex-start!important;
    transition:color .18s ease, background .18s ease, border-left-color .18s ease, box-shadow .18s ease!important;
    position:relative!important;
}
.stButton>button:hover{
  color:#ecedf6!important;
  background:linear-gradient(90deg,rgba(133,173,255,0.06) 0%,transparent 100%)!important;
  border-left-color:#85adff!important;
  box-shadow:inset 3px 0 8px rgba(133,173,255,0.1)!important;
}
.stButton>button:focus{box-shadow:none!important;outline:none!important;}
.stButton>button:active{
  color:#85adff!important;
  border-left-color:#85adff!important;
  background:rgba(133,173,255,0.08)!important;
}

/* Selectbox / slider / toggle labels */
.stSelectbox label,.stSlider>label,.stToggle label{
    color:#a9abb3!important;font-size:0.7rem!important;letter-spacing:0.09em!important;
    font-weight:600!important;text-transform:uppercase!important;
}
div[data-baseweb="select"]>div{
  background:#161a21!important;border:none!important;border-bottom:1px solid #85adff!important;color:#ecedf6!important;
  box-shadow: 0 4px 12px rgba(133,173,255,0.05)!important;
  transition:border-color .2s ease!important;
}
div[data-baseweb="select"]>div:hover{border-color:#699cff!important;}
div[data-baseweb="select"] svg{color:#a9abb3!important;}

/* Slider — neon track accent */
.stSlider [data-testid="stSlider"] div[role="slider"]{
  background:#85adff!important;
  box-shadow:0 0 8px rgba(133,173,255,.5)!important;
  border:2px solid rgba(133,173,255,.6)!important;
  transition:box-shadow .2s ease!important;
}
.stSlider [data-testid="stSlider"] div[role="slider"]:hover{
  box-shadow:0 0 14px rgba(133,173,255,.8)!important;
}

/* Toggle — neon green when on */
[data-testid="stToggle"] div[role="checkbox"][aria-checked="true"]{
  background:#69f6b8!important;
  box-shadow:0 0 8px rgba(105,246,184,.4)!important;
}

/* ── Top Bar ────────────────────────────────────────────────────────────── */
.top-bar{
    background:#0b0e14;border-bottom:1px solid rgba(69,72,79,0.2);
    padding:11px 28px;display:flex;align-items:center;justify-content:space-between;gap:16px;
    position:sticky;top:0;z-index:100;
}
.search-box{
    background:#161a21;border:1px solid rgba(69,72,79,0.2);border-radius:0.25rem;padding:7px 13px;
    color:#a9abb3;font-size:0.81rem;font-family:'JetBrains Mono',monospace;
    min-width:170px;display:inline-flex;align-items:center;gap:8px;transition:border-color .2s;
}
.search-box:hover{border-color:rgba(69,72,79,0.5);}
.top-tabs{display:flex;gap:24px;align-items:center;}
.tab-item{color:#a9abb3;font-size:0.76rem;font-weight:600;letter-spacing:0.1em;padding-bottom:3px;cursor:pointer;transition:color .15s;}
.tab-item:hover{color:#ecedf6;}
.tab-active{color:#85adff!important;border-bottom:2px solid #85adff;}
.top-right{display:flex;align-items:center;gap:14px;color:#a9abb3;}
.top-icon{font-size:0.95rem;cursor:pointer;opacity:.7;transition:opacity .15s;}
.top-icon:hover{opacity:1;}
.sys-label{font-size:0.67rem;font-weight:600;color:#ecedf6;text-align:right;line-height:1.2;}
.sys-id{font-family:'JetBrains Mono',monospace;font-size:0.65rem;color:#a9abb3;}
.avatar{width:28px;height:28px;background:#161a21;border-radius:50%;border:1px solid rgba(69,72,79,0.2);display:flex;align-items:center;justify-content:center;font-size:0.72rem;cursor:pointer;}

/* ── Sidebar Brand ──────────────────────────────────────────────────────── */
.sb-brand{padding:20px 18px 0;display:flex;align-items:center;gap:9px;}
.sb-logo{font-size:1.2rem;line-height:1;}
.sb-title{font-family:'Space Grotesk',sans-serif;font-size:0.98rem;font-weight:800;font-style:italic;color:#85adff;letter-spacing:-0.02em;}
.sb-badge{margin:3px 18px 16px;font-size:0.63rem;font-weight:700;letter-spacing:0.14em;color:#69f6b8;display:flex;align-items:center;gap:5px;}
.sb-badge-dot{width:5px;height:5px;background:#69f6b8;border-radius:50%;animation:pulse 2s ease-in-out infinite;}
.sb-divider{height:1px;background:rgba(69,72,79,0.2);margin:4px 0;}
.sb-section{padding:6px 18px 2px;font-size:0.62rem;font-weight:700;letter-spacing:0.13em;color:#ecedf6;text-transform:uppercase;}
.sb-util{padding:8px 18px;color:#a9abb3;font-size:0.82rem;cursor:pointer;display:flex;align-items:center;gap:9px;transition:color .15s;}
.sb-util:hover{color:#ecedf6;}
.deploy-btn{
    margin:12px 16px 4px;background:#85adff;color:#002c66;border-radius:0.25rem;
    padding:9px 14px;font-weight:700;font-size:0.83rem;text-align:center;cursor:pointer;
    transition:background .15s;letter-spacing:0.02em;
    box-shadow:0 0 4px rgba(133,173,255,.2);
}
.deploy-btn:hover{background:#699cff;box-shadow:0 0 8px rgba(133,173,255,.4);}
.qlink{color:#a9abb3!important;font-size:0.77rem;text-decoration:none!important;display:block;padding:4px 18px;transition:color .15s;}
.qlink:hover{color:#85adff!important;}

/* ── Cards (Kinetic Observer) ───────────────────────────────────────────────── */
.card{
  background:#10131a;
  border:1px solid rgba(69,72,79,0.2);
  border-radius:0.25rem;
  padding:16px 18px;
  transition:background .2s ease, box-shadow .2s ease;
}
.card:hover{
  background:#161a21;
  box-shadow:0 10px 40px rgba(236,237,246,0.02);
}
.card-sm{
  background:#10131a;
  border:1px solid rgba(69,72,79,0.2);
  border-radius:0.25rem;
  padding:13px 16px;
}

/* ── HUD Specific ────────────────────────────────────────────────────────── */
.lbl{font-size:0.62rem;font-weight:700;letter-spacing:0.13em;color:#a9abb3;text-transform:uppercase;margin-bottom:8px;display:block;}
.live-badge{
  display:inline-flex;align-items:center;gap:5px;
  background:#006c49;border:none;
  border-radius:20px;padding:3px 9px;font-size:0.65rem;font-weight:700;
  color:#e1ffec;letter-spacing:.1em;
  box-shadow:0 0 8px rgba(105,246,184,.15);
  animation:badge-pulse 2s ease-in-out infinite;
}
.pulse-dot{width:6px;height:6px;background:#69f6b8;border-radius:50%;display:inline-block;animation:pulse 1.6s ease-in-out infinite;flex-shrink:0;box-shadow:0 0 4px #69f6b8;}
.pred-word{
  font-family:'Space Grotesk',sans-serif;font-size:3.5rem;font-weight:900;line-height:1;letter-spacing:-1px;
  text-shadow:0 0 24px currentColor;
  transition:color .4s ease, text-shadow .4s ease;
}
.signal-row{font-size:0.65rem;font-weight:700;letter-spacing:.12em;margin-top:5px;display:flex;align-items:center;gap:5px;}
.conf-bar-bg{height:4px;background:#161a21;border-radius:0px;margin-top:11px;overflow:hidden;}
.conf-bar-fill{height:100%;border-radius:0px;transition:width .6s cubic-bezier(.4,0,.2,1);}
.conf-lbl{font-size:0.62rem;letter-spacing:.12em;color:#a9abb3;font-weight:600;margin-bottom:2px;}
.conf-num{
  font-family:'Space Grotesk',sans-serif;font-size:2rem;font-weight:700;color:#ecedf6;
  line-height:1;
  text-shadow:0 0 12px rgba(236,237,246,0.2);
}
.conf-pct{font-size:0.85rem;color:#a9abb3;font-weight:400;}
.metric-big{
  font-family:'Space Grotesk',sans-serif;font-size:2.2rem;font-weight:700;
  color:#ecedf6;line-height:1.05;margin-top:4px;
  text-shadow:0 0 16px rgba(236,237,246,0.1);
  transition:color .3s ease;
}
.metric-unit{font-size:0.68rem;color:#a9abb3;font-weight:400;font-family:'Inter',sans-serif;}
.badge-green{font-size:0.68rem;font-weight:600;color:#69f6b8;margin-top:3px;text-shadow:0 0 6px rgba(105,246,184,.4);}
.badge-grey{font-size:0.68rem;font-weight:500;color:#a9abb3;margin-top:3px;}
.badge-red{font-size:0.68rem;font-weight:600;color:#fc4563;margin-top:3px;text-shadow:0 0 6px rgba(252,69,99,.4);}

/* ── Chart cards ────────────────────────────────────────────────────────── */
.chart-lbl{font-size:0.62rem;font-weight:700;letter-spacing:.13em;color:#a9abb3;text-transform:uppercase;margin-bottom:4px;display:flex;justify-content:space-between;align-items:center;}
.legend{display:flex;gap:10px;font-size:0.65rem;font-weight:600;color:#a9abb3;}
.leg-g::before{content:"●";color:#69f6b8;margin-right:4px;}
.leg-b::before{content:"●";color:#85adff;margin-right:4px;}

/* ── Page titles ─────────────────────────────────────────────────────────── */
.page-h1{font-family:'Space Grotesk',sans-serif;font-size:2.5rem;font-weight:900;color:#ecedf6;letter-spacing:-1.5px;line-height:1;}
.page-sub{font-size:0.68rem;font-weight:500;color:#a9abb3;letter-spacing:.1em;margin-top:4px;text-transform:uppercase;}

/* ── Tables ─────────────────────────────────────────────────────────────── */
.t-hdr{display:flex;padding:7px 12px;font-size:0.62rem;font-weight:700;letter-spacing:.1em;color:#a9abb3;text-transform:uppercase;border-bottom:1px solid rgba(69,72,79,0.2);}
.t-row{display:flex;align-items:center;padding:10px 12px;background:#0b0e14;border-radius:0.25rem;margin-bottom:4px;font-size:0.82rem;transition:background .15s;}
.t-row:hover{background:#10131a;}

/* ── Status chips ────────────────────────────────────────────────────────── */
.chip-ok{background:#006c49;color:#e1ffec;border:none;border-radius:0.25rem;padding:2px 9px;font-size:0.65rem;font-weight:700;letter-spacing:.05em;}
.chip-run{background:#282c36;color:#85adff;border:1px solid rgba(69,72,79,0.2);border-radius:0.25rem;padding:2px 9px;font-size:0.65rem;font-weight:700;letter-spacing:.05em;}
.chip-fail{background:#fc4563;color:#490010;border:none;border-radius:0.25rem;padding:2px 9px;font-size:0.65rem;font-weight:700;letter-spacing:.05em;}
.chip-warn{background:#282c36;color:#e3b341;border:1px solid rgba(69,72,79,0.2);border-radius:0.25rem;padding:2px 9px;font-size:0.65rem;font-weight:700;letter-spacing:.05em;}
.chip-prod{background:#006c49;color:#e1ffec;border-radius:0.25rem;padding:2px 9px;font-size:0.65rem;font-weight:700;letter-spacing:.05em;}
.chip-stag{background:#282c36;color:#85adff;border:1px solid rgba(69,72,79,0.2);border-radius:0.25rem;padding:2px 9px;font-size:0.65rem;font-weight:700;}
.chip-arch{background:#161a21;color:#a9abb3;border:1px solid rgba(69,72,79,0.2);border-radius:0.25rem;padding:2px 9px;font-size:0.65rem;font-weight:700;}

/* ── Feature tags ────────────────────────────────────────────────────────── */
.tag-redis{background:#006c49;color:#e1ffec;border-radius:0.25rem;padding:1px 6px;font-size:0.62rem;font-weight:700;margin-right:3px;}
.tag-duck{background:#282c36;color:#85adff;border-radius:0.25rem;padding:1px 6px;font-size:0.62rem;font-weight:700;margin-right:3px;}

/* ── Action buttons ──────────────────────────────────────────────────────── */
.act-primary{background:#85adff;color:#002c66;border-radius:0.25rem;padding:9px 12px;text-align:center;cursor:pointer;font-size:0.72rem;font-weight:700;letter-spacing:.04em;transition:background .15s;box-shadow:0 0 4px rgba(133,173,255,.2);}
.act-primary:hover{background:#699cff;}
.act-secondary{background:transparent;border:1px solid rgba(69,72,79,0.2);color:#85adff;border-radius:0.25rem;padding:9px 12px;text-align:center;cursor:pointer;font-size:0.72rem;font-weight:700;letter-spacing:.04em;transition:background .15s;}
.act-secondary:hover{background:#161a21;}
.act-danger{background:transparent;border:1px solid rgba(69,72,79,0.2);color:#fc4563;border-radius:0.25rem;padding:9px 12px;text-align:center;cursor:pointer;font-size:0.72rem;font-weight:700;letter-spacing:.04em;}

/* ── Misc ────────────────────────────────────────────────────────────────── */
.mono{font-family:'JetBrains Mono',monospace;}
.muted{color:#a9abb3;}
.green{color:#69f6b8;}
.blue{color:#85adff;}
.red{color:#fc4563;}
.warn{color:#e3b341;}

@keyframes pulse{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.3;transform:scale(.65);}}
@keyframes badge-pulse{0%,100%{box-shadow:0 0 8px rgba(105,246,184,.15);}50%{box-shadow:0 0 14px rgba(105,246,184,.3);}}
@keyframes glow-green{0%,100%{text-shadow:0 0 0 transparent;}50%{text-shadow:0 0 16px rgba(105,246,184,.5);}}
@keyframes slide-in{from{opacity:0;transform:translateY(4px);}to{opacity:1;transform:translateY(0);}}
@keyframes number-tick{from{opacity:.6;transform:translateY(2px);}to{opacity:1;transform:translateY(0);}}
.card{animation:slide-in .25s ease both;}

/* ── HUD Layout Components ──────────────────────────────────────────────── */
.hud-header{display:flex;justify-content:space-between;align-items:flex-start;}
.hud-body{display:flex;align-items:flex-end;gap:28px;margin-top:8px;}
.hud-body-main{flex:1;}
.hud-body-aside{text-align:right;flex-shrink:0;}

/* ── Metric Card Internals ──────────────────────────────────────────────── */
.metric-spacer{height:14px;}

/* ── Momentum Badge Card ────────────────────────────────────────────────── */
.momentum-card{
  display:flex;justify-content:space-between;align-items:center;padding:12px 16px;
}
.momentum-word{
  font-family:var(--font-display);font-size:1.4rem;font-weight:900;font-style:italic;
  transition:color .4s ease;
}
.momentum-ring{
  width:48px;height:48px;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font-family:var(--font-mono);font-size:0.95rem;font-weight:700;
  transition:border-color .4s ease, color .4s ease;
}

/* ── Footer Bar ─────────────────────────────────────────────────────────── */
.footer-bar{
  background:var(--color-surface);border-top:var(--border-ghost);
  padding:6px 24px;display:flex;justify-content:space-between;align-items:center;
  font-family:var(--font-mono);font-size:0.6rem;color:var(--color-on-surface-variant);
  letter-spacing:0.08em;margin-top:12px;
}

/* ── Glassmorphism Overlay ──────────────────────────────────────────────── */
.glass-overlay{
  background:rgba(34,38,47,0.7);
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
  border:var(--border-ghost);border-radius:var(--radius-lg);
}

/* ── Input Field ────────────────────────────────────────────────────────── */
.input-field{
  background:var(--color-surface-container-highest);color:var(--color-on-surface);
  font-family:var(--font-body);font-size:0.875rem;
  padding:0.625rem 0.875rem;border:none;
  border-bottom:1px solid transparent;border-radius:var(--radius-default);
  transition:all .2s ease;
}
.input-field:focus{
  outline:none;border-bottom-color:var(--color-primary);
  box-shadow:0 2px 8px rgba(105,156,255,0.15);
}

/* ── Terminal Field ─────────────────────────────────────────────────────── */
.terminal-field{
  background:var(--color-surface-container-lowest);color:var(--color-secondary);
  font-family:var(--font-mono);font-size:0.75rem;
  padding:1rem;border-radius:var(--radius-default);
}

/* ── Button Variants (DESIGN.md §5.1) ───────────────────────────────────── */
.btn-primary{
  background-color:var(--color-primary);color:var(--color-on-primary);
  font-family:var(--font-body);font-size:0.875rem;font-weight:500;
  padding:0.625rem 1.25rem;border:none;border-radius:var(--radius-default);
  box-shadow:var(--shadow-glow-primary);cursor:pointer;transition:all .2s ease;
}
.btn-primary:hover{box-shadow:var(--shadow-glow-primary-hover);}
.btn-secondary{
  background-color:transparent;color:var(--color-primary);
  font-family:var(--font-body);font-size:0.875rem;font-weight:500;
  padding:0.625rem 1.25rem;border:var(--border-ghost);border-radius:var(--radius-default);
  cursor:pointer;transition:all .2s ease;
}
.btn-secondary:hover{border-color:rgba(133,173,255,0.4);}
.btn-tertiary{
  background-color:transparent;color:var(--color-on-surface-variant);
  font-family:var(--font-body);font-size:0.875rem;font-weight:500;
  padding:0.625rem 1.25rem;border:none;border-radius:var(--radius-default);
  cursor:pointer;transition:all .2s ease;
}
.btn-tertiary:hover{background-color:var(--color-surface-bright);}
</style>
"""

def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)

def api_get(path, timeout=3.0):
    try:
        r = requests.get(f"{API_URL}{path}", timeout=timeout)
        return r.json() if r.ok else None
    except Exception:
        return None

def api_post(path, data, timeout=5.0):
    try:
        r = requests.post(f"{API_URL}{path}", json=data, timeout=timeout)
        return r.json() if r.ok else None
    except Exception:
        return None

def demo_features(symbol):
    base = {"BTCUSDT":68000,"ETHUSDT":3500,"SOLUSDT":150}
    p = base.get(symbol, 200) * (1 + random.gauss(0, 0.002))
    return {
        "avg_price_5m":   round(p, 2),
        "momentum_1m":    round(random.gauss(0, 0.005), 5),
        "vwap_10m":       round(p * (1 + random.gauss(0, 0.001)), 2),
        "volatility_10m": round(abs(random.gauss(0.5, 0.3)), 4),
        "trade_count_5m": random.randint(200, 4000),
        "current_price":  round(p * (1 + random.gauss(0, 0.0005)), 2),
    }

def demo_prediction(symbol, features):
    momentum = features.get("momentum_1m", 0)
    pred = "UP" if momentum >= 0 else "DOWN"
    conf = min(0.5 + abs(momentum) * 60, 0.97)
    return {
        "symbol": symbol, "prediction": pred,
        "confidence": round(conf, 4),
        "features": features,
        "model_version": "v1.0.42",
        "latency_ms": round(random.uniform(6, 42), 1),
    }

NAV_ITEMS = [
    ("Dashboard",      "⬡"),
    ("Feature Store",  "◈"),
    ("Model Registry", "⊞"),
    ("Monitoring",     "⌁"),
    ("API Docs",       "⊕"),
]

def render_topbar(symbol, active_tab="MODELS", placeholder=None):
    ph = placeholder or symbol
    tabs_html = "".join(
        f'<span class="tab-item {"tab-active" if t == active_tab else ""}">{t}</span>'
        for t in ["MODELS", "FEATURES", "LOGS"]
    )
    st.markdown(
        f'<div class="top-bar">'
        f'<div class="search-box"><span class="muted">⌕</span> {ph}</div>'
        f'<div class="top-tabs">{tabs_html}</div>'
        f'<div class="top-right">'
        f'<span class="top-icon">📡</span>'
        f'<span class="top-icon">🔔</span>'
        f'<span class="top-icon">⌨</span>'
        f'<div><div class="sys-label">SYSTEM ADMIN</div><div class="sys-id">IS-882-MLX</div></div>'
        f'<div class="avatar">👤</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

def render_sidebar(active_nav, symbol, rate, demo):
    with st.sidebar:
        # Brand
        st.markdown(
            '<div class="sb-brand">'
            '<span class="sb-logo">⚡</span>'
            '<span class="sb-title">InferStream</span>'
            '</div>'
            f'<div class="sb-badge">'
            f'<span class="sb-badge-dot"></span>SYSTEM: STABLE'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

        # Nav
        st.markdown('<div class="sb-section">Navigation</div>', unsafe_allow_html=True)
        new_nav = active_nav
        for label, icon in NAV_ITEMS:
            if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
                new_nav = label

        st.markdown('<div class="sb-divider" style="margin-top:8px"></div>', unsafe_allow_html=True)

        # Controls
        st.markdown('<div class="sb-section">Controls</div>', unsafe_allow_html=True)
        sym  = st.selectbox("Active Symbol", SYMBOLS,
                            index=SYMBOLS.index(symbol) if symbol in SYMBOLS else 0,
                            label_visibility="visible")
        rate_new = st.slider("Refresh (s)", 1, 10, rate)
        demo_new = st.toggle("Demo Mode", value=demo)

        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="deploy-btn">⬆ &nbsp;Deploy Model</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="sb-util"><span>⚙</span> Settings</div>'
            '<div class="sb-util"><span>?</span> Support</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sb-section">Quick Links</div>', unsafe_allow_html=True)
        for href, label in [
            ("http://localhost:8000/docs", "↗ API Docs"),
            ("http://localhost:5000",      "↗ MLflow"),
            ("http://localhost:3001",      "↗ Grafana"),
            ("http://localhost:8080",      "↗ Airflow"),
        ]:
            st.markdown(f'<a href="{href}" target="_blank" class="qlink">{label}</a>', unsafe_allow_html=True)

    return new_nav, sym, rate_new, demo_new
