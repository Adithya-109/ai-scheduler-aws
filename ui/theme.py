"""Colours and CSS. build(mode) returns every theme value as a namespace."""

from types import SimpleNamespace

_LIGHT = """
        --bg-canvas: #f6f7f9;
        --surface-card: #ffffff;
        --surface-hover: #f1f3f7;
        --surface-well: #f3f4f8;
        --border-color: #e3e6ec;
        --border-hover: #c7cdf5;
        --border-subtle: rgba(16, 24, 40, 0.06);
        --text-pure: #101828;
        --text-primary: #1d2939;
        --text-muted: #667085;
        --accent-amber: #4f46e5;
        --accent-amber-hover: #4338ca;
        --accent-amber-glow: rgba(79, 70, 229, 0.18);
        --accent-emerald: #059669;
        --accent-purple: #7c3aed;
        --accent-cyan: #0891b2;
        --input-bg: #ffffff;
        --card-shadow: 0 1px 2px rgba(16, 24, 40, 0.05), 0 1px 3px rgba(16, 24, 40, 0.06);
        --grid-dot-color: rgba(16, 24, 40, 0.05);
"""

_DARK = """
        --bg-canvas: #0d1117;
        --surface-card: #161b22;
        --surface-hover: #1c2330;
        --surface-well: #11161d;
        --border-color: #262d38;
        --border-hover: #3b4577;
        --border-subtle: rgba(255, 255, 255, 0.06);
        --text-pure: #f0f3f8;
        --text-primary: #d5dbe6;
        --text-muted: #8b95a7;
        --accent-amber: #8b93ff;
        --accent-amber-hover: #a5abff;
        --accent-amber-glow: rgba(139, 147, 255, 0.22);
        --accent-emerald: #34d399;
        --accent-purple: #a78bfa;
        --accent-cyan: #22d3ee;
        --input-bg: #0d1117;
        --card-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
        --grid-dot-color: rgba(255, 255, 255, 0.04);
"""


def build(mode: str) -> SimpleNamespace:
    is_dark = mode == "dark"
    theme_vars = _DARK if is_dark else _LIGHT
    chart_text = "#8b95a7" if is_dark else "#475467"
    chart_grid = "rgba(255, 255, 255, 0.07)" if is_dark else "rgba(16, 24, 40, 0.07)"
    chart_pred = "#8b93ff" if is_dark else "#4f46e5"
    chart_act = "#34d399" if is_dark else "#059669"
    primary_text = "#0d1117" if is_dark else "#ffffff"

    custom_css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {{
        display: none !important;
    }}

    :root {{
        {theme_vars}
        --font-heading: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif;
        --font-body: 'Inter', -apple-system, 'Segoe UI', Roboto, sans-serif;
        --font-mono: 'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace;
    }}

    html, body, .stApp {{
        background-color: var(--bg-canvas) !important;
        font-family: var(--font-body) !important;
        color: var(--text-primary) !important;
        overflow-x: hidden !important;
    }}

    .live-bg-container {{ display: none !important; }}

    .main .block-container {{
        max-width: 1180px !important;
        padding: 1.4rem 2rem 4rem 2rem !important;
        margin: 0 auto !important;
    }}

    h1, h2, h3, h4, h5, h6 {{
        font-family: var(--font-heading) !important;
        letter-spacing: -0.02em !important;
        color: var(--text-pure) !important;
        font-weight: 650 !important;
    }}
    p, li, label {{ font-family: var(--font-body) !important; }}

    .fluid-view {{ animation: fluidFadeIn 0.25s ease-out forwards; }}
    @keyframes fluidFadeIn {{
        from {{ opacity: 0; transform: translateY(6px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .gradient-text {{ color: var(--accent-amber); }}

    .dev-card {{
        background: var(--surface-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.4rem 1.4rem;
        box-shadow: var(--card-shadow);
        height: 100%;
        transition: border-color 0.15s ease;
    }}
    .dev-card:hover {{ border-color: var(--border-hover); }}

    .tech-chip {{
        font-family: var(--font-body);
        font-size: 0.72rem;
        font-weight: 500;
        padding: 3px 10px;
        border-radius: 999px;
        background: var(--surface-well);
        border: 1px solid var(--border-color);
        color: var(--text-muted);
        display: inline-flex;
        align-items: center;
        gap: 6px;
        white-space: nowrap;
    }}

    .pulse-dot, .pulse-dot-amber {{
        width: 7px; height: 7px; border-radius: 50%;
        display: inline-block; background-color: var(--accent-emerald);
    }}
    .pulse-dot-amber {{ background-color: var(--accent-amber); }}

    /* Buttons */
    .stButton>button {{
        font-family: var(--font-body) !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 0.5rem 1rem !important;
        border-radius: 8px !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
        white-space: nowrap !important;
        transition: background 0.15s ease, border-color 0.15s ease !important;
    }}
    .stButton>button p {{ font-size: 0.88rem !important; font-weight: 600 !important; margin: 0 !important; }}
    .stButton>button[data-testid="baseButton-primary"] {{
        background: var(--accent-amber) !important;
        color: {primary_text} !important;
        border: 1px solid var(--accent-amber) !important;
        box-shadow: var(--card-shadow) !important;
    }}
    .stButton>button[data-testid="baseButton-primary"] p {{ color: {primary_text} !important; }}
    .stButton>button[data-testid="baseButton-primary"]:hover {{
        background: var(--accent-amber-hover) !important;
        border-color: var(--accent-amber-hover) !important;
    }}
    .stButton>button:not([data-testid="baseButton-primary"]) {{
        background: var(--surface-card) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        box-shadow: var(--card-shadow) !important;
    }}
    .stButton>button:not([data-testid="baseButton-primary"]):hover {{
        background: var(--surface-hover) !important;
        border-color: var(--border-hover) !important;
        color: var(--text-pure) !important;
    }}

    /* Inputs */
    .stTextArea textarea, .stTextInput input {{
        background-color: var(--input-bg) !important;
        color: var(--text-pure) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        font-family: var(--font-mono) !important;
        font-size: 0.84rem !important;
        line-height: 1.55 !important;
        padding: 0.75rem !important;
    }}
    .stTextArea textarea:focus, .stTextInput input:focus {{
        border-color: var(--accent-amber) !important;
        box-shadow: 0 0 0 3px var(--accent-amber-glow) !important;
    }}
    .stSelectbox>div>div {{ border-radius: 8px !important; }}

    /* Decision card */
    .decision-banner {{
        background: var(--surface-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: var(--card-shadow);
    }}
    .decision-banner.edge-decision {{ border-left: 4px solid var(--accent-emerald); }}
    .decision-banner.cloud-decision {{ border-left: 4px solid var(--accent-amber); }}

    /* Metrics */
    div[data-testid="stMetricValue"] {{
        color: var(--text-pure) !important;
        font-family: var(--font-heading) !important;
        font-weight: 650 !important;
        font-size: 1.6rem !important;
    }}
    div[data-testid="stMetricLabel"] p {{
        color: var(--text-muted) !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
    }}

    /* Theme toggle */
    [data-testid="stToggle"] {{ display: flex; align-items: center; justify-content: flex-end; }}
    [data-testid="stToggle"] p {{
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: var(--text-muted) !important;
        margin: 0 !important;
        white-space: nowrap !important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 2px !important;
        background: var(--surface-well) !important;
        padding: 4px !important;
        border-radius: 10px !important;
        border: 1px solid var(--border-color) !important;
        width: fit-content !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-family: var(--font-body) !important;
        font-weight: 500 !important;
        font-size: 0.86rem !important;
        padding: 6px 16px !important;
        border-radius: 7px !important;
        color: var(--text-muted) !important;
        background: transparent !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: var(--surface-card) !important;
        color: var(--text-pure) !important;
        box-shadow: var(--card-shadow) !important;
    }}
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display: none !important; }}

    .dev-footer {{
        margin-top: 3.5rem;
        padding-top: 1.4rem;
        border-top: 1px solid var(--border-color);
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.8rem;
        color: var(--text-muted);
    }}
    </style>
    """
    return SimpleNamespace(
        chart_act=chart_act,
        chart_grid=chart_grid,
        chart_pred=chart_pred,
        chart_text=chart_text,
        custom_css=custom_css,
        is_dark=is_dark,
        theme_vars=theme_vars,
    )
