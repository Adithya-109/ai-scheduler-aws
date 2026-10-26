"""playground page."""

import streamlit as st

from ui.execution import execute_workload


def render(ctx) -> None:
    get_dispatcher = ctx.get_dispatcher
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

    cloud_rtt = st.session_state.sim_cloud_rtt
    dispatcher = get_dispatcher(cloud_rtt)

    tab_manual, tab_batch = st.tabs(["Single Code Dispatch", "Multi-File Batch Evaluation"])

    with tab_manual:
        st.markdown("<div style='font-family: var(--font-heading); font-size: 0.92rem; font-weight: 700; margin: 12px 0 8px 0; color: var(--text-pure);'>Select Workload Preset:</div>", unsafe_allow_html=True)

        pr1, pr2, pr3, pr4 = st.columns(4, gap="small")
        with pr1:
            if st.button("Matrix Dot", use_container_width=True, width="stretch", type="primary" if st.session_state.code_preset == "heavy" else "secondary"):
                st.session_state.code_preset = "heavy"
                st.rerun()
        with pr2:
            if st.button("String Parse", use_container_width=True, width="stretch", type="primary" if st.session_state.code_preset == "light" else "secondary"):
                st.session_state.code_preset = "light"
                st.rerun()
        with pr3:
            if st.button("Fibonacci", use_container_width=True, width="stretch", type="primary" if st.session_state.code_preset == "fib" else "secondary"):
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
            if st.button("RUN WORKLOAD →", type="primary", use_container_width=True, width="stretch"):
                clicked = True

        if clicked:
            execute_workload(ctx, user_code, "Manual Input", dispatcher)

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

        if st.button("RUN ALL FILES →", type="primary"):
            if not uploaded_files:
                st.warning("Please upload one or more .py files to evaluate.")
            else:
                for file in uploaded_files:
                    file_name = file.name
                    file_content = file.getvalue().decode("utf-8")

                    with st.expander(f"Script: {file_name}", expanded=True):
                        st.code(file_content, language="python")
                        execute_workload(ctx, file_content, file_name, dispatcher)

    st.markdown("</div>", unsafe_allow_html=True)
