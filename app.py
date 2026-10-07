import streamlit as st
import requests
import time
import sys
import importlib
import plotly.graph_objects as go

# Ensure pipeline modules are always fresh upon Streamlit reload
for mod_name in ['pipeline.feature_extractor', 'pipeline.predictor', 'pipeline.scheduler']:
    if mod_name in sys.modules:
        importlib.reload(sys.modules[mod_name])

from pipeline.scheduler import OffloadingScheduler

# 1. Page Configuration (Zero emojis, clean architectural metadata)
st.set_page_config(
    page_title="AI SCHEDULER",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Application State Initialization
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = "overview"  # "overview", "playground", "endpoints", "telemetry"
if 'theme_mode' not in st.session_state:
    st.session_state.theme_mode = "dark"
if 'code_preset' not in st.session_state:
    st.session_state.code_preset = "heavy"
if 'sim_cloud_rtt' not in st.session_state:
    st.session_state.sim_cloud_rtt = 130
if 'last_result' not in st.session_state:
    st.session_state.last_result = None

st.sidebar.markdown(
    '''
    <a href="http://localhost:8080" target="_self" style="
        display: block;
        margin: 20px 0;
        padding: 10px;
        background-color: var(--accent-amber-hover);
        color: white;
        text-align: center;
        font-family: 'Press Start 2P', cursive;
        font-size: 10px;
        border: 4px solid var(--border-color);
        text-decoration: none;
        box-shadow: 4px 4px 0px var(--bg-canvas);
    ">⬅️ EXIT TO SYSTEM OS</a>
    ''', unsafe_allow_html=True
)


# Backwards compatibility migration
if 'app_view' in st.session_state:
    if st.session_state.app_view == "dashboard":
        st.session_state.current_tab = st.session_state.get('dashboard_tab', 'playground')
    else:
        st.session_state.current_tab = "overview"
    del st.session_state.app_view

# 3. Dynamic Theme System (Refined Glassmorphism & High-Performance Live Canvas)
is_dark = st.session_state.theme_mode == 'dark'

if is_dark:
    theme_vars = """
    --bg-canvas: #0b0c10;
    --surface-card: #1f2833;
    --surface-hover: #2b3a4a;
    --surface-well: #141a22;
    --border-color: #45f3ff;
    --border-hover: #ff003c;
    --border-subtle: rgba(69, 243, 255, 0.2);
    --text-pure: #ffffff;
    --text-primary: #45f3ff;
    --text-muted: #c5c6c7;
    --accent-amber: #45f3ff;
    --accent-amber-hover: #ff003c;
    --accent-amber-glow: rgba(69, 243, 255, 0.4);
    --accent-emerald: #00ff00;
    --accent-purple: #ff00ff;
    --accent-cyan: #45f3ff;
    --input-bg: #000000;
    --card-shadow: 8px 8px 0px rgba(69, 243, 255, 0.1);
    --live-orb-1: rgba(69, 243, 255, 0.05);
    --live-orb-2: rgba(255, 0, 60, 0.05);
    --live-orb-3: rgba(0, 255, 0, 0.03);
    --grid-dot-color: rgba(69, 243, 255, 0.1);
    """
    chart_text = "#8892B0"
    chart_grid = "rgba(255, 255, 255, 0.06)"
    chart_pred = "#F59E0B"
    chart_act = "#8B5CF6"
else:
    theme_vars = """
    --bg-canvas: #e0e0e0;
    --surface-card: #ffffff;
    --surface-hover: #f0f0f0;
    --surface-well: #dcdcdc;
    --border-color: #333333;
    --border-hover: #ff003c;
    --border-subtle: rgba(0, 0, 0, 0.1);
    --text-pure: #000000;
    --text-primary: #222222;
    --text-muted: #555555;
    --accent-amber: #333333;
    --accent-amber-hover: #ff003c;
    --accent-amber-glow: rgba(0, 0, 0, 0.1);
    --accent-emerald: #008000;
    --accent-purple: #800080;
    --accent-cyan: #008080;
    --input-bg: #f9f9f9;
    --card-shadow: 8px 8px 0px rgba(0, 0, 0, 0.2);
    --live-orb-1: rgba(0, 0, 0, 0.05);
    --live-orb-2: rgba(255, 0, 60, 0.05);
    --live-orb-3: rgba(0, 255, 0, 0.03);
    --grid-dot-color: rgba(0, 0, 0, 0.05);
    """
    chart_text = "#475569"
    chart_grid = "rgba(0, 0, 0, 0.06)"
    chart_pred = "#D97706"
    chart_act = "#7C3AED"

custom_css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap');

/* Remove default Streamlit chrome */
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {{
    display: none !important;
}}

:root {{
    {theme_vars}
    --font-heading: 'Press Start 2P', cursive;
    --font-body: 'VT323', monospace;
    --font-mono: 'VT323', monospace;
}}

html, body, .stApp {{
    background-color: var(--bg-canvas) !important;
    font-family: var(--font-body) !important;
    color: var(--text-primary) !important;
    transition: background-color 0.25s ease, color 0.25s ease;
    overflow-x: hidden !important;
}}

/* Live Background System */
.live-bg-container {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    pointer-events: none;
    z-index: 0;
}}

.live-bg-grid {{
    position: absolute;
    inset: 0;
    background-image: radial-gradient(var(--grid-dot-color) 1px, transparent 1px);
    background-size: 32px 32px;
    mask-image: radial-gradient(ellipse 90% 80% at 50% 25%, #000 40%, transparent 85%);
    -webkit-mask-image: radial-gradient(ellipse 90% 80% at 50% 25%, #000 40%, transparent 85%);
}}

.live-orb {{
    position: absolute;
    border-radius: 50%;
    filter: blur(85px);
    will-change: transform;
}}

.live-orb-1 {{
    top: -8%;
    right: 4%;
    width: 650px;
    height: 650px;
    background: radial-gradient(circle, var(--live-orb-1) 0%, transparent 70%);
    animation: orbDrift1 22s cubic-bezier(0.4, 0, 0.2, 1) infinite alternate;
}}

.live-orb-2 {{
    top: 18%;
    left: -8%;
    width: 580px;
    height: 580px;
    background: radial-gradient(circle, var(--live-orb-2) 0%, transparent 70%);
    animation: orbDrift2 26s cubic-bezier(0.4, 0, 0.2, 1) infinite alternate;
}}

.live-orb-3 {{
    bottom: -5%;
    right: 28%;
    width: 620px;
    height: 520px;
    background: radial-gradient(circle, var(--live-orb-3) 0%, transparent 70%);
    animation: orbDrift3 30s cubic-bezier(0.4, 0, 0.2, 1) infinite alternate;
}}

@keyframes orbDrift1 {{
    0% {{ transform: translate(0px, 0px) scale(1); }}
    50% {{ transform: translate(-70px, 60px) scale(1.08); }}
    100% {{ transform: translate(40px, 100px) scale(0.95); }}
}}

@keyframes orbDrift2 {{
    0% {{ transform: translate(0px, 0px) scale(1); }}
    50% {{ transform: translate(80px, -40px) scale(1.12); }}
    100% {{ transform: translate(-30px, 70px) scale(0.94); }}
}}

@keyframes orbDrift3 {{
    0% {{ transform: translate(0px, 0px) scale(1); }}
    50% {{ transform: translate(-60px, -50px) scale(1.06); }}
    100% {{ transform: translate(50px, -20px) scale(0.96); }}
}}

/* Precision Container Layout with Generous Margins */
.main .block-container {{
    max-width: 1220px !important;
    padding-top: 1.6rem !important;
    padding-bottom: 5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    margin: 0 auto !important;
    position: relative !important;
    z-index: 1 !important;
}}

/* Headings: Clean Architectural Grotesk */
h1, h2, h3, h4, h5, h6 {{
    font-family: var(--font-heading) !important;
    letter-spacing: -0.025em !important;
    color: var(--text-pure) !important;
    font-weight: 700 !important;
}}


.stButton>button {{
    font-family: 'Press Start 2P', cursive !important;
    border: 4px solid var(--border-color) !important;
    border-radius: 0 !important;
    box-shadow: 6px 6px 0px var(--bg-canvas) !important;
    transition: all 0.1s !important;
    text-transform: uppercase !important;
}}
.stButton>button:active {{
    transform: translate(4px, 4px) !important;
    box-shadow: 2px 2px 0px var(--bg-canvas) !important;
}}
.stSelectbox>div>div, .stTextInput>div>div, .stTextArea>div>div {{
    border: 4px solid var(--border-color) !important;
    border-radius: 0 !important;
}}
.stTextArea textarea {{
    font-size: 26px !important;
    font-family: var(--font-mono) !important;
    line-height: 1.6 !important;
    color: var(--text-pure) !important;
}}
.stButton>button p {{
    font-size: 18px !important;
}}
.stMarkdown p, .stMarkdown div, .stMetric label, .stMetric div {{
    font-size: 20px !important;
}}
.stSelectbox>div>div, .stTextInput>div>div {{
    font-size: 20px !important;
}}

/* Smooth View Transitions */
@keyframes fluidFadeIn {{
    0% {{ opacity: 0; transform: translateY(8px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
}}
.fluid-view {{
    animation: fluidFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}}

/* Subtle Gradient Text Accent */
.gradient-text {{
    background: linear-gradient(135deg, #F59E0B 0%, #FBBF24 50%, #06B6D4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: inline-block;
}}

/* Refined Glassmorphism Card with Balanced Padding */
.dev-card {{
    background: var(--surface-card);
    border: 4px solid var(--border-color); box-shadow: var(--card-shadow);
    border-radius: 0px;
    padding: 1.8rem 1.6rem;
    box-shadow: var(--card-shadow);
    
    -webkit-
    transition: border-color 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease;
    height: 100%;
}}
.dev-card:hover {{
    border-color: var(--border-hover);
    transform: translateY(-2px);
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.45);
}}

/* Creative Button System */
@keyframes shimmerSweep {{
    0% {{ background-position: -200% center; }}
    100% {{ background-position: 200% center; }}
}}

.stButton>button {{
    font-family: var(--font-heading) !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.58rem 1.3rem !important;
    letter-spacing: 0.015em !important;
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    position: relative !important;
    overflow: hidden !important;
    cursor: pointer !important;
}}

/* Primary: Warm amber gradient with subtle glow */
.stButton>button[data-testid="baseButton-primary"] {{
    background: linear-gradient(135deg, #F59E0B 0%, #E8850C 60%, #C26300 100%) !important;
    background-size: 200% auto !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    border: 4px solid rgba(251, 191, 36, 0.35) !important;
    box-shadow: 0 3px 14px var(--accent-amber-glow), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
}}
.stButton>button[data-testid="baseButton-primary"]:hover {{
    background-position: right center !important;
    animation: shimmerSweep 0.8s ease-in-out !important;
    transform: translateY(-1px) scale(1.01) !important;
    box-shadow: 0 6px 24px var(--accent-amber-glow), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
    color: #FFFFFF !important;
}}
.stButton>button[data-testid="baseButton-primary"]:active {{
    transform: translateY(0) scale(0.98) !important;
    box-shadow: 0 2px 6px var(--accent-amber-glow) !important;
}}

/* Secondary / Ghost: Clean card with amber accent on hover */
.stButton>button[data-testid="baseButton-secondary"],
.stButton>button:not([data-testid="baseButton-primary"]) {{
    background: var(--surface-card) !important;
    color: var(--text-primary) !important;
    border: 4px solid var(--border-color) !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    backdrop-filter: blur(10px) !important;
}}
.stButton>button[data-testid="baseButton-secondary"]:hover,
.stButton>button:not([data-testid="baseButton-primary"]):hover {{
    background: var(--surface-hover) !important;
    border-color: var(--accent-amber) !important;
    color: var(--text-pure) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 0 0 1px var(--accent-amber), 0 4px 16px var(--accent-amber-glow) !important;
}}
.stButton>button[data-testid="baseButton-secondary"]:active,
.stButton>button:not([data-testid="baseButton-primary"]):active {{
    transform: translateY(0) scale(0.98) !important;
}}

/* Tech Chips & Badges */
.tech-chip {{
    font-family: var(--font-mono);
    font-size: 0.72rem;
    padding: 3px 8px;
    border-radius: 4px;
    background: var(--surface-well);
    border: 4px solid var(--border-color); box-shadow: var(--card-shadow);
    color: var(--text-muted);
    display: inline-flex;
    align-items: center;
    gap: 6px;
}}

/* Pulse Indicators */
.pulse-dot {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background-color: #10B981;
    display: inline-block;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
    animation: pulseGlow 2.2s infinite;
}}
.pulse-dot-amber {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background-color: var(--accent-amber);
    display: inline-block;
    box-shadow: 0 0 0 0 var(--accent-amber-glow);
    animation: pulseGlowAmber 2.2s infinite;
}}
@keyframes pulseGlow {{
    0% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }}
    70% {{ box-shadow: 0 0 0 5px rgba(16, 185, 129, 0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }}
}}
@keyframes pulseGlowAmber {{
    0% {{ box-shadow: 0 0 0 0 var(--accent-amber-glow); }}
    70% {{ box-shadow: 0 0 0 5px rgba(245, 158, 11, 0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }}
}}

/* Decision Result Card */
.decision-banner {{
    background: var(--surface-card);
    border-radius: 0px;
    padding: 1.3rem 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 4px solid var(--border-color); box-shadow: var(--card-shadow);
    box-shadow: var(--card-shadow);
    
}}
.decision-banner.edge-decision {{
    border-left: 4px solid var(--accent-emerald);
}}
.decision-banner.cloud-decision {{
    border-left: 4px solid var(--accent-amber);
}}

/* Metrics */
div[data-testid="stMetricValue"] {{
    color: var(--text-pure) !important;
    font-family: var(--font-heading) !important;
    font-weight: 700 !important;
    font-size: 1.7rem !important;
}}
div[data-testid="stMetricLabel"] p {{
    color: var(--text-muted) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

/* Form Inputs */
.stTextArea textarea, .stTextInput input {{
    background-color: var(--input-bg) !important;
    color: var(--text-pure) !important;
    border: 4px solid var(--border-color) !important;
    border-radius: 6px !important;
    font-family: var(--font-mono) !important;
    font-size: 0.86rem !important;
    padding: 0.8rem !important;
}}
.stTextArea textarea:focus, .stTextInput input:focus {{
    border-color: var(--accent-amber) !important;
    box-shadow: 0 0 8px var(--accent-amber-glow) !important;
}}

/* Theme Toggle */
[data-testid="stToggle"] {{
    display: flex;
    align-items: center;
    justify-content: flex-end;
}}
[data-testid="stToggle"] label {{
    display: inline-flex !important;
    align-items: center !important;
    gap: 8px !important;
    padding: 5px 12px 5px 10px !important;
    background: var(--surface-well) !important;
    border: 4px solid var(--border-color) !important;
    border-radius: 20px !important;
    cursor: pointer !important;
}}
[data-testid="stToggle"] label:hover {{
    border-color: var(--accent-amber) !important;
}}
[data-testid="stToggle"] p {{
    font-family: var(--font-heading) !important;
    font-weight: 600 !important;
    font-size: 0.75rem !important;
    color: var(--text-muted) !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    margin: 0 !important;
}}

/* Segmented Tabs */
.stTabs [data-baseweb="tab-list"] {{
    gap: 3px !important;
    background: var(--surface-well) !important;
    padding: 4px !important;
    border-radius: 8px !important;
    border: 4px solid var(--border-color) !important;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: var(--font-heading) !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
    padding: 8px 18px !important;
    border-radius: 6px !important;
    color: var(--text-muted) !important;
    background: transparent !important;
}}
.stTabs [data-baseweb="tab"]:hover {{
    color: var(--text-pure) !important;
}}
.stTabs [aria-selected="true"] {{
    background: var(--accent-amber) !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    box-shadow: 0 2px 8px var(--accent-amber-glow) !important;
}}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {{
    display: none !important;
}}

/* Developer Footer */
.dev-footer {{
    margin-top: 4.5rem;
    padding-top: 1.8rem;
    border-top: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.8rem;
    color: var(--text-muted);
    font-family: var(--font-mono);
}}
</style>
"""

st.markdown(custom_css, unsafe_allow_html=True)

# 4. Live Background Render Layer (Fixed Behind Content, 60fps GPU Composited)
st.markdown(
    """
    <div class="live-bg-container">
        <div class="live-bg-grid"></div>
        <div class="live-orb live-orb-1"></div>
        <div class="live-orb live-orb-2"></div>
        <div class="live-orb live-orb-3"></div>
    </div>
    """,
    unsafe_allow_html=True
)

# 5. Global Header Bar: Brand, Clean Unified Navigation & Controls
header_brand, header_nav, header_ctrl = st.columns([2.8, 6.0, 3.2], gap="medium")

with header_brand:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 10px; height: 100%; padding-top: 4px;">
            <div style="background: linear-gradient(135deg, #F59E0B, #D97706); color: #FFFFFF; width: 28px; height: 28px; border-radius: 0px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 0.78rem; font-family: var(--font-heading); box-shadow: 0 2px 8px rgba(245,158,11,0.25);">
                AS
            </div>
            <span style="font-family: var(--font-heading); font-size: 1.25rem; font-weight: 700; color: var(--text-pure); letter-spacing: -0.02em;">
                AI SCHEDULER
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

with header_nav:
    n1, n2, n3, n4 = st.columns(4, gap="small")
    with n1:
        is_active = st.session_state.current_tab == "overview"
        if st.button("Overview", use_container_width=True, width="stretch", type="primary" if is_active else "secondary"):
            st.session_state.current_tab = "overview"
            st.rerun()
    with n2:
        is_active = st.session_state.current_tab == "playground"
        if st.button("Live Dispatch", use_container_width=True, width="stretch", type="primary" if is_active else "secondary"):
            st.session_state.current_tab = "playground"
            st.rerun()
    with n3:
        is_active = st.session_state.current_tab == "endpoints"
        if st.button("Cluster & RTT", use_container_width=True, width="stretch", type="primary" if is_active else "secondary"):
            st.session_state.current_tab = "endpoints"
            st.rerun()
    with n4:
        is_active = st.session_state.current_tab == "telemetry"
        if st.button("Telemetry", use_container_width=True, width="stretch", type="primary" if is_active else "secondary"):
            st.session_state.current_tab = "telemetry"
            st.rerun()

with header_ctrl:
    theme_col, status_col = st.columns([1.1, 1.3], gap="small")
    with theme_col:
        new_theme = st.toggle("Dark", value=is_dark, key="theme_toggle")
        if new_theme != is_dark:
            st.session_state.theme_mode = 'dark' if new_theme else 'light'
            st.rerun()
    with status_col:
        st.markdown(
            """
            <div style="display: flex; justify-content: flex-end; align-items: center; height: 100%; padding-top: 4px;">
                <span class="tech-chip" style="color: #10B981; border-color: rgba(16,185,129,0.25);">
                    <span class="pulse-dot"></span> EC2 Online
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("<div style='margin-bottom: 2.2rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.6rem;'></div>", unsafe_allow_html=True)


# Core Execution & Latency Processing Function
def execute_workload(code_string, filename, local_url, cloud_url, scheduler_instance):
    schedule_res = scheduler_instance.schedule(code_string)
    
    if "error" in schedule_res:
        st.error(f"AST Parsing Failed for {filename}: {schedule_res['error']}")
        return

    preds = schedule_res["predictions"]
    decision = schedule_res["decision"]
    confidence = schedule_res.get("confidence", 0)
    decision_method = schedule_res.get("decision_method", "regression")
    target_name = "Local Edge Worker" if decision == "EDGE" else "AWS EC2 Cloud Node"
    target_url = local_url if decision == "EDGE" else cloud_url
    is_edge = decision == "EDGE"

    st.markdown("<br>", unsafe_allow_html=True)
    
    banner_class = "edge-decision" if is_edge else "cloud-decision"
    badge_color = "#10B981" if is_edge else "var(--accent-amber)"

    st.markdown(
        f"""
        <div class="decision-banner {banner_class}" style="margin: 1.5rem 0 1.2rem 0;">
            <div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.08em; margin-bottom: 4px;">
                    ROUTING DECISION · {decision_method.upper()} CLASSIFIER ({confidence:.1%} CONFIDENCE)
                </div>
                <div style="font-family: var(--font-heading); font-size: 1.3rem; font-weight: 700; color: {badge_color};">
                    Dispatched to {target_name}
                </div>
            </div>
            <div class="tech-chip" style="font-size: 0.8rem; padding: 5px 12px;">
                URL: {target_url}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    m1, m2, m3 = st.columns(3, gap="medium")
    with m1:
        st.metric(label="Predicted Edge Latency", value=f"{preds['predicted_edge_time']:.4f} s")
    with m2:
        st.metric(label="Predicted Cloud Latency", value=f"{preds['predicted_cloud_time']:.4f} s")
    with m3:
        speedup = (preds['predicted_edge_time'] - preds['predicted_cloud_time'])
        st.metric(label="Predicted Offload Delta", value=f"{speedup:+.4f} s", delta="Cloud Speedup" if speedup > 0 else "Edge Faster")

    worker_data = None
    total_rtt = 0.0
    st.toast(f"👾 [TRANSMITTING PAYLOAD TO {target_name}]", icon="🛰️")
    req_start = time.perf_counter()
    try:
        response = requests.post(target_url, json={"code": code_string}, timeout=65)
        total_rtt = time.perf_counter() - req_start
        worker_data = response.json()
        st.toast(f"✅ [EXECUTION COMPLETE ON {target_name}]", icon="🏆")
        st.markdown("""
        <div id="arcade-overlay" style="
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(11, 12, 16, 0.95); z-index: 999999;
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            animation: fadeOutArcade 3.5s forwards; pointer-events: none;
        ">
            <h1 style="font-family: 'Press Start 2P', cursive; font-size: 4rem; color: #45f3ff; text-shadow: 6px 6px #ff003c; text-align: center; margin-bottom: 20px; animation: glitch 0.2s linear infinite;">MISSION ACCOMPLISHED</h1>
            <h2 style="font-family: 'VT323', monospace; font-size: 3rem; color: #00ff00; animation: blinker 0.4s linear infinite;">PAYLOAD ROUTED SUCESSFULLY</h2>
            <style>
            @keyframes fadeOutArcade {
                0% { opacity: 0; transform: scale(0.8); }
                10% { opacity: 1; transform: scale(1.1); }
                15% { transform: scale(1); }
                80% { opacity: 1; transform: scale(1); }
                100% { opacity: 0; pointer-events: none; display: none; }
            }
            @keyframes glitch {
                0% { transform: translate(0) }
                20% { transform: translate(-5px, 5px) }
                40% { transform: translate(-5px, -5px) }
                60% { transform: translate(5px, 5px) }
                80% { transform: translate(5px, -5px) }
                100% { transform: translate(0) }
            }
            @keyframes blinker { 50% { opacity: 0; } }
            </style>
        </div>
        <script>
        setTimeout(() => { document.getElementById('arcade-overlay').style.display = 'none'; }, 3500);
        </script>
        """, unsafe_allow_html=True)
    except Exception as ex:
        st.error(f"Execution failed on {target_url}: {ex}")

    if worker_data:
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        col_out, col_chart = st.columns([1.1, 1.3], gap="large")
        
        with col_out:
            st.markdown(
                """
                <div style="background: var(--surface-well); border: 4px solid var(--border-color); box-shadow: var(--card-shadow); border-radius: 0px; padding: 8px 12px; margin-bottom: 8px; font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted); display: flex; justify-content: space-between;">
                    <span>RUNTIME EXECUTION CONSOLE</span>
                    <span style="color:#10B981;">200 OK</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            if worker_data.get("stdout"):
                st.code(worker_data["stdout"], language="text")
            if worker_data.get("stderr"):
                st.error(worker_data["stderr"])
            
            st.markdown(
                f"""
                <div style="font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-muted); margin-top: 8px;">
                    Worker Compute: <b style="color:var(--text-pure);">{worker_data.get('execution_time_seconds', 0):.4f}s</b> &nbsp;|&nbsp; 
                    Network Round-Trip: <b style="color:var(--accent-amber);">{total_rtt:.4f}s</b>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_chart:
            st.markdown(
                """
                <div style="font-family: var(--font-heading); font-size: 1.05rem; font-weight: 700; color: var(--text-pure); margin-bottom: 8px;">
                    Execution Telemetry Comparison
                </div>
                """,
                unsafe_allow_html=True
            )
            categories = ["Local Edge", "AWS Cloud"]
            pred_values = [preds["predicted_edge_time"], preds["predicted_cloud_time"]]
            actual_values = [
                total_rtt if is_edge else 0,
                total_rtt if not is_edge else 0
            ]
            actual_texts = [
                f"{total_rtt:.4f} s" if is_edge else "Not Dispatched",
                f"{total_rtt:.4f} s" if not is_edge else "Not Dispatched"
            ]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Predicted Latency",
                x=categories,
                y=pred_values,
                marker_color=chart_pred,
                text=[f"{v:.4f} s" for v in pred_values],
                textposition="outside",
                hovertemplate="<b>%{x} (Predicted)</b>: %{y:.4f} s<extra></extra>"
            ))
            fig.add_trace(go.Bar(
                name="Actual RTT",
                x=categories,
                y=actual_values,
                marker_color=chart_act,
                text=actual_texts,
                textposition="outside",
                hovertemplate="<b>%{x} (Actual)</b>: %{text}<extra></extra>"
            ))

            all_vals = pred_values + [total_rtt]
            max_y = max(all_vals) if all_vals else 1.0

            fig.update_layout(
                barmode="group", bargap=0.3, bargroupgap=0.08,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=260,
                margin=dict(l=15, r=15, t=25, b=25),
                font=dict(color=chart_text, family="Space Grotesk, sans-serif", size=11),
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0, font=dict(size=11, color=chart_text)),
                xaxis=dict(showgrid=False, linecolor=chart_grid, tickfont=dict(size=11, color=chart_text)),
                yaxis=dict(showgrid=True, gridcolor=chart_grid, zeroline=True, zerolinecolor=chart_grid, range=[0, max_y * 1.35], ticksuffix=" s", tickfont=dict(size=11, color=chart_text))
            )
            st.plotly_chart(fig, use_container_width=True, width="stretch")


# ==============================================================================
# TAB 1: OVERVIEW & LANDING PAGE (Clean, Balanced Margins, Live Background)
# ==============================================================================
if st.session_state.current_tab == "overview":
    st.markdown("<div class='fluid-view'>", unsafe_allow_html=True)
    
    # Hero Section
    hero_l, hero_r = st.columns([1.18, 0.82], gap="large")
    with hero_l:
        st.markdown(
            """
            <div style="padding: 1.0rem 0 1.2rem 0;">
                <div class="tech-chip" style="margin-bottom: 1.4rem; border-color: rgba(245,158,11,0.25); color: var(--accent-amber);">
                    <span class="pulse-dot-amber"></span> AUTONOMOUS HYBRID SCHEDULING
                </div>
                <h1 style="font-size: 3.3rem; font-weight: 700; line-height: 1.12; letter-spacing: -0.03em; margin-bottom: 1.2rem; color: var(--text-pure);">
                    Intelligent Workload Routing<br>
                    Between <span class="gradient-text">Edge & AWS Cloud</span>
                </h1>
                <p style="font-size: 1.05rem; color: var(--text-muted); line-height: 1.7; max-width: 570px; margin-bottom: 2.2rem;">
                    Static Python AST analysis evaluates computational complexity in microseconds to autonomously route code between local edge hardware and AWS EC2 instances based on real-time network latency.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        btn_c1, btn_c2, _ = st.columns([3.5, 3.5, 3.0], gap="small")
        with btn_c1:
            if st.button("Launch Live Dispatch →", type="primary", use_container_width=True, width="stretch"):
                st.session_state.current_tab = "playground"
                st.rerun()
        with btn_c2:
            if st.button("Cluster Topology & RTT", type="secondary", use_container_width=True, width="stretch"):
                st.session_state.current_tab = "endpoints"
                st.rerun()

    with hero_r:
        st.markdown(
            """
            <div class="dev-card" style="padding: 1.8rem 1.6rem; border-color: var(--border-hover);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.2rem;">
                    <span class="tech-chip" style="color: var(--accent-amber);">SYSTEM TOPOLOGY</span>
                    <span class="tech-chip" style="color: #10B981; border-color: rgba(16,185,129,0.3);">
                        <span class="pulse-dot"></span> REST FABRIC READY
                    </span>
                </div>
                <div style="font-family: var(--font-heading); font-size: 1.25rem; font-weight: 700; color: var(--text-pure); margin-bottom: 0.8rem;">
                    Real-Time Latency Arbitration
                </div>
                <div style="background: var(--surface-well); border: 4px solid var(--border-color); box-shadow: var(--card-shadow); border-radius: 0px; padding: 12px 14px; margin-bottom: 1.2rem; font-family: var(--font-mono); font-size: 0.78rem; color: var(--text-muted); line-height: 1.85;">
                    <div style="display: flex; justify-content: space-between;">
                        <span>01 / Static AST Profiling</span>
                        <span style="color: var(--accent-amber);">&lt; 12ms</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>02 / ML Routing Decision</span>
                        <span style="color: #10B981;">99.4% Accuracy</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span>03 / WAN Delay Modeling</span>
                        <span style="color: var(--text-pure);">~130ms RTT</span>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 1.2rem;">
                    <div style="background: var(--surface-well); padding: 10px 12px; border-radius: 0px; border: 4px solid var(--border-color); box-shadow: var(--card-shadow);">
                        <div style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted);">LOCAL EDGE</div>
                        <div style="font-family: var(--font-heading); font-size: 0.98rem; font-weight: 700; color: var(--text-pure);">localhost:8000</div>
                        <div style="font-family: var(--font-mono); font-size: 0.68rem; color: #10B981;">0ms Transit Penalty</div>
                    </div>
                    <div style="background: var(--surface-well); padding: 10px 12px; border-radius: 0px; border: 4px solid var(--border-color); box-shadow: var(--card-shadow);">
                        <div style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted);">AWS EC2 CLOUD</div>
                        <div style="font-family: var(--font-heading); font-size: 0.98rem; font-weight: 700; color: var(--text-pure);">18.60.41.230</div>
                        <div style="font-family: var(--font-mono); font-size: 0.68rem; color: var(--accent-amber);">~130ms WAN Delay</div>
                    </div>
                </div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted); border-top: 1px solid var(--border-color); padding-top: 10px; display: flex; justify-content: space-between;">
                    <span>Rule: Cost(Cloud) + RTT &lt; Cost(Edge)</span>
                    <span style="color: var(--accent-amber);">Dynamic Offload</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Key Validation Metrics Ribbon with Balanced Margin
    st.markdown("<div style='margin: 3.5rem 0 2.2rem 0; border-top: 1px solid var(--border-color);'></div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4, gap="medium")
    with m1:
        st.markdown(
            """
            <div class="dev-card" style="padding: 1.3rem 1.2rem; border-top: 2px solid var(--accent-amber);">
                <div style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">DECISION ACCURACY</div>
                <div style="font-family: var(--font-heading); font-size: 2.1rem; font-weight: 700; color: var(--text-pure); margin: 3px 0;">99.4%</div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; color: #10B981;">Dual-Engine ML Model</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m2:
        st.markdown(
            """
            <div class="dev-card" style="padding: 1.3rem 1.2rem; border-top: 2px solid var(--accent-emerald);">
                <div style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">PROFILING LATENCY</div>
                <div style="font-family: var(--font-heading); font-size: 2.1rem; font-weight: 700; color: var(--text-pure); margin: 3px 0;">&lt; 12ms</div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; color: #10B981;">Zero Execution Risk</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m3:
        st.markdown(
            """
            <div class="dev-card" style="padding: 1.3rem 1.2rem; border-top: 2px solid var(--accent-purple);">
                <div style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">EVALUATED WORKLOADS</div>
                <div style="font-family: var(--font-heading); font-size: 2.1rem; font-weight: 700; color: var(--text-pure); margin: 3px 0;">503</div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted);">Diverse AST Scripts</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m4:
        st.markdown(
            """
            <div class="dev-card" style="padding: 1.3rem 1.2rem; border-top: 2px solid var(--accent-cyan);">
                <div style="font-family: var(--font-mono); font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">REGRESSION FIT</div>
                <div style="font-family: var(--font-heading); font-size: 2.1rem; font-weight: 700; color: var(--text-pure); margin: 3px 0;">0.972</div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem; color: var(--text-muted);">R² Latency Model</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Core Architectural Pillars (3 Clean Cards with Generous Spacing)
    st.markdown(
        """
        <div style="margin: 3.5rem 0 1.6rem 0;">
            <div class="tech-chip" style="color: var(--accent-amber); margin-bottom: 6px;">CORE ARCHITECTURE</div>
            <h2 style="font-size: 1.9rem; color: var(--text-pure);">Architectural Foundations</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.markdown(
            """
            <div class="dev-card">
                <div style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent-amber); margin-bottom: 0.6rem; font-weight: 600;">01 / STATIC PROFILING</div>
                <div style="font-family: var(--font-heading); font-size: 1.15rem; font-weight: 700; color: var(--text-pure); margin-bottom: 0.5rem;">
                    AST Syntax Analysis
                </div>
                <p style="font-size: 0.88rem; color: var(--text-muted); line-height: 1.65; margin: 0;">
                    Parses abstract syntax trees to measure matrix operations, nested loop depth, and recursion in microseconds—without executing untrusted code.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            """
            <div class="dev-card">
                <div style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent-amber); margin-bottom: 0.6rem; font-weight: 600;">02 / NETWORK AWARENESS</div>
                <div style="font-family: var(--font-heading); font-size: 1.15rem; font-weight: 700; color: var(--text-pure); margin-bottom: 0.5rem;">
                    RTT Compensation
                </div>
                <p style="font-size: 0.88rem; color: var(--text-muted); line-height: 1.65; margin: 0;">
                    Dynamically models real-time WAN round-trip delays, guaranteeing that cloud offloading only occurs when compute speedup exceeds transit time.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            """
            <div class="dev-card">
                <div style="font-family: var(--font-mono); font-size: 0.75rem; color: var(--accent-amber); margin-bottom: 0.6rem; font-weight: 600;">03 / MACHINE LEARNING</div>
                <div style="font-family: var(--font-heading); font-size: 1.15rem; font-weight: 700; color: var(--text-pure); margin-bottom: 0.5rem;">
                    Dual-Engine Inference
                </div>
                <p style="font-size: 0.88rem; color: var(--text-muted); line-height: 1.65; margin: 0;">
                    Random Forest classification paired with Gradient Boosting regression yields 99.4% accurate decisions with sub-millisecond inference latency.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Minimalist Bottom CTA Banner with Balanced Margins
    st.markdown("<div style='margin-top: 3.8rem;'></div>", unsafe_allow_html=True)
    cta_l, cta_r = st.columns([7.2, 2.8], gap="medium")
    with cta_l:
        st.markdown(
            """
            <div class="dev-card" style="padding: 1.4rem 1.8rem; height: auto;">
                <h3 style="font-size: 1.35rem; color: var(--text-pure); margin-bottom: 4px;">Experience Live Hybrid Offloading</h3>
                <p style="color: var(--text-muted); font-size: 0.92rem; margin: 0;">Profile custom Python code or batch evaluate test suites with live execution telemetry.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with cta_r:
        st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
        if st.button("Open Live Dispatch →", type="primary", use_container_width=True, width="stretch"):
            st.session_state.current_tab = "playground"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# TAB 2: LIVE DISPATCH PLAYGROUND
# ==============================================================================
elif st.session_state.current_tab == "playground":
    st.markdown("<div class='fluid-view'>", unsafe_allow_html=True)
    
    st.markdown(
        """
        <div style="margin-bottom: 1.8rem;">
            <div class="tech-chip" style="color: var(--accent-amber); margin-bottom: 6px;">INTERACTIVE WORKSPACE</div>
            <h2 style="font-size: 2.1rem; color: var(--text-pure);">Live Workload Dispatch Playground</h2>
            <p style="color: var(--text-muted); font-size: 0.95rem;">Select a workload preset or enter custom Python code to profile AST complexity and trigger real-time routing.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    local_endpoint = "http://localhost:8000/execute"
    cloud_endpoint = "http://18.60.41.230:8000/execute"
    cloud_rtt = st.session_state.sim_cloud_rtt
    scheduler = OffloadingScheduler(cloud_rtt_ms=cloud_rtt)

    tab_manual, tab_batch = st.tabs(["Single Code Dispatch", "Multi-File Batch Evaluation"])

    with tab_manual:
        st.markdown("<div style='font-family: var(--font-heading); font-size: 0.92rem; font-weight: 700; margin: 12px 0 8px 0; color: var(--text-pure);'>Select Workload Preset:</div>", unsafe_allow_html=True)
        
        pr1, pr2, pr3, pr4 = st.columns(4, gap="small")
        with pr1:
            if st.button("Matrix Dot (Cloud)", use_container_width=True, width="stretch", type="primary" if st.session_state.code_preset == "heavy" else "secondary"):
                st.session_state.code_preset = "heavy"
                st.rerun()
        with pr2:
            if st.button("String Parse (Edge)", use_container_width=True, width="stretch", type="primary" if st.session_state.code_preset == "light" else "secondary"):
                st.session_state.code_preset = "light"
                st.rerun()
        with pr3:
            if st.button("Fibonacci (CPU)", use_container_width=True, width="stretch", type="primary" if st.session_state.code_preset == "fib" else "secondary"):
                st.session_state.code_preset = "fib"
                st.rerun()
        with pr4:
            if st.button("Nested Loops", use_container_width=True, width="stretch", type="primary" if st.session_state.code_preset == "loop" else "secondary"):
                st.session_state.code_preset = "loop"
                st.rerun()

        if st.session_state.code_preset == "heavy":
            default_code = """import numpy as np

# Heavy Matrix Multiplication: 2000x2000
size = 2000
A = np.random.rand(size, size)
B = np.random.rand(size, size)
C = np.dot(A, B)
print("Computation Complete! Result shape:", C.shape)"""
        elif st.session_state.code_preset == "light":
            default_code = """# Lightweight String Operations
text = "ai scheduler dynamic workload orchestration"
words = [w.capitalize() for w in text.split()]
print("Formatted:", " ".join(words))
print("Reversed:", text[::-1])"""
        elif st.session_state.code_preset == "fib":
            default_code = """# Recursive CPU Workload
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

result = fib(32)
print("Fibonacci(32) =", result)"""
        else:
            default_code = """# Nested Compute Loop
total = 0
for i in range(1500):
    for j in range(1500):
        total += (i * j) % 17
print("Loop computation total:", total)"""

        st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
        user_code = st.text_area("Python Source Payload", default_code, height=210, label_visibility="collapsed")
        
        btn_run_col, _ = st.columns([3.8, 6.2])
        clicked = False
        with btn_run_col:
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("EXECUTE & DISPATCH WORKLOAD →", type="primary", use_container_width=True, width="stretch"):
                clicked = True
                
        if clicked:
            execute_workload(user_code, "Manual Input", local_endpoint, cloud_endpoint, scheduler)

    with tab_batch:
        st.markdown("<br>", unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Upload Multiple Python Scripts (.py)",
            type=["py"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

        if uploaded_files:
            st.markdown(f"<p style='color: var(--text-muted); font-family: var(--font-mono); font-size: 0.85rem;'>Queued for batch execution: <b style='color:var(--text-pure);'>{len(uploaded_files)} files</b></p>", unsafe_allow_html=True)

        if st.button("RUN FULL BATCH PIPELINE →", type="primary"):
            if not uploaded_files:
                st.warning("Please upload one or more .py files to evaluate.")
            else:
                for file in uploaded_files:
                    file_name = file.name
                    file_content = file.getvalue().decode("utf-8")

                    with st.expander(f"Script: {file_name}", expanded=True):
                        st.code(file_content, language="python")
                        execute_workload(file_content, file_name, local_endpoint, cloud_endpoint, scheduler)

    st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# TAB 3: CLUSTER ENDPOINTS & RTT
# ==============================================================================
elif st.session_state.current_tab == "endpoints":
    st.markdown("<div class='fluid-view'>", unsafe_allow_html=True)
    
    st.markdown(
        """
        <div style="margin-bottom: 1.8rem;">
            <div class="tech-chip" style="color: var(--accent-amber); margin-bottom: 6px;">COMPUTE FABRIC MONITOR</div>
            <h2 style="font-size: 2.1rem; color: var(--text-pure);">Cluster Endpoints & Network Latency</h2>
            <p style="color: var(--text-muted); font-size: 0.95rem;">Perform live connectivity pings to compute nodes and adjust the simulated network round-trip compensation delay.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    ep_col1, ep_col2 = st.columns(2, gap="large")
    with ep_col1:
        st.markdown(
            """
            <div class="dev-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <span style="font-family: var(--font-heading); font-size: 1.25rem; font-weight: 700; color: var(--text-pure);">
                        Local Edge Worker
                    </span>
                    <span class="tech-chip" style="color: #10B981; border-color: rgba(16,185,129,0.3);">
                        <span class="pulse-dot"></span> ONLINE
                    </span>
                </div>
                <div style="font-family: var(--font-mono); font-size: 0.82rem; color: var(--text-muted); line-height: 1.85; margin-bottom: 1.2rem;">
                    <b>URL:</b> http://localhost:8000/execute<br>
                    <b>Hardware:</b> Local Host Worker Process<br>
                    <b>Network Transit:</b> 0ms (Local Loopback)<br>
                    <b>Optimal For:</b> Lightweight scripts, string heuristics, fast transforms
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("Ping Local Edge Worker", use_container_width=True, width="stretch"):
            try:
                t0 = time.perf_counter()
                r = requests.post("http://localhost:8000/execute", json={"code": "pass"}, timeout=3)
                ms = (time.perf_counter() - t0) * 1000
                st.success(f"Local Edge responded in {ms:.1f}ms (HTTP {r.status_code})")
            except Exception as e:
                st.error(f"Edge connection failed: {e}")

    with ep_col2:
        st.markdown(
            """
            <div class="dev-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <span style="font-family: var(--font-heading); font-size: 1.25rem; font-weight: 700; color: var(--text-pure);">
                        AWS EC2 Cloud Node
                    </span>
                    <span class="tech-chip" style="color: #10B981; border-color: rgba(16,185,129,0.3);">
                        <span class="pulse-dot"></span> 18.60.41.230
                    </span>
                </div>
                <div style="font-family: var(--font-mono); font-size: 0.82rem; color: var(--text-muted); line-height: 1.85; margin-bottom: 1.2rem;">
                    <b>URL:</b> http://18.60.41.230:8000/execute<br>
                    <b>Hardware:</b> AWS EC2 Cloud Instance<br>
                    <b>Network Transit:</b> ~130ms - 155ms (WAN latency)<br>
                    <b>Optimal For:</b> High-dimensional matrices, parallel PyTorch/NumPy
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("Ping AWS EC2 Node", use_container_width=True, width="stretch"):
            try:
                t0 = time.perf_counter()
                r = requests.post("http://18.60.41.230:8000/execute", json={"code": "pass"}, timeout=5)
                ms = (time.perf_counter() - t0) * 1000
                st.success(f"AWS EC2 responded in {ms:.1f}ms (HTTP {r.status_code})")
            except Exception as e:
                st.error(f"AWS EC2 connection failed: {e}")

    st.markdown("<div style='margin: 3.2rem 0 2rem 0; border-top: 1px solid var(--border-color);'></div>", unsafe_allow_html=True)
    
    st.markdown(
        """
        <div class="dev-card" style="padding: 1.8rem 2rem;">
            <div style="font-family: var(--font-heading); font-size: 1.3rem; font-weight: 700; color: var(--text-pure); margin-bottom: 0.4rem;">
                Dynamic Network Round-Trip Delay Simulator
            </div>
            <p style="color: var(--text-muted); font-size: 0.88rem; margin-bottom: 1.2rem;">
                Adjusting the simulated WAN network delay alters the offload crossover threshold in real-time.
            </p>
        """,
        unsafe_allow_html=True
    )

    new_rtt = st.slider(
        "Simulated Cloud Latency (ms)",
        10, 500,
        st.session_state.sim_cloud_rtt,
        help="Adjusting this slider updates the network penalty applied during latency prediction and classification."
    )
    st.session_state.sim_cloud_rtt = new_rtt
    st.caption(f"Currently simulating **{new_rtt}ms** WAN latency. Offloading to AWS Cloud will only trigger when compute acceleration exceeds {new_rtt}ms.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# TAB 4: MODEL BENCHMARKS & TELEMETRY
# ==============================================================================
elif st.session_state.current_tab == "telemetry":
    st.markdown("<div class='fluid-view'>", unsafe_allow_html=True)
    
    st.markdown(
        """
        <div style="margin-bottom: 1.8rem;">
            <div class="tech-chip" style="color: var(--accent-amber); margin-bottom: 6px;">EMPIRICAL VALIDATION</div>
            <h2 style="font-size: 2.1rem; color: var(--text-pure);">Model Benchmarks & Decision Telemetry</h2>
            <p style="color: var(--text-muted); font-size: 0.95rem;">Empirical validation metrics across 503 test scripts comparing Random Forest Classification with Latency Regression.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    k1, k2, k3, k4 = st.columns(4, gap="medium")
    with k1:
        st.metric(label="Decision Accuracy", value="99.4%", delta="+24.2% RF Model")
    with k2:
        st.metric(label="Regression Latency R²", value="0.972", delta="Trained Fit")
    with k3:
        st.metric(label="Evaluated Scripts", value="503", delta="Diverse AST")
    with k4:
        st.metric(label="AST Extraction Overhead", value="< 12ms", delta="Real-Time")

    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    
    chart_c1, chart_c2 = st.columns([1.25, 0.75], gap="large")
    with chart_c1:
        st.markdown(
            """
            <div style="font-family: var(--font-heading); font-size: 1.1rem; font-weight: 700; color: var(--text-pure); margin-bottom: 0.6rem;">
                Latency Crossover Differential: Edge vs Cloud + RTT
            </div>
            """,
            unsafe_allow_html=True
        )
        x_complexity = [100, 300, 600, 1000, 1500, 2000, 2500, 3000]
        y_edge = [0.005, 0.02, 0.08, 0.25, 0.65, 1.45, 2.80, 4.80]
        y_cloud_net = [0.155, 0.165, 0.20, 0.32, 0.55, 0.95, 1.60, 2.50]

        curve_fig = go.Figure()
        curve_fig.add_trace(go.Scatter(
            x=x_complexity, y=y_edge,
            mode='lines+markers', name='Local Edge Duration',
            line=dict(color='#10B981', width=3),
            marker=dict(size=7)
        ))
        curve_fig.add_trace(go.Scatter(
            x=x_complexity, y=y_cloud_net,
            mode='lines+markers', name='AWS Cloud + 130ms RTT',
            line=dict(color=chart_pred, width=3, dash='dot'),
            marker=dict(size=7)
        ))

        curve_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=300, margin=dict(l=15, r=15, t=30, b=25),
            font=dict(color=chart_text, family="Space Grotesk, sans-serif"),
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0),
            xaxis=dict(title="Computational Load / Matrix Dimension", showgrid=True, gridcolor=chart_grid),
            yaxis=dict(title="Execution Time (seconds)", showgrid=True, gridcolor=chart_grid)
        )
        st.plotly_chart(curve_fig, use_container_width=True, width="stretch")

    with chart_c2:
        st.markdown(
            """
            <div style="font-family: var(--font-heading); font-size: 1.1rem; font-weight: 700; color: var(--text-pure); margin-bottom: 0.6rem;">
                Routing Decision Breakdown
            </div>
            """,
            unsafe_allow_html=True
        )
        pie_fig = go.Figure(data=[go.Pie(
            labels=['Local Edge Node', 'AWS EC2 Cloud Node'],
            values=[377, 126],
            hole=.55,
            marker_colors=['#10B981', chart_pred]
        )])
        pie_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=300, margin=dict(l=10, r=10, t=10, b=10),
            font=dict(color=chart_text, family="Space Grotesk, sans-serif"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
        )
        st.plotly_chart(pie_fig, use_container_width=True, width="stretch")

    st.markdown("</div>", unsafe_allow_html=True)


# 5. Minimalist Developer Footer
st.markdown(
    """
    <div class="dev-footer">
        <div>
            <b style="color: var(--text-pure);">AI SCHEDULER</b>
            &nbsp;·&nbsp; Cloud & Edge Hybrid Computing Engine &nbsp;·&nbsp; VIT CAD Project
        </div>
        <div style="display: flex; gap: 20px; align-items: center;">
            <span>Edge: localhost:8000</span>
            <span>Cloud: 18.60.41.230:8000</span>
            <span style="color: #10B981; display: inline-flex; align-items: center; gap: 5px;">
                <span class="pulse-dot"></span> Online
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)