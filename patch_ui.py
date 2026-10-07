import re

with open('app.py', 'r') as f:
    content = f.read()

# 1. Update CSS Theme Vars
retro_dark_vars = """
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

retro_light_vars = """
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

# Replace the theme blocks
content = re.sub(r'(--bg-canvas: #07080B;.*?--grid-dot-color: rgba\(255, 255, 255, 0\.06\);)', retro_dark_vars.strip(), content, flags=re.DOTALL)
content = re.sub(r'(--bg-canvas: #F8FAFC;.*?--grid-dot-color: rgba\(0, 0, 0, 0\.04\);)', retro_light_vars.strip(), content, flags=re.DOTALL)

# 2. Update Fonts to Retro Fonts
content = re.sub(r"url\('https://fonts\.googleapis\.com/css2.*?display=swap'\)", "url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap')", content)
content = re.sub(r"--font-heading: 'Space Grotesk', -apple-system, sans-serif;", "--font-heading: 'Press Start 2P', cursive;", content)
content = re.sub(r"--font-body: 'Inter', -apple-system, sans-serif;", "--font-body: 'VT323', monospace;", content)
content = re.sub(r"--font-mono: 'JetBrains Mono', Consolas, monospace;", "--font-mono: 'VT323', monospace;", content)

# 3. Retro borders and removal of blur
content = content.replace("border-radius: 10px;", "border-radius: 0px;")
content = content.replace("border-radius: 8px;", "border-radius: 0px;")
content = content.replace("border-radius: 6px;", "border-radius: 0px;")
content = content.replace("backdrop-filter: blur(14px);", "")
content = content.replace("-webkit-backdrop-filter: blur(14px);", "")
content = content.replace("backdrop-filter: blur(8px);", "")
content = content.replace("-webkit-backdrop-filter: blur(8px);", "")
content = content.replace("border: 1px solid var(--border-color);", "border: 4px solid var(--border-color); box-shadow: var(--card-shadow);")
content = content.replace("border: 1px solid", "border: 4px solid")
content = content.replace("border:1px solid", "border:4px solid")

# Add some global streamlit button styling via CSS inject
css_inject = """
.stButton>button {
    font-family: 'Press Start 2P', cursive !important;
    border: 4px solid var(--border-color) !important;
    border-radius: 0 !important;
    box-shadow: 6px 6px 0px var(--bg-canvas) !important;
    transition: all 0.1s !important;
    text-transform: uppercase !important;
}
.stButton>button:active {
    transform: translate(4px, 4px) !important;
    box-shadow: 2px 2px 0px var(--bg-canvas) !important;
}
.stSelectbox>div>div, .stTextInput>div>div, .stTextArea>div>div {
    border: 4px solid var(--border-color) !important;
    border-radius: 0 !important;
}
"""
content = content.replace("/* Smooth View Transitions */", css_inject + "\n/* Smooth View Transitions */")

# 4. Fix Plotly Charts Width Warning
content = content.replace("use_container_width=True", 'use_container_width=True, width="stretch"')

# 5. Add execution animations (toast and balloons)
# Find execution block
spinner_block = """    with st.spinner(f"Executing payload on {target_name}..."):
        req_start = time.perf_counter()
        try:
            response = requests.post(target_url, json={"code": code_string}, timeout=65)
            total_rtt = time.perf_counter() - req_start
            worker_data = response.json()
        except Exception as ex:
            st.error(f"Execution failed on {target_url}: {ex}")"""

animated_block = """    st.toast(f"👾 [TRANSMITTING PAYLOAD TO {target_name}]", icon="🛰️")
    req_start = time.perf_counter()
    try:
        response = requests.post(target_url, json={"code": code_string}, timeout=65)
        total_rtt = time.perf_counter() - req_start
        worker_data = response.json()
        st.toast(f"✅ [EXECUTION COMPLETE ON {target_name}]", icon="🏆")
        st.balloons()
    except Exception as ex:
        st.error(f"Execution failed on {target_url}: {ex}")"""

content = content.replace(spinner_block, animated_block)

# Replace batch execution spinner
batch_spinner = """                with st.spinner(f"Simulating live routing... ({idx}/{len(batch_cases)})"):
                    try:"""

batch_animated = """                st.toast(f"🕹️ [ROUTING PAYLOAD {idx}/{len(batch_cases)}]", icon="📡")
                try:"""
content = content.replace(batch_spinner, batch_animated)

# After batch completes
batch_complete = """        st.success(f"Batch Execution Complete! Processed {len(batch_cases)} workloads.")"""
batch_complete_animated = """        st.success(f"Batch Execution Complete! Processed {len(batch_cases)} workloads.")
        st.balloons()
        st.snow()"""
content = content.replace(batch_complete, batch_complete_animated)


with open('app.py', 'w') as f:
    f.write(content)

print("UI successfully patched!")
