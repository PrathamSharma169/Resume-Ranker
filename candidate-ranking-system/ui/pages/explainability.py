"""
Explainability Page — View decision traces and explanations.
"""

import streamlit as st
import plotly.graph_objects as go


def render_explainability():
    """Render the explainability page."""
    st.markdown('<h2 class="gradient-text">💡 Explainability Dashboard</h2>', unsafe_allow_html=True)

    if "explanations" not in st.session_state:
        st.info("Run the pipeline first to see explanations.")
        return

    explanations = st.session_state.explanations
    candidates = st.session_state.ranked_candidates

    # Module contribution heatmap
    st.subheader("🎨 Module Contributions Heatmap")

    modules = ["Technical Alignment", "Semantic Relevance", "Evidence Strength",
               "Profile Authenticity", "Career Narrative", "Behavioral Intelligence", "Recruitability"]

    z_data = []
    y_labels = []
    for exp, rc in zip(explanations[:20], candidates[:20]):
        contribs = exp.module_contributions
        row = [contribs.get(m, 0) for m in modules]
        z_data.append(row)
        y_labels.append(f"#{rc.final_rank} {rc.candidate_name[:18]}")

    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=[m.split()[-1] for m in modules],
        y=y_labels,
        colorscale=[[0, '#1a1d29'], [0.5, '#667eea'], [1, '#f093fb']],
        text=[[f"{v:.2f}" for v in row] for row in z_data],
        texttemplate="%{text}",
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        height=max(400, len(z_data) * 30),
        margin=dict(l=150, r=20, t=40, b=60),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Individual explanations
    st.markdown("---")
    st.subheader("📋 Detailed Explanations")

    for exp, rc in zip(explanations[:10], candidates[:10]):
        with st.expander(f"#{rc.final_rank} — {rc.candidate_name} (Score: {rc.final_score:.4f})"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**💪 Strengths:**")
                for s in exp.strengths:
                    st.markdown(f"- ✅ {s}")
            with col2:
                st.markdown("**📈 Improvement Areas:**")
                for a in exp.improvement_areas:
                    st.markdown(f"- ⚠️ {a}")

            st.markdown("**📝 Reasoning:**")
            st.info(exp.reasoning)

            st.markdown("**🔗 Decision Trace:**")
            for trace in exp.decision_trace:
                st.code(trace)

            st.markdown(f"**Confidence:** {exp.confidence_summary}")
