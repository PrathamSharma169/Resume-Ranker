"""
Rankings Dashboard — Full ranking table with visualizations.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from ui.theme.styles import render_candidate_card


def render_ranking_dashboard():
    """Render the ranking dashboard."""
    st.markdown('<h2 class="gradient-text">🏆 Candidate Rankings</h2>', unsafe_allow_html=True)

    if "ranked_candidates" not in st.session_state:
        st.info("Run the pipeline first to see rankings.")
        return

    candidates = st.session_state.ranked_candidates

    # Score distribution
    st.subheader("📊 Score Distribution")
    scores = [rc.final_score for rc in candidates]
    fig = go.Figure(data=[go.Histogram(
        x=scores,
        nbinsx=20,
        marker=dict(color='#667eea', line=dict(color='#764ba2', width=1)),
    )])
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Score",
        yaxis_title="Count",
        height=300,
        margin=dict(l=40, r=20, t=20, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Ranking table
    st.markdown("---")
    st.subheader("📋 Full Rankings")

    # Build dataframe
    rows = []
    for rc in candidates:
        ucp = rc.unified_profile
        rows.append({
            "Rank": rc.final_rank,
            "Candidate": rc.candidate_name,
            "Title": rc.current_title,
            "Experience (yr)": rc.years_experience,
            "Score": round(rc.final_score, 4),
            "Technical": round(ucp.fused_technical, 3),
            "Semantic": round(ucp.fused_semantic, 3),
            "Evidence": round(ucp.fused_evidence, 3),
            "Authenticity": round(ucp.fused_authenticity, 3),
            "Narrative": round(ucp.fused_narrative, 3),
            "Behavioral": round(ucp.fused_behavioral, 3),
            "Recruitability": round(ucp.fused_recruitability, 3),
            "Confidence": round(rc.ranking_metadata.ranking_confidence, 3),
        })

    df = pd.DataFrame(rows)

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        min_score = st.slider("Min Score", 0.0, 1.0, 0.0, 0.01)
    with col2:
        search = st.text_input("🔍 Search by name or title")

    filtered_df = df[df["Score"] >= min_score]
    if search:
        search_lower = search.lower()
        filtered_df = filtered_df[
            filtered_df["Candidate"].str.lower().str.contains(search_lower, na=False) |
            filtered_df["Title"].str.lower().str.contains(search_lower, na=False)
        ]

    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=500,
        column_config={
            "Rank": st.column_config.NumberColumn(width="small"),
            "Score": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.4f"),
            "Technical": st.column_config.ProgressColumn(min_value=0, max_value=1),
            "Semantic": st.column_config.ProgressColumn(min_value=0, max_value=1),
            "Evidence": st.column_config.ProgressColumn(min_value=0, max_value=1),
            "Authenticity": st.column_config.ProgressColumn(min_value=0, max_value=1),
            "Narrative": st.column_config.ProgressColumn(min_value=0, max_value=1),
            "Behavioral": st.column_config.ProgressColumn(min_value=0, max_value=1),
            "Recruitability": st.column_config.ProgressColumn(min_value=0, max_value=1),
            "Confidence": st.column_config.ProgressColumn(min_value=0, max_value=1),
        }
    )

    # Radar chart comparison (top 5)
    st.markdown("---")
    st.subheader("🕸️ Top 5 — Multi-Dimensional Comparison")

    categories = ["Technical", "Semantic", "Evidence", "Authenticity", "Narrative", "Behavioral", "Recruitability"]

    fig = go.Figure()
    colors = ['#667eea', '#764ba2', '#f093fb', '#4ade80', '#fbbf24']

    for i, rc in enumerate(candidates[:5]):
        ucp = rc.unified_profile
        values = [
            ucp.fused_technical, ucp.fused_semantic, ucp.fused_evidence,
            ucp.fused_authenticity, ucp.fused_narrative,
            ucp.fused_behavioral, ucp.fused_recruitability,
        ]
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill='toself',
            name=f"#{rc.final_rank} {rc.candidate_name[:20]}",
            line=dict(color=colors[i]),
            opacity=0.7,
        ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1]),
            bgcolor="rgba(0,0,0,0)",
        ),
        height=500,
        margin=dict(l=60, r=60, t=40, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)
