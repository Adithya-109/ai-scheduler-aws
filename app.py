import streamlit as st
import requests
import time
import plotly.graph_objects as go
from pipeline.scheduler import OffloadingScheduler

# 1. Page Configuration
st.set_page_config(
    page_title="AI Workload Orchestrator", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# 2. Application State Initialization
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'landing'
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = True

# 3. Typography & Advanced Animation Stylesheet
font_family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
code_font = "'JetBrains Mono', 'Fira Code', Consolas, Menlo, monospace"

base_css = f"""
<style>
/* Remove default Streamlit chrome */
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {{
    display: none !important;
}}

/* Typography System */
html, body, [class*="css"] {{
    font-family: {font_family} !important;
    letter-spacing: -0.01em;
    scroll-behavior: smooth;
}}

code, pre, .stCode, textarea {{
    font-family: {code_font} !important;
}}

/* Tighten Central Alignment & Eliminate Top Dead Space */
.main .block-container {{
    max-width: 1060px !important;
    padding-top: 1.5rem !important; /* Reduced from default 4rem+ */
    padding-bottom: 3rem !important;
    margin: 0 auto !important;
}}

/* =========================================
   NEW: GLOBAL SYSTEM TELEMETRY BAR
========================================= */
.system-status-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 18px;
    background: var(--input-bg);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 12px var(--shadow-color);
    animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}}
.status-item {{
    display: flex;
    align-items: center;
    gap: 6px;
}}
.status-indicator {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
}}
.indicator-green {{ background-color: #10B981; box-shadow: 0 0 8px #10B981; }}
.indicator-blue {{ background-color: #38BDF8; box-shadow: 0 0 8px #38BDF8; }}
.indicator-purple {{ background-color: #8B5CF6; box-shadow: 0 0 8px #8B5CF6; }}

/* =========================================
   GLOBAL ANIMATIONS & KEYFRAMES
========================================= */
@keyframes floatGlow {{
    0% {{ transform: translate(0px, 0px) scale(1); }}
    50% {{ transform: translate(60px, 40px) scale(1.1); }}
    100% {{ transform: translate(-40px, 80px) scale(0.95); }}
}}
@keyframes fadeInUp {{
    0% {{ opacity: 0; transform: translateY(20px); }}
    100% {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes popIn {{
    0% {{ opacity: 0; transform: scale(0.92) translateY(10px); }}
    70% {{ transform: scale(1.02); }}
    100% {{ opacity: 1; transform: scale(1) translateY(0); }}
}}
@keyframes gradientShift {{
    0% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}
@keyframes pulseGlow {{
    0% {{ box-shadow: 0 0 0 0 var(--pulse-color); }}
    70% {{ box-shadow: 0 0 0 10px rgba(0,0,0,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(0,0,0,0); }}
}}

.hero-content {{ animation: fadeInUp 0.7s cubic-bezier(0.16, 1, 0.3, 1) forwards; }}
.stagger-1 {{ animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.1s forwards; opacity: 0; }}
.stagger-2 {{ animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.2s forwards; opacity: 0; }}
.stagger-3 {{ animation: fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) 0.3s forwards; opacity: 0; }}

.animated-gradient-text {{
    background: linear-gradient(-45deg, var(--grad-1), var(--grad-2), var(--grad-3), var(--grad-1));
    background-size: 300% 300%;
    animation: gradientShift 6s ease infinite;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    display: inline-block;
}}

[data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{ animation: popIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards; }}
div[data-testid="stExpander"] {{ animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards; }}

/* =========================================
   INTERACTIVE COMPONENT HOVERS
========================================= */
.feature-card {{
    padding: 20px; border-radius: 10px; border: 1px solid var(--border-color);
    background: var(--card-bg); height: 100%; transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative; overflow: hidden;
}}
.feature-card::before {{
    content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 2px;
    background: linear-gradient(90deg, transparent, var(--grad-1), transparent);
    transform: translateX(-100%); transition: transform 0.6s ease;
}}
.feature-card:hover {{ transform: translateY(-6px) scale(1.02); box-shadow: 0 12px 24px var(--shadow-color); border-color: var(--grad-2); }}
.feature-card:hover::before {{ transform: translateX(100%); }}

.stButton>button {{
    border-radius: 6px !important; font-weight: 500 !important; font-size: 0.88rem !important;
    padding: 0.55rem 1.2rem !important; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
    position: relative; overflow: hidden;
}}
.stButton>button:hover {{ transform: translateY(-2px); box-shadow: 0 6px 14px var(--shadow-color) !important; }}
.stButton>button:active {{ transform: translateY(1px) scale(0.97); }}
.stButton>button[kind="primary"] {{ animation: pulseGlow 2.5s infinite; }}
.stButton>button[kind="primary"]:hover {{ animation: none; }}

.stTextArea textarea, .stTextInput input {{ transition: all 0.3s ease !important; }}
.stTextArea textarea:hover, .stTextInput input:hover {{ border-color: var(--grad-2) !important; }}
.stTextArea textarea:focus, .stTextInput input:focus {{ transform: translateY(-1px); box-shadow: 0 4px 12px var(--shadow-color) !important; border-color: var(--grad-1) !important; }}

[data-testid="stFileUploader"] section {{ transition: all 0.3s ease !important; }}
[data-testid="stFileUploader"] section:hover {{ transform: translateY(-2px); border-color: var(--grad-2) !important; background-color: var(--badge-bg) !important; }}

div[data-testid="stExpander"] {{ transition: all 0.3s ease !important; }}
div[data-testid="stExpander"]:hover {{ border-color: var(--grad-2) !important; box-shadow: 0 4px 12px var(--shadow-color) !important; }}

.stTabs [data-baseweb="tab-list"] {{ gap: 12px; border-bottom: 1px solid var(--border-color); padding-bottom: 4px; }}
.stTabs [data-baseweb="tab"] {{ border-radius: 6px 6px 0 0; padding: 8px 18px; font-weight: 500; font-size: 0.92rem; transition: all 0.3s ease !important; }}
.stTabs [data-baseweb="tab"]:hover {{ background-color: var(--badge-bg) !important; transform: translateY(-2px); }}

.route-badge {{ transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); animation: popIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards; }}
.route-badge:hover {{ transform: translateY(-3px) scale(1.02); box-shadow: 0 6px 16px var(--shadow-color); }}

.ambient-bg {{ position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: -999; overflow: hidden; pointer-events: none; }}
.ambient-orb-1, .ambient-orb-2 {{ position: absolute; border-radius: 50%; filter: blur(80px); animation: floatGlow 18s ease-in-out infinite alternate; }}
.ambient-grid {{ position: absolute; width: 100%; height: 100%; background-size: 40px 40px; opacity: 0.8; }}
</style>
"""

# Theme Dependent Palette & Variables
if st.session_state.dark_mode:
    theme_css = """
<style>
:root {
    --bg-main: #0B0F17;
    --card-bg: #111827;
    --input-bg: #161F30;
    --border-color: #27354A;
    --text-primary: #F9FAFB;
    --text-muted: #94A3B8;
    
    --grad-1: #0284C7;
    --grad-2: #8B5CF6;
    --grad-3: #38BDF8;
    --shadow-color: rgba(2, 132, 199, 0.15);
    --pulse-color: rgba(2, 132, 199, 0.4);
    --badge-bg: rgba(2, 132, 199, 0.1);
}
.stApp { background-color: transparent; }
.stAppViewContainer { background-color: var(--bg-main); color: var(--text-primary); }

.ambient-bg { background-color: #080C14; }
.ambient-orb-1 { width: 450px; height: 450px; top: 5%; left: 15%; background: radial-gradient(circle, rgba(14, 116, 144, 0.28) 0%, rgba(0,0,0,0) 70%); }
.ambient-orb-2 { width: 500px; height: 500px; bottom: 10%; right: 10%; background: radial-gradient(circle, rgba(79, 70, 229, 0.22) 0%, rgba(0,0,0,0) 70%); }
.ambient-grid { background-image: linear-gradient(to right, rgba(255, 255, 255, 0.02) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.02) 1px, transparent 1px); }

.stButton>button { background-color: #1A2333 !important; color: #F3F4F6 !important; border: 1px solid #334155 !important; }
.stButton>button:hover { background-color: #243046 !important; border-color: #475569 !important; color: #FFFFFF !important; }
.stButton>button[kind="primary"] { background-color: #0284C7 !important; border-color: #0369A1 !important; color: #FFFFFF !important; }

h1, h2, h3, h4, h5, h6 { color: var(--text-primary) !important; }
.stMarkdown p { color: var(--text-primary) !important; }
label, .stWidgetLabel, .stWidgetLabel p { color: var(--text-primary) !important; font-weight: 500 !important; }
div[data-testid="stMetricValue"] { color: var(--text-primary) !important; }
div[data-testid="stMetricLabel"] p { color: var(--text-muted) !important; }
.stCaption, .stCaption p { color: var(--text-muted) !important; }

.stTextArea textarea, .stTextInput input { background-color: var(--input-bg) !important; color: #F8FAFC !important; border: 1px solid var(--border-color) !important; border-radius: 6px !important; }
div[data-testid="stExpander"] { background-color: var(--card-bg) !important; border: 1px solid var(--border-color) !important; border-radius: 8px !important; }
div[data-testid="stExpander"] summary { color: var(--text-primary) !important; }
[data-testid="stFileUploader"] section { background-color: var(--input-bg) !important; border: 1px dashed var(--border-color) !important; }
[data-testid="stFileUploader"] section span, [data-testid="stFileUploader"] section small { color: var(--text-muted) !important; }
button[data-baseweb="tab"] { color: var(--text-muted) !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #38BDF8 !important; font-weight: 600 !important; border-bottom: 2px solid #38BDF8 !important; }
hr { border-color: var(--border-color); }
</style>
"""
    color_pred = "#38BDF8"       
    color_actual = "#34D399"     
    badge_edge_bg = "rgba(2, 132, 199, 0.14)"
    badge_edge_text = "#38BDF8"
    badge_cloud_bg = "rgba(217, 119, 6, 0.14)"
    badge_cloud_text = "#FBBF24"
    chart_bg = "rgba(0,0,0,0)"
    grid_color = "#1E293B"
    text_chart = "#94A3B8"
else:
    theme_css = """
<style>
:root {
    --bg-main: #F8FAFC;
    --card-bg: #FFFFFF;
    --input-bg: #FFFFFF;
    --border-color: #E2E8F0;
    --text-primary: #0F172A;
    --text-muted: #64748B;
    
    --grad-1: #0284C7;
    --grad-2: #4F46E5;
    --grad-3: #0EA5E9;
    --shadow-color: rgba(15, 23, 42, 0.08);
    --pulse-color: rgba(2, 132, 199, 0.25);
    --badge-bg: rgba(2, 132, 199, 0.05);
}
.stApp { background-color: transparent; }
.stAppViewContainer { background-color: var(--bg-main); color: var(--text-primary); }

.ambient-bg { background-color: #F8FAFC; }
.ambient-orb-1 { width: 450px; height: 450px; top: 0%; left: 20%; background: radial-gradient(circle, rgba(186, 230, 253, 0.6) 0%, rgba(255,255,255,0) 70%); }
.ambient-orb-2 { width: 500px; height: 500px; bottom: 15%; right: 15%; background: radial-gradient(circle, rgba(224, 231, 255, 0.6) 0%, rgba(255,255,255,0) 70%); }
.ambient-grid { background-image: linear-gradient(to right, rgba(15, 23, 42, 0.035) 1px, transparent 1px), linear-gradient(to bottom, rgba(15, 23, 42, 0.035) 1px, transparent 1px); }

.stButton>button { background-color: #FFFFFF !important; color: #1E293B !important; border: 1px solid #CBD5E1 !important; }
.stButton>button:hover { background-color: #F1F5F9 !important; border-color: #94A3B8 !important; }
.stButton>button[kind="primary"] { background-color: #0284C7 !important; border-color: #0369A1 !important; color: #FFFFFF !important; }

h1, h2, h3, h4, h5, h6 { color: var(--text-primary) !important; }
.stMarkdown p { color: var(--text-primary) !important; }
label, .stWidgetLabel, .stWidgetLabel p { color: var(--text-primary) !important; font-weight: 500 !important; }
div[data-testid="stMetricValue"] { color: var(--text-primary) !important; }
div[data-testid="stMetricLabel"] p { color: var(--text-muted) !important; }
.stCaption, .stCaption p { color: var(--text-muted) !important; }

.stTextArea textarea, .stTextInput input { background-color: var(--input-bg) !important; color: var(--text-primary) !important; border: 1px solid var(--border-color) !important; border-radius: 6px !important; }
div[data-testid="stExpander"] { background-color: var(--card-bg) !important; border: 1px solid var(--border-color) !important; border-radius: 8px !important; }
div[data-testid="stExpander"] summary { color: var(--text-primary) !important; }
[data-testid="stFileUploader"] section { background-color: #F1F5F9 !important; border: 1px dashed var(--border-color) !important; }
[data-testid="stFileUploader"] section span, [data-testid="stFileUploader"] section small { color: var(--text-muted) !important; }
button[data-baseweb="tab"] { color: var(--text-muted) !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #0284C7 !important; font-weight: 600 !important; border-bottom: 2px solid #0284C7 !important; }
hr { border-color: var(--border-color); }
</style>
"""
    color_pred = "#0284C7"       
    color_actual = "#059669"     
    badge_edge_bg = "rgba(2, 132, 199, 0.1)"
    badge_edge_text = "#0284C7"
    badge_cloud_bg = "rgba(217, 119, 6, 0.1)"
    badge_cloud_text = "#B45309"
    chart_bg = "rgba(0,0,0,0)"
    grid_color = "#E2E8F0"
    text_chart = "#475569"

st.markdown(base_css + theme_css, unsafe_allow_html=True)

# Render Global Live Ambient Background
st.markdown(
    """
    <div class="ambient-bg">
        <div class="ambient-orb-1"></div>
        <div class="ambient-orb-2"></div>
        <div class="ambient-grid"></div>
    </div>
    """,
    unsafe_allow_html=True
)

# 4. NEW: Global System Telemetry Bar (Fills Top Void)
st.markdown(
    """
    <div class="system-status-bar">
        <div class="status-item">
            <span class="status-indicator indicator-blue"></span>
            Edge Compute Node: Local
        </div>
        <div class="status-item">
            <span class="status-indicator indicator-green"></span>
            Cloud Worker: AWS EC2
        </div>
        <div class="status-item">
            <span class="status-indicator indicator-purple"></span>
            Active Model: RandomForest
        </div>
    </div>
    """, 
    unsafe_allow_html=True
)

# 5. Top Navigation Bar
nav_col1, _, nav_col3 = st.columns([2.5, 6.5, 2])
with nav_col1:
    if st.session_state.current_page == 'dashboard':
        if st.button("Back to Overview"):
            st.session_state.current_page = 'landing'
            st.rerun()

with nav_col3:
    is_dark = st.toggle("Dark Theme", value=st.session_state.dark_mode)
    if is_dark != st.session_state.dark_mode:
        st.session_state.dark_mode = is_dark
        st.rerun()

st.markdown("<hr style='margin: 0.6rem 0 1.6rem 0; opacity: 0.5;'>", unsafe_allow_html=True)


# 6. Execution & Clustered Visualization Helper
def process_code_payload(code_string, filename, local_url, cloud_url, scheduler_instance):
    schedule_res = scheduler_instance.schedule(code_string)
    
    if "error" in schedule_res:
        st.error(f"Analysis Failed for {filename}: {schedule_res['error']}")
        return

    preds = schedule_res["predictions"]
    decision = schedule_res["decision"]
    target_name = "Edge Node (Local)" if decision == "EDGE" else "Cloud Node (AWS)"
    target_url = local_url if decision == "EDGE" else cloud_url
    badge_bg = badge_edge_bg if decision == "EDGE" else badge_cloud_bg
    badge_text = badge_edge_text if decision == "EDGE" else badge_cloud_text

    m1, m2, m3 = st.columns([1, 1, 1.4])
    with m1:
        st.metric(label="Predicted Edge Latency", value=f"{preds['predicted_edge_time']} s")
    with m2:
        st.metric(label="Predicted Cloud Latency", value=f"{preds['predicted_cloud_time']} s")
    with m3:
        st.markdown(
            f"""
            <div class="route-badge" style="background: {badge_bg}; border-color: {badge_text}40;">
                <span style="font-size: 0.76rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); display: block;">Routing Decision</span>
                <span style="font-size: 1.15rem; font-weight: 700; color: {badge_text} !important;">{target_name}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    worker_data = None
    total_rtt = 0.0
    with st.spinner(f"Dispatched to {target_name}. Measuring response..."):
        req_start = time.perf_counter()
        try:
            response = requests.post(target_url, json={"code": code_string}, timeout=65)
            total_rtt = time.perf_counter() - req_start
            worker_data = response.json()
        except Exception as ex:
            st.error(f"Execution failed on {target_url}: {ex}")

    if worker_data:
        st.markdown("<div class='stagger-1'>", unsafe_allow_html=True)
        out_col, chart_col = st.columns([1.1, 1.3])
        with out_col:
            st.markdown("##### Standard Output")
            if worker_data.get("stdout"):
                st.code(worker_data["stdout"], language="text")
            if worker_data.get("stderr"):
                st.error(worker_data["stderr"])
            
            st.caption(
                f"Worker Compute: {worker_data.get('execution_time_seconds', 0):.4f}s  |  "
                f"Network RTT: {total_rtt:.4f}s"
            )

        with chart_col:
            st.markdown("##### Performance Comparison by Node")
            categories = ["Edge (Local)", "Cloud (AWS)"]
            pred_values = [preds["predicted_edge_time"], preds["predicted_cloud_time"]]
            actual_values = [
                total_rtt if decision == "EDGE" else 0,
                total_rtt if decision == "CLOUD" else 0
            ]
            actual_texts = [
                f"{total_rtt:.4f} s" if decision == "EDGE" else "Not Dispatched",
                f"{total_rtt:.4f} s" if decision == "CLOUD" else "Not Dispatched"
            ]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Predicted",
                x=categories,
                y=pred_values,
                marker_color=color_pred,
                text=[f"{v:.4f} s" for v in pred_values],
                textposition="outside",
                hovertemplate="<b>%{x} (Predicted)</b>: %{y:.4f} s<extra></extra>"
            ))
            fig.add_trace(go.Bar(
                name="Actual",
                x=categories,
                y=actual_values,
                marker_color=color_actual,
                text=actual_texts,
                textposition="outside",
                hovertemplate="<b>%{x} (Actual)</b>: %{text}<extra></extra>"
            ))

            all_vals = pred_values + [total_rtt]
            max_y = max(all_vals) if all_vals else 1.0

            fig.update_layout(
                barmode="group", bargap=0.3, bargroupgap=0.08,
                paper_bgcolor=chart_bg, plot_bgcolor=chart_bg, height=260,
                margin=dict(l=10, r=10, t=30, b=25),
                font=dict(color=text_chart, family="Inter, sans-serif", size=12),
                legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0, font=dict(size=11, color=text_chart)),
                xaxis=dict(showgrid=False, linecolor=grid_color, tickfont=dict(size=12, color=text_chart)),
                yaxis=dict(showgrid=True, gridcolor=grid_color, zeroline=True, zerolinecolor=grid_color, range=[0, max_y * 1.35], ticksuffix=" s", tickfont=dict(size=11, color=text_chart))
            )
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# PAGE 1: STREAMLINED LANDING PAGE
# ==========================================
if st.session_state.current_page == 'landing':
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
        <div class='hero-content' style='text-align: center;'>
            <span style='padding: 5px 14px; border-radius: 9999px; font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; border: 1px solid var(--border-color); background: var(--badge-bg); color: var(--grad-1); display: inline-block; margin-bottom: 1rem;'>
                Intelligent Workload Engine
            </span>
            <h1 style='font-size: 3rem; font-weight: 800; margin-top: 0; margin-bottom: 0.8rem;'>
                <span class="animated-gradient-text">Predictive Code Orchestration</span>
            </h1>
            <p style='font-size: 1.12rem; color: var(--text-muted); max-width: 640px; margin: 0 auto 2.5rem auto; line-height: 1.6;'>
                Analyze Python AST structures to forecast hardware execution latency and dynamically route tasks between Edge and Cloud environments.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.markdown(
            """
            <div class="feature-card stagger-1">
                <h4 style="margin: 0 0 10px 0; font-size: 1.05rem; font-weight: 600;">Static Code Analysis</h4>
                <p style="font-size: 0.88rem; color: var(--text-muted); line-height: 1.5; margin: 0;">Extracts loop depths, numerical complexity, and library overhead instantly without executing the code.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_f2:
        st.markdown(
            """
            <div class="feature-card stagger-2">
                <h4 style="margin: 0 0 10px 0; font-size: 1.05rem; font-weight: 600;">Latency Prediction</h4>
                <p style="font-size: 0.88rem; color: var(--text-muted); line-height: 1.5; margin: 0;">Evaluates hardware thresholds using non-linear models to accurately project runtime durations.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_f3:
        st.markdown(
            """
            <div class="feature-card stagger-3">
                <h4 style="margin: 0 0 10px 0; font-size: 1.05rem; font-weight: 600;">Automated Routing</h4>
                <p style="font-size: 0.88rem; color: var(--text-muted); line-height: 1.5; margin: 0;">Offloads tasks to AWS only when the execution benefits overcome the network round-trip delay.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<div class='stagger-3'>", unsafe_allow_html=True)
    _, c_btn2, _ = st.columns([2.5, 5, 2.5])
    with c_btn2:
        if st.button("Open Orchestration Dashboard", type="primary", use_container_width=True):
            st.session_state.current_page = 'dashboard'
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================
# PAGE 2: EXECUTION DASHBOARD
# ==========================================
elif st.session_state.current_page == 'dashboard':
    st.markdown("<div class='hero-content'>", unsafe_allow_html=True)
    st.markdown("<h2 style='font-weight: 700; margin-bottom: 0.15rem;'><span class='animated-gradient-text' style='animation-duration: 8s;'>Execution Control Center</span></h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-muted); font-size: 0.94rem; margin-bottom: 1.5rem;'>Execute code payloads with real-time dynamic latency routing.</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("System Endpoints & Network Topology Configuration"):
        c1, c2, c3 = st.columns(3)
        local_endpoint = c1.text_input("Edge Worker URL", "http://localhost:8000/execute")
        cloud_endpoint = c2.text_input("Cloud Worker URL", "http://localhost:8000/execute")
        cloud_rtt = c3.slider("Simulated Cloud Network RTT (ms)", 10, 500, 80)

    scheduler = OffloadingScheduler(cloud_rtt_ms=cloud_rtt)

    tab_manual, tab_batch = st.tabs(["Manual Payload Entry", "Batch Pipeline Evaluation"])

    # --- TAB 1: MANUAL ENTRY ---
    with tab_manual:
        st.markdown("<br>", unsafe_allow_html=True)
        default_code = """import numpy as np
import time

# Compute matrix calculation
size = 2000
A = np.random.rand(size, size)
B = np.random.rand(size, size)
C = np.dot(A, B)
print("Computation Complete! Resulting shape:", C.shape)"""

        user_code = st.text_area("Source Code", default_code, height=200, label_visibility="collapsed")
        
        c_btn, _ = st.columns([2.5, 7.5])
        with c_btn:
            st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
            run_btn = st.button("Dispatch Payload", type="primary", use_container_width=True)

        if run_btn:
            st.markdown("<hr style='margin: 1.5rem 0; opacity: 0.5;'>", unsafe_allow_html=True)
            process_code_payload(user_code, "Manual Input", local_endpoint, cloud_endpoint, scheduler)

    # --- TAB 2: BATCH PROCESSING ---
    with tab_batch:
        st.markdown("<br>", unsafe_allow_html=True)
        uploaded_files = st.file_uploader(
            "Upload Python Files (.py)",
            type=["py"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

        if uploaded_files:
            st.markdown(f"<p style='color: var(--text-muted); font-size: 0.88rem; animation: popIn 0.3s forwards;'>Queued files: <b>{len(uploaded_files)}</b></p>", unsafe_allow_html=True)

        if st.button("Execute Batch Pipeline", type="primary"):
            if not uploaded_files:
                st.warning("Please upload one or more Python files.")
            else:
                for file in uploaded_files:
                    file_name = file.name
                    file_content = file.getvalue().decode("utf-8")

                    with st.expander(f"File: {file_name}", expanded=True):
                        st.code(file_content, language="python")
                        st.markdown("<hr style='margin: 1rem 0; opacity: 0.5;'>", unsafe_allow_html=True)
                        process_code_payload(file_content, file_name, local_endpoint, cloud_endpoint, scheduler)