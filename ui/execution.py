"""Schedule, dispatch and show one workload."""
import time

import plotly.graph_objects as go
import requests
import streamlit as st

import config


def execute_workload(ctx, code_string, filename, local_url, cloud_url, scheduler_instance):
    chart_act, chart_grid, chart_pred, chart_text = ctx.chart_act, ctx.chart_grid, ctx.chart_pred, ctx.chart_text
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
    if not is_edge and not cloud_url:
        st.warning("Scheduler chose the cloud, but CLOUD_WORKER_URL is not set (see .env.example). "
                   "Running on the local edge worker instead.")
        target_name, target_url, is_edge = "Local Edge Worker", local_url, True

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
        response = requests.post(target_url, json={"code": code_string},
                                 headers=config.auth_headers(), timeout=65)
        total_rtt = time.perf_counter() - req_start
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
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
