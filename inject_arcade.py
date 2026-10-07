import re

with open('app.py', 'r') as f:
    content = f.read()

# 1. Add "Back to Arcade" in the sidebar
sidebar_injection = """
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
"""
content = content.replace("st.session_state.last_result = None", "st.session_state.last_result = None\n" + sidebar_injection)

# 2. Replace st.balloons() with a massive arcade overlay
arcade_overlay = '''
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
'''
content = content.replace("st.balloons()", arcade_overlay.strip())

with open('app.py', 'w') as f:
    f.write(content)

print("Arcade injection complete!")
