"""
Candidate Explorer — Deep-dive into individual candidates.
"""

import streamlit as st
import plotly.graph_objects as go
from ui.theme.styles import render_score_badge


def render_candidate_explorer():
    """Render the candidate explorer page."""
    st.markdown('<h2 class="gradient-text">🔍 Candidate Explorer</h2>', unsafe_allow_html=True)

    if "ranked_candidates" not in st.session_state:
        st.info("Run the pipeline first to explore candidates.")
        return

    candidates = st.session_state.ranked_candidates
    explanations = st.session_state.get("explanations", [])

    # Candidate selector
    options = [
        f"#{rc.final_rank} — {rc.candidate_name} ({rc.current_title})"
        for rc in candidates
    ]
    selected = st.selectbox("Select Candidate", options)
    idx = options.index(selected)
    rc = candidates[idx]
    ucp = rc.unified_profile
    exp = explanations[idx] if idx < len(explanations) else None

    # Profile card
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"""
        <div class="glass-card">
            <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
                <div class="rank-badge" style="font-size: 1.5rem; width: 60px; height: 60px;">
                    {rc.final_rank}
                </div>
                <div>
                    <h3 style="margin: 0; color: var(--text-primary);">{rc.candidate_name}</h3>
                    <p style="margin: 0; color: var(--text-secondary);">{rc.current_title}</p>
                    <p style="margin: 0; color: var(--text-secondary);">{rc.years_experience:.0f} years experience</p>
                </div>
            </div>
            <div>
                {render_score_badge(rc.final_score, "Overall Score")}
                &nbsp;
                {render_score_badge(rc.ranking_metadata.ranking_confidence, "Confidence")}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("⚡ Quick Stats")
        fv = ucp.feature_vector
        st.write(f"**Skills:** {fv.technical_features.total_skills}")
        st.write(f"**Relevant Skills:** {fv.technical_features.relevant_skills_count}")
        st.write(f"**Skill Coverage:** {fv.technical_features.skill_coverage:.0%}")
        st.write(f"**Companies:** {fv.career_features.total_companies}")
        st.write(f"**Assessment Avg:** {fv.technical_features.assessment_score_avg:.0%}")
        st.markdown('</div>', unsafe_allow_html=True)

    # Dimension scores radar chart
    st.markdown("---")
    st.subheader("🕸️ Multi-Dimensional Profile")

    dimensions = {
        "Technical": ucp.fused_technical,
        "Semantic": ucp.fused_semantic,
        "Evidence": ucp.fused_evidence,
        "Authenticity": ucp.fused_authenticity,
        "Narrative": ucp.fused_narrative,
        "Behavioral": ucp.fused_behavioral,
        "Recruitability": ucp.fused_recruitability,
    }

    fig = go.Figure()
    cats = list(dimensions.keys())
    vals = list(dimensions.values())

    fig.add_trace(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=cats + [cats[0]],
        fill='toself',
        name=rc.candidate_name,
        fillcolor='rgba(102, 126, 234, 0.2)',
        line=dict(color='#667eea', width=2),
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1]),
            bgcolor="rgba(0,0,0,0)",
        ),
        height=400,
        margin=dict(l=60, r=60, t=40, b=40),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Dimension scores bar chart
    fig2 = go.Figure(data=[go.Bar(
        x=cats,
        y=vals,
        marker=dict(
            color=vals,
            colorscale=[[0, '#f87171'], [0.5, '#fbbf24'], [1, '#4ade80']],
        ),
        text=[f"{v:.0%}" for v in vals],
        textposition='auto',
    )])
    fig2.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(range=[0, 1]),
        height=300,
        margin=dict(l=40, r=20, t=20, b=40),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Explanation
    if exp:
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("💪 Strengths")
            for s in exp.strengths:
                st.markdown(f"✅ {s}")

        with col2:
            st.subheader("📈 Improvement Areas")
            for a in exp.improvement_areas:
                st.markdown(f"⚠️ {a}")

        st.markdown("---")
        st.subheader("🔗 Decision Trace")
        for trace in exp.decision_trace:
            st.code(trace)

        st.subheader("📝 Reasoning")
        st.markdown(f"> {exp.reasoning}")
