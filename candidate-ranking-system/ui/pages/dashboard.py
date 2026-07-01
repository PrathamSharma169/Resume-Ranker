"""
Dashboard Page — Main overview with pipeline execution.
"""

import streamlit as st
import time
from pathlib import Path
from ui.theme.styles import render_metric_card, render_candidate_card


def render_dashboard():
    """Render the main dashboard page."""
    st.markdown("""
    <h1 class="gradient-text" style="font-size: 2.2rem; margin-bottom: 0.5rem;">
        Candidate Intelligence Engine
    </h1>
    <p style="color: #8b8fa3; font-size: 1rem; margin-bottom: 2rem;">
        Adaptive Multi-Stage Ranking Pipeline — Evidence-Driven, Explainable, Deterministic
    </p>
    """, unsafe_allow_html=True)

    from src.utils.file_utils import get_data_path, PROJECT_ROOT

    # --- Resolve default paths ---
    default_jd = get_data_path("job_description.docx")
    # Prefer full candidates.jsonl over the 50-record sample
    default_candidates = get_data_path("candidates.jsonl")
    if not default_candidates.exists():
        default_candidates = get_data_path("sample_candidates.json")

    # --- Pipeline execution controls ---
    st.markdown("### 📂 Data Sources")

    col_left, col_right = st.columns(2)

    with col_left:
        jd_source = st.radio(
            "Job Description source",
            ["Use local file", "Upload file"],
            horizontal=True,
            key="jd_source_radio",
        )
        if jd_source == "Use local file":
            jd_path_input = st.text_input(
                "📄 JD file path (.docx)",
                value="",
                placeholder="e.g. C:/Users/lenovo/Documents/Resume Ranker/candidate-ranking-system/job_description.docx",
                key="jd_path_input",
            )
        else:
            jd_file = st.file_uploader(
                "📄 Upload Job Description (.docx)",
                type=["docx"],
                key="jd_upload",
            )
            jd_path_input = None

    with col_right:
        cand_source = st.radio(
            "Candidates source",
            ["Use local file", "Upload file"],
            horizontal=True,
            key="cand_source_radio",
        )
        if cand_source == "Use local file":
            candidates_path_input = st.text_input(
                "👥 Candidates file path (.jsonl / .json)",
                value="",
                placeholder="e.g. C:/Users/lenovo/Documents/Resume Ranker/candidate-ranking-system/candidates.jsonl",
                key="cand_path_input",
            )
        else:
            candidates_file = st.file_uploader(
                "👥 Candidates (.jsonl, .json)",
                type=["jsonl", "json"],
                key="candidates_upload",
            )
            candidates_path_input = None

    # Options
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        use_embeddings = st.checkbox("🧠 Semantic Embeddings", value=True)
    with col_opt2:
        top_k = st.number_input("🏆 Top-K to rank", min_value=10, max_value=1000, value=100, step=10)

    # --- Resolve final paths ---
    # JD
    if jd_source == "Use local file":
        final_jd_path = jd_path_input
    else:
        if jd_file is not None:
            from src.utils.file_utils import ensure_dir
            upload_dir = ensure_dir(PROJECT_ROOT / "data" / "uploads")
            final_jd_path = str(upload_dir / jd_file.name)
            with open(final_jd_path, "wb") as f:
                f.write(jd_file.getbuffer())
        else:
            final_jd_path = str(default_jd)

    # Candidates
    if cand_source == "Use local file":
        final_candidates_path = candidates_path_input
    else:
        if candidates_file is not None:
            from src.utils.file_utils import ensure_dir
            upload_dir = ensure_dir(PROJECT_ROOT / "data" / "uploads")
            final_candidates_path = str(upload_dir / candidates_file.name)
            with open(final_candidates_path, "wb") as f:
                f.write(candidates_file.getbuffer())
        else:
            final_candidates_path = str(default_candidates)

    # Validate paths
    jd_exists = Path(final_jd_path).exists() if final_jd_path else False
    cand_exists = Path(final_candidates_path).exists() if final_candidates_path else False

    if final_jd_path and not jd_exists:
        st.warning(f"⚠️ JD file not found: `{final_jd_path}`")
    if final_candidates_path and not cand_exists:
        st.warning(f"⚠️ Candidates file not found: `{final_candidates_path}`")

    # Show file info
    if cand_exists:
        cand_size = Path(final_candidates_path).stat().st_size
        cand_size_mb = cand_size / (1024 * 1024)
        st.info(f"📊 Candidates file: **{Path(final_candidates_path).name}** ({cand_size_mb:.1f} MB)")

    # Run pipeline button
    can_run = jd_exists and cand_exists
    if st.button(
        "🚀 Run Intelligence Pipeline",
        type="primary",
        use_container_width=True,
        disabled=not can_run,
    ):
        _run_pipeline(final_jd_path, final_candidates_path, use_embeddings, top_k)

    # Show results if pipeline has run
    if "pipeline_complete" in st.session_state and st.session_state.pipeline_complete:
        _render_results()


def _run_pipeline(jd_path: str, candidates_path: str, use_embeddings: bool, top_k: int):
    """Execute the ranking pipeline."""
    from src.pipeline.pipeline_manager import PipelineManager

    # Progress display
    progress_bar = st.progress(0, text="Initializing pipeline...")
    status_text = st.empty()

    def progress_callback(stage, progress, message):
        progress_bar.progress(min(progress, 1.0), text=message)
        status_text.markdown(f"**{message}**")

    # Run pipeline
    try:
        pipeline = PipelineManager()
        pipeline.top_k = top_k
        pipeline.set_progress_callback(progress_callback)

        results = pipeline.run(
            jd_path=jd_path,
            candidates_path=candidates_path,
            use_embeddings=use_embeddings,
        )

        # Store results in session state
        st.session_state.pipeline_complete = True
        st.session_state.ranked_candidates = results
        st.session_state.explanations = pipeline.explanations
        st.session_state.hiring_profile = pipeline.hiring_profile
        st.session_state.metrics = pipeline.metrics

        progress_bar.progress(1.0, text="✅ Pipeline complete!")
        st.balloons()
        st.rerun()

    except Exception as e:
        st.error(f"Pipeline failed: {e}")
        import traceback
        st.code(traceback.format_exc())


def _render_results():
    """Render pipeline results."""
    metrics = st.session_state.metrics
    candidates = st.session_state.ranked_candidates

    # Key metrics
    st.markdown('<div class="section-header">📊 Pipeline Results</div>', unsafe_allow_html=True)

    cols = st.columns(5)
    metric_data = [
        ("Total Candidates", f"{metrics.get('total_candidates', 0):,}", "👥"),
        ("After Stage 1", f"{metrics.get('candidates_after_stage1', 0):,}", "🔍"),
        ("Final Ranked", f"{metrics.get('candidates_ranked', 0)}", "🏆"),
        ("Runtime", f"{metrics.get('runtime_seconds', 0):.1f}s", "⏱️"),
        ("Top Score", f"{candidates[0].final_score:.4f}" if candidates else "N/A", "⭐"),
    ]

    for col, (label, value, icon) in zip(cols, metric_data):
        with col:
            render_metric_card(label, value, icon)

    st.markdown("<br>", unsafe_allow_html=True)

    # Top candidates
    n_ranked = len(candidates)
    st.markdown(f'<div class="section-header">🏆 Top {min(10, n_ranked)} Candidates (of {n_ranked} ranked)</div>', unsafe_allow_html=True)

    for rc in candidates[:10]:
        render_candidate_card(
            rank=rc.final_rank,
            name=rc.candidate_name,
            title=rc.current_title,
            score=rc.final_score,
            exp=rc.years_experience,
        )

    # Download submission
    st.markdown("<br>", unsafe_allow_html=True)
    from src.utils.file_utils import PROJECT_ROOT
    csv_path = PROJECT_ROOT / "data" / "output" / "submissions" / "submission.csv"
    if csv_path.exists():
        with open(csv_path, "r") as f:
            csv_data = f.read()
        n_lines = csv_data.count("\n") - 1  # minus header
        st.success(f"✅ Submission CSV contains **{n_lines}** ranked candidates")
        st.download_button(
            f"📥 Download Submission CSV ({n_lines} candidates)",
            csv_data,
            file_name="submission.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True,
        )
