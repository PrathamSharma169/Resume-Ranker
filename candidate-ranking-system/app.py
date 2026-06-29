"""
Streamlit Application — Adaptive Multi-Stage Candidate Intelligence Engine
Premium dark-themed dashboard with glassmorphism, animations, and interactive visualizations.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from src.utils.logger import setup_logger
from src.utils.file_utils import Config

# Page config MUST be first Streamlit command
st.set_page_config(
    page_title="Candidate Intelligence Engine",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Setup
setup_logger(level="INFO")
Config.load()

# Import pages
from ui.pages.dashboard import render_dashboard
from ui.pages.job_intelligence import render_job_intelligence
from ui.pages.ranking_dashboard import render_ranking_dashboard
from ui.pages.candidate_explorer import render_candidate_explorer
from ui.pages.explainability import render_explainability
from ui.pages.runtime_monitor import render_runtime_monitor
from ui.theme.styles import inject_custom_css


def main():
    # Inject custom CSS
    inject_custom_css()

    # Sidebar navigation
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h1 style="font-size: 1.8rem; background: linear-gradient(135deg, #667eea, #764ba2);
                -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                margin-bottom: 0.3rem;">🧠 CandidateIQ</h1>
            <p style="color: #8b8fa3; font-size: 0.8rem; margin: 0;">
                Adaptive Intelligence Engine</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        page = st.radio(
            "Navigation",
            [
                "🏠 Dashboard",
                "📋 Job Intelligence",
                "🏆 Rankings",
                "🔍 Candidate Explorer",
                "💡 Explainability",
                "⚡ Runtime Monitor",
            ],
            label_visibility="collapsed",
        )

        st.markdown("---")

        # Pipeline status
        if "pipeline_complete" in st.session_state and st.session_state.pipeline_complete:
            st.success("✅ Pipeline Complete")
            if "metrics" in st.session_state:
                m = st.session_state.metrics
                st.metric("Candidates Processed", f"{m.get('total_candidates', 0):,}")
                st.metric("Final Ranked", f"{m.get('candidates_ranked', 0)}")
                st.metric("Runtime", f"{m.get('runtime_seconds', 0):.1f}s")
        else:
            st.info("⏳ Pipeline not started")

    # Route to pages
    if page == "🏠 Dashboard":
        render_dashboard()
    elif page == "📋 Job Intelligence":
        render_job_intelligence()
    elif page == "🏆 Rankings":
        render_ranking_dashboard()
    elif page == "🔍 Candidate Explorer":
        render_candidate_explorer()
    elif page == "💡 Explainability":
        render_explainability()
    elif page == "⚡ Runtime Monitor":
        render_runtime_monitor()


if __name__ == "__main__":
    main()
