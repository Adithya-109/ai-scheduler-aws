"""Streamlit entry point. Thin on purpose: state, theme, header, page dispatch.

Pages live in ui/pages/, shared widgets in ui/. Run:  streamlit run app.py
"""
import importlib
import sys
from types import SimpleNamespace

import streamlit as st

# Keep pipeline modules fresh across Streamlit reruns.
for _m in ("pipeline.feature_extractor", "pipeline.predictor", "pipeline.scheduler", "pipeline.history"):
    if _m in sys.modules:
        importlib.reload(sys.modules[_m])

import config
from pipeline import reporting
from pipeline.scheduler import OffloadingScheduler
from ui import header, theme
from ui.execution import execute_workload
from ui.pages import endpoints, overview, playground, telemetry


@st.cache_resource
def get_scheduler(rtt_ms):
    # Loading the models costs ~100 ms; do it once per RTT setting, not per rerun.
    return OffloadingScheduler(cloud_rtt_ms=rtt_ms)


@st.cache_data(show_spinner=False)
def get_summary():
    return reporting.summary()


@st.cache_data(show_spinner=False)
def get_curve(rtt_ms):
    return reporting.crossover_curve(rtt_ms)


STAT = get_summary()
SCHED_VS_EDGE = reporting.fmt_pct(STAT["sched_vs_edge_pct"])
CLOUD_HOST = config.CLOUD_WORKER_URL.split("//")[-1].split("/")[0] if config.CLOUD_WORKER_URL else "not configured"

st.set_page_config(page_title="AI SCHEDULER", page_icon=None, layout="wide", initial_sidebar_state="collapsed")

for _k, _v in (("current_tab", "overview"), ("theme_mode", "dark"), ("code_preset", "heavy"),
               ("sim_cloud_rtt", int(STAT["rtt_ms"])), ("last_result", None)):
    st.session_state.setdefault(_k, _v)

# Old links used app_view; map them onto current_tab.
if "app_view" in st.session_state:
    st.session_state.current_tab = (st.session_state.get("dashboard_tab", "playground")
                                    if st.session_state.app_view == "dashboard" else "overview")
    del st.session_state.app_view

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

T = theme.build(st.session_state.theme_mode)
st.markdown(T.custom_css, unsafe_allow_html=True)

ctx = SimpleNamespace(
    STAT=STAT, SCHED_VS_EDGE=SCHED_VS_EDGE, CLOUD_HOST=CLOUD_HOST,
    get_scheduler=get_scheduler, get_summary=get_summary, get_curve=get_curve,
    execute_workload=execute_workload, **vars(T))

header.render(ctx)

PAGES = {"overview": overview, "playground": playground, "endpoints": endpoints, "telemetry": telemetry}
PAGES.get(st.session_state.current_tab, overview).render(ctx)

# Footer
# 5. Minimalist Developer Footer
st.markdown(
    f"""
    <div class="dev-footer">
        <div>
            <b style="color: var(--text-pure);">AI SCHEDULER</b>
            &nbsp;·&nbsp; Cloud & Edge Hybrid Computing Engine &nbsp;·&nbsp; VIT CAD Project
        </div>
        <div style="display: flex; gap: 20px; align-items: center;">
            <span>Edge: localhost:8000</span>
            <span>Cloud: {CLOUD_HOST}</span>
            <span style="color: #10B981; display: inline-flex; align-items: center; gap: 5px;">
                <span class="pulse-dot"></span> Online
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
