"""Schedule, dispatch and show one workload."""

import plotly.graph_objects as go
import streamlit as st


def execute_workload(ctx, code_string, filename, dispatcher):
    """Schedule and run one script through the Dispatcher (fallback, circuit
    breaker, live RTT, history and the decision log all apply)."""
    chart_act, chart_grid, chart_pred, chart_text = ctx.chart_act, ctx.chart_grid, ctx.chart_pred, ctx.chart_text
    st.toast("Scheduling and dispatching", icon="🛰️")
    try:
        res = dispatcher.run(code_string)
    except Exception as ex:  # an edge failure is a real error; cloud errors fall back inside run()
        st.error(f"Execution failed: {ex}")
        return

    if "error" in res:
        st.error(f"AST Parsing Failed for {filename}: {res['error']}")
        return

    preds = res["predictions"]
    decision = res["decision"]
    confidence = res.get("confidence", 0)
    decision_method = res.get("decision_method", "regression")
    is_edge = res["target"] == "edge"
    target_name = "the local edge worker" if is_edge else "the AWS cloud worker"
    target_url = dispatcher.edge.url if is_edge else dispatcher.cloud.url
    if res.get("fallback"):
        st.warning(f"The scheduler chose {decision} but the job ran on the local edge worker ({res['fallback']}).")
    if res.get("explored"):
        st.info("Exploration run: this low-confidence job was sent to the other side so the models see both.")

    st.markdown("<br>", unsafe_allow_html=True)

    banner_class = "edge-decision" if is_edge else "cloud-decision"
    badge_color = "#059669" if is_edge else "var(--accent-amber)"

    st.markdown(
        f"""
        <div class="decision-banner {banner_class}" style="margin: 1.5rem 0 1.2rem 0;">
            <div>
                <div style="font-family: var(--font-mono); font-size: 0.72rem;  color: var(--text-muted); margin-bottom: 4px;">
                    Routing decision · {decision_method} · {confidence:.0%} confidence
                </div>
                <div style="font-family: var(--font-heading); font-size: 1.3rem; font-weight: 700; color: {badge_color};">
                    Ran on {target_name}
                </div>
            </div>
            <div class="tech-chip" style="font-size: 0.8rem; padding: 5px 12px;">
                {target_url}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    m1, m2, m3 = st.columns(3, gap="medium")
    with m1:
        st.metric(label="Predicted edge time", value=f"{preds['predicted_edge_time']:.4f} s")
    with m2:
        st.metric(label="Predicted cloud time", value=f"{preds['predicted_cloud_time']:.4f} s")
    with m3:
        speedup = (preds['predicted_edge_time'] - preds['predicted_cloud_time'])
        st.metric(label="Predicted saving from offload", value=f"{speedup:+.4f} s", delta="Cloud faster" if speedup > 0 else "Edge faster")

    worker_data = res["worker"]
    total_rtt = res["wall_time_s"]
    st.markdown(
        """
    <style>
    @keyframes doneBanner {
        0%   { opacity: 0; transform: translate(-50%, -14px); }
        12%  { opacity: 1; transform: translate(-50%, 0); }
        78%  { opacity: 1; transform: translate(-50%, 0); }
        100% { opacity: 0; transform: translate(-50%, -6px); visibility: hidden; }
    }
    .done-banner {
        position: fixed; top: 18px; left: 50%; z-index: 999999; pointer-events: none;
        padding: 14px 28px; min-width: 300px; border-radius: 12px; text-align: center;
        background: var(--surface-card); color: var(--text-pure);
        border: 1px solid var(--border-color); box-shadow: var(--card-shadow);
        font-family: var(--font-heading); font-size: 0.95rem; letter-spacing: 0.02em;
        animation: doneBanner 1.6s ease-out forwards;
    }
    .done-banner b { color: var(--accent-emerald); }
    .done-banner span { font-family: var(--font-mono); font-size: 0.85rem; color: var(--text-muted); }
    </style>
    <div class="done-banner"><b>Done</b> &middot; ran on __TARGET__<br><span>__TIME__ s round trip</span></div>
    """.replace("__TARGET__", "the edge worker" if is_edge else "the cloud worker").replace("__TIME__", f"{total_rtt:.3f}"),
        unsafe_allow_html=True,
    )

    if worker_data:
        st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
        col_out, col_chart = st.columns([1.1, 1.3], gap="large")

        with col_out:
            st.markdown(
                """
                <div style="background: var(--surface-well); border: 1px solid var(--border-color); box-shadow: var(--card-shadow); border-radius: 8px; padding: 8px 12px; margin-bottom: 8px; font-family: var(--font-mono); font-size: 0.75rem; color: var(--text-muted); display: flex; justify-content: space-between;">
                    <span>Output</span>
                    <span style="color:#059669;">200 OK</span>
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
                    Worker compute: <b style="color:var(--text-pure);">{worker_data.get('execution_time_seconds', 0):.4f}s</b> &nbsp;|&nbsp;
                    Round trip: <b style="color:var(--accent-amber);">{total_rtt:.4f}s</b>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_chart:
            st.markdown(
                """
                <div style="font-family: var(--font-heading); font-size: 1.05rem; font-weight: 700; color: var(--text-pure); margin-bottom: 8px;">
                    Predicted vs. measured time
                </div>
                """,
                unsafe_allow_html=True
            )
            categories = ["Edge", "Cloud"]
            pred_values = [preds["predicted_edge_time"], preds["predicted_cloud_time"]]
            actual_values = [
                total_rtt if is_edge else 0,
                total_rtt if not is_edge else 0
            ]
            actual_texts = [
                f"{total_rtt:.4f} s" if is_edge else "not used",
                f"{total_rtt:.4f} s" if not is_edge else "not used"
            ]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Predicted",
                x=categories,
                y=pred_values,
                marker_color=chart_pred,
                text=[f"{v:.4f} s" for v in pred_values],
                textposition="outside",
                hovertemplate="<b>%{x} (Predicted)</b>: %{y:.4f} s<extra></extra>"
            ))
            fig.add_trace(go.Bar(
                name="Measured (round trip)",
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
                font=dict(color=chart_text, family="Inter, sans-serif", size=11),
                legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="left", x=0, font=dict(size=11, color=chart_text)),
                xaxis=dict(showgrid=False, linecolor=chart_grid, tickfont=dict(size=11, color=chart_text)),
                yaxis=dict(showgrid=True, gridcolor=chart_grid, zeroline=True, zerolinecolor=chart_grid, range=[0, max_y * 1.35], ticksuffix=" s", tickfont=dict(size=11, color=chart_text))
            )
            st.plotly_chart(fig, use_container_width=True, width="stretch")
