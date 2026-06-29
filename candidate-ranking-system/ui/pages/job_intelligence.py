"""
Job Intelligence Page — Visualize JD analysis results.
"""

import streamlit as st
import plotly.graph_objects as go
from ui.theme.styles import render_score_badge


def render_job_intelligence():
    """Render the Job Intelligence page."""
    st.markdown('<h2 class="gradient-text">📋 Job Description Intelligence</h2>', unsafe_allow_html=True)

    if "hiring_profile" not in st.session_state:
        st.info("Run the pipeline first to see JD analysis results.")
        return

    hp = st.session_state.hiring_profile

    # Role Metadata
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("🎯 Role Profile")
        if hp.role_metadata.title:
            st.write(f"**Title:** {hp.role_metadata.title}")
        st.write(f"**Work Mode:** {hp.role_metadata.work_mode}")
        st.write(f"**Experience:** {hp.experience_expectation.min_years:.0f}–{hp.experience_expectation.max_years:.0f} years")
        st.write(f"**Seniority:** {hp.experience_expectation.seniority_level}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("🧭 Hiring Philosophy")
        for phil in hp.hiring_philosophy[:5]:
            badge = render_score_badge(phil.strength, phil.dimension.replace("_", " ").title())
            st.markdown(badge, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Competencies
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔴 Required Competencies")
        for comp in hp.required_competencies[:15]:
            badge = render_score_badge(comp.importance, comp.name)
            st.markdown(f"- {badge}", unsafe_allow_html=True)

    with col2:
        st.subheader("🟡 Preferred Competencies")
        for comp in hp.preferred_competencies[:15]:
            badge = render_score_badge(comp.importance, comp.name)
            st.markdown(f"- {badge}", unsafe_allow_html=True)

    # Semantic Concepts
    st.markdown("---")
    st.subheader("🌐 Semantic Concepts")

    if hp.semantic_concepts:
        names = [c.primary_term for c in hp.semantic_concepts]
        values = [c.importance for c in hp.semantic_concepts]

        fig = go.Figure(data=go.Bar(
            x=values,
            y=names,
            orientation='h',
            marker=dict(
                color=values,
                colorscale=[[0, '#667eea'], [1, '#764ba2']],
            ),
        ))
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=30, b=0),
            height=300,
            title="Concept Importance",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Feature Importance
    st.markdown("---")
    st.subheader("⚖️ Dynamic Feature Importance")

    if hp.feature_importance:
        labels = [k.replace("_", " ").title() for k in hp.feature_importance.keys()]
        values = list(hp.feature_importance.values())

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.5,
            marker=dict(colors=[
                '#667eea', '#764ba2', '#f093fb',
                '#4ade80', '#fbbf24', '#60a5fa', '#f87171'
            ]),
            textinfo='label+percent',
        )])
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            height=400,
            title="Feature Importance Distribution",
        )
        st.plotly_chart(fig, use_container_width=True)
