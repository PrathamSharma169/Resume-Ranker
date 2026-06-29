"""
Runtime Monitor — Performance metrics and pipeline analytics.
"""

import streamlit as st
import json
from pathlib import Path
from ui.theme.styles import render_metric_card


def render_runtime_monitor():
    """Render the runtime monitor page."""
    st.markdown('<h2 class="gradient-text">⚡ Runtime Monitor</h2>', unsafe_allow_html=True)

    if "metrics" not in st.session_state:
        st.info("Run the pipeline first to see runtime metrics.")
        return

    metrics = st.session_state.metrics

    # Key metrics
    cols = st.columns(4)
    metric_items = [
        ("Total Candidates", f"{metrics.get('total_candidates', 0):,}", "👥"),
        ("Runtime", f"{metrics.get('runtime_seconds', 0):.1f}s", "⏱️"),
        ("Throughput", f"{metrics.get('total_candidates', 0) / max(0.1, metrics.get('runtime_seconds', 1)):.0f}/s", "🚀"),
        ("Final Ranked", f"{metrics.get('candidates_ranked', 0)}", "🏆"),
    ]

    for col, (label, value, icon) in zip(cols, metric_items):
        with col:
            render_metric_card(label, value, icon)

    st.markdown("<br>", unsafe_allow_html=True)

    # Pipeline stages
    st.subheader("🔄 Pipeline Stages")

    stages = [
        ("JD Intelligence", "Parsed job description and built HiringProfile", "complete"),
        ("Candidate Streaming", f"Streamed {metrics.get('total_candidates', 0):,} candidates", "complete"),
        ("Feature Engineering", f"Extracted features, filtered to {metrics.get('candidates_after_stage1', 0):,}", "complete"),
        ("Intelligence Engines", "Evidence, Authenticity, Narrative, Behavioral, Recruitability", "complete"),
        ("Feature Fusion", "Merged all intelligence dimensions", "complete"),
        ("Ensemble Ranking", f"Top-{metrics.get('candidates_ranked', 0)} heap ranking", "complete"),
        ("Explainability", "Generated deterministic explanations", "complete"),
        ("Submission", "Produced submission CSV + reports", "complete"),
    ]

    for name, desc, status in stages:
        icon = "✅" if status == "complete" else "⏳"
        css = "complete" if status == "complete" else "active"
        st.markdown(f"""
        <div class="pipeline-stage {css}">
            <span>{icon}</span>
            <div>
                <strong>{name}</strong>
                <br><span style="color: #8b8fa3; font-size: 0.85rem;">{desc}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Reports download
    st.markdown("---")
    st.subheader("📥 Download Reports")

    from src.utils.file_utils import PROJECT_ROOT
    reports_dir = PROJECT_ROOT / "data" / "output" / "reports"

    col1, col2, col3 = st.columns(3)

    report_files = [
        ("runtime_report.json", "Runtime Report", col1),
        ("explanations.json", "Explanations", col2),
        ("ranking_metadata.json", "Ranking Metadata", col3),
    ]

    for filename, label, col in report_files:
        filepath = reports_dir / filename
        if filepath.exists():
            with col:
                with open(filepath, "r") as f:
                    data = f.read()
                st.download_button(
                    f"📄 {label}",
                    data,
                    file_name=filename,
                    mime="application/json",
                    use_container_width=True,
                )
