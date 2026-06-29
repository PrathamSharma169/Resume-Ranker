"""
Pipeline Manager — Central Orchestrator.
Controls the complete execution flow with progressive filtering.
100K → 15K → 3K → 500 → Top 100
"""

import time
import csv
import json
import heapq
import traceback
from pathlib import Path
from typing import Optional
from models.hiring_profile import HiringProfile
from models.candidate import CandidateObject
from models.ranking import RankedCandidate
from models.explanation import CandidateExplanation
from src.jd_engine.jd_intelligence import JDIntelligenceEngine
from src.parser.candidate_parser import stream_candidates, parse_candidate
from src.engines.feature_engineering import FeatureEngineeringEngine
from src.engines.intelligence import (
    EvidenceEngine, AuthenticityEngine, NarrativeEngine,
    BehavioralEngine, RecruitabilityEngine,
)
from src.engines.ranking_engine import RankingEngine
from src.utils.logger import get_logger, setup_logger
from src.utils.timer import Timer, get_timings
from src.utils.file_utils import Config, ensure_dir, get_data_path, PROJECT_ROOT

logger = get_logger("pipeline")


class PipelineManager:
    """
    Central orchestrator for the Adaptive Multi-Stage Candidate Intelligence Engine.
    Manages the complete pipeline from JD parsing to submission generation.
    """

    def __init__(self, config: Config = None):
        self.config = config or Config.load()
        self.hiring_profile: Optional[HiringProfile] = None
        self.ranked_candidates: list[RankedCandidate] = []
        self.explanations: list[CandidateExplanation] = []

        # Pipeline configuration
        pipeline_cfg = self.config.get("pipeline", default={})
        filtering = pipeline_cfg.get("filtering", {})
        self.top_k = filtering.get("final_top_k", 100)
        self.stage1_cutoff = filtering.get("stage_1_cheap_features", 15000)

        # Metrics
        self.metrics = {
            "total_candidates": 0,
            "candidates_after_stage1": 0,
            "candidates_ranked": 0,
            "start_time": None,
            "end_time": None,
            "runtime_seconds": 0,
        }

        # State
        self._embedding_model = None
        self._is_running = False
        self._progress_callback = None

    def set_progress_callback(self, callback):
        """Set a callback for progress updates (for Streamlit)."""
        self._progress_callback = callback

    def _report_progress(self, stage: str, progress: float, message: str):
        """Report progress to callback if set."""
        if self._progress_callback:
            self._progress_callback(stage, progress, message)

    def _load_embedding_model(self):
        """Lazy-load the embedding model."""
        if self._embedding_model is None:
            try:
                model_name = self.config.get("models", "embedding.model_name", "all-MiniLM-L6-v2")
                logger.info(f"Loading embedding model: {model_name}")
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer(model_name)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}. Semantic features disabled.")
                self._embedding_model = None

    def run(
        self,
        jd_path: str = None,
        candidates_path: str = None,
        output_dir: str = None,
        use_embeddings: bool = True,
        output_csv: str = None,
    ) -> list[RankedCandidate]:
        """
        Run the complete pipeline.

        Args:
            jd_path: Path to job description DOCX
            candidates_path: Path to candidates JSONL/JSON
            output_dir: Output directory for results
            use_embeddings: Whether to use semantic embeddings
        """
        self._is_running = True
        self.metrics["start_time"] = time.time()

        try:
            # Resolve paths
            if jd_path is None:
                jd_path = str(get_data_path("job_description.docx"))
            if candidates_path is None:
                # Try JSONL first, then JSON
                jsonl_path = get_data_path("candidates.jsonl")
                json_path = get_data_path("sample_candidates.json")
                candidates_path = str(jsonl_path if jsonl_path.exists() else json_path)
            if output_dir is None:
                output_dir = str(PROJECT_ROOT / "data" / "output")

            ensure_dir(output_dir)

            # ================================================================
            # Stage 0: Load embedding model
            # ================================================================
            if use_embeddings:
                self._report_progress("init", 0.0, "Loading embedding model...")
                self._load_embedding_model()

            # ================================================================
            # Stage 1: JD Intelligence
            # ================================================================
            self._report_progress("jd_analysis", 0.05, "Analyzing Job Description...")
            logger.info("=" * 60)
            logger.info("STAGE 1: Job Description Intelligence")
            logger.info("=" * 60)

            jd_engine = JDIntelligenceEngine(embedding_model=self._embedding_model)
            self.hiring_profile = jd_engine.analyze(jd_path)

            logger.info(
                f"HiringProfile: {len(self.hiring_profile.required_competencies)} required, "
                f"{len(self.hiring_profile.preferred_competencies)} preferred competencies"
            )

            # ================================================================
            # Stage 2 & 3: Rolling Batch Evaluation
            # Evaluate 15K → take top 100 → add to next 15K → repeat
            # Every single candidate is fully evaluated.
            # ================================================================
            self._report_progress("processing", 0.10, "Processing candidates...")
            logger.info("=" * 60)
            logger.info("STAGE 2 & 3: Rolling Batch Evaluation (all candidates)")
            logger.info("=" * 60)

            feature_engine = FeatureEngineeringEngine(
                embedding_model=self._embedding_model
            )
            evidence_engine = EvidenceEngine()
            authenticity_engine = AuthenticityEngine()
            narrative_engine = NarrativeEngine()
            behavioral_engine = BehavioralEngine()
            recruitability_engine = RecruitabilityEngine()
            ranking_engine = RankingEngine(top_k=self.top_k)

            BATCH_SIZE = 15000
            current_batch = []          # raw CandidateObject list for current batch
            carry_over = []             # top 100 survivors from previous batch: list of (score, CandidateObject)
            total_count = 0
            batch_num = 0

            for candidate in stream_candidates(candidates_path):
                total_count += 1
                current_batch.append(candidate)

                if len(current_batch) >= BATCH_SIZE:
                    batch_num += 1
                    # Merge carry-over winners into this batch
                    for _, carry_candidate in carry_over:
                        current_batch.append(carry_candidate)

                    logger.info(
                        f"Batch {batch_num}: evaluating {len(current_batch)} candidates "
                        f"({BATCH_SIZE} new + {len(carry_over)} carry-over)"
                    )

                    # Fully evaluate every candidate in this batch
                    carry_over = self._evaluate_batch_and_get_top(
                        current_batch, feature_engine, evidence_engine,
                        authenticity_engine, narrative_engine, behavioral_engine,
                        recruitability_engine, ranking_engine, use_embeddings,
                    )

                    logger.info(
                        f"Batch {batch_num} done. Top {len(carry_over)} survivors carry forward."
                    )

                    current_batch = []  # Free memory

                    progress = min(0.80, 0.10 + (total_count / 100000) * 0.70)
                    self._report_progress(
                        "processing", progress,
                        f"Processed {total_count:,} candidates (batch {batch_num})..."
                    )

            # Process the last partial batch
            if current_batch:
                batch_num += 1
                for _, carry_candidate in carry_over:
                    current_batch.append(carry_candidate)

                logger.info(
                    f"Batch {batch_num} (final): evaluating {len(current_batch)} candidates "
                    f"({len(current_batch) - len(carry_over)} new + {len(carry_over)} carry-over)"
                )

                carry_over = self._evaluate_batch_and_get_top(
                    current_batch, feature_engine, evidence_engine,
                    authenticity_engine, narrative_engine, behavioral_engine,
                    recruitability_engine, ranking_engine, use_embeddings,
                )

            self.metrics["total_candidates"] = total_count
            self.metrics["candidates_after_stage1"] = total_count  # All evaluated
            self.metrics["batches_processed"] = batch_num
            logger.info(
                f"All batches complete: {total_count:,} candidates processed "
                f"across {batch_num} batches"
            )

            # ================================================================
            # Stage 4: Finalize Ranking & Generate Explanations
            # ================================================================
            self._report_progress("ranking", 0.85, "Finalizing rankings...")
            logger.info("=" * 60)
            logger.info("STAGE 4: Ranking & Explanation")
            logger.info("=" * 60)

            self.ranked_candidates = ranking_engine.get_ranked_results(self.hiring_profile)
            self.explanations = ranking_engine.generate_explanations(
                self.ranked_candidates, self.hiring_profile
            )

            self.metrics["candidates_ranked"] = len(self.ranked_candidates)
            logger.info(f"Final ranking: {len(self.ranked_candidates)} candidates")

            # ================================================================
            # Stage 5: Generate Submission
            # ================================================================
            self._report_progress("submission", 0.90, "Generating submission...")
            logger.info("=" * 60)
            logger.info("STAGE 5: Submission Generation")
            logger.info("=" * 60)

            self._generate_submission(output_dir, output_csv)
            self._generate_reports(output_dir)

            self.metrics["end_time"] = time.time()
            self.metrics["runtime_seconds"] = self.metrics["end_time"] - self.metrics["start_time"]

            self._report_progress("complete", 1.0, "Pipeline complete!")
            logger.info(f"Pipeline complete in {self.metrics['runtime_seconds']:.1f}s")

            return self.ranked_candidates

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            logger.error(traceback.format_exc())
            raise
        finally:
            self._is_running = False

    def _evaluate_batch_and_get_top(
        self,
        batch: list,
        feature_engine,
        evidence_engine,
        authenticity_engine,
        narrative_engine,
        behavioral_engine,
        recruitability_engine,
        ranking_engine,
        use_embeddings: bool,
    ) -> list:
        """
        Fully evaluate every candidate in the batch through ALL intelligence
        engines, push them into the global ranking heap, and return the
        current top-100 as (score, CandidateObject) pairs to carry forward.
        """
        for candidate in batch:
            # 1. Feature extraction
            features = feature_engine.extract_features(candidate, self.hiring_profile)

            # 2. Semantic features (if embeddings enabled)
            if use_embeddings and features.semantic_features.overall_semantic_score == 0:
                features.semantic_features = feature_engine._extract_semantic_features(
                    candidate, self.hiring_profile
                )

            # 3. Full intelligence analysis
            evidence = evidence_engine.analyze(candidate, self.hiring_profile, features)
            authenticity = authenticity_engine.analyze(candidate, evidence, features)
            narrative = narrative_engine.analyze(candidate, self.hiring_profile, features)
            behavioral = behavioral_engine.analyze(candidate, features)
            recruitability = recruitability_engine.analyze(
                candidate, self.hiring_profile, behavioral, features
            )

            # 4. Build unified profile
            unified = ranking_engine.build_unified_profile(
                candidate, features, evidence, authenticity,
                narrative, behavioral, recruitability, self.hiring_profile
            )

            # 5. Push into global top-K heap inside ranking_engine
            ranking_engine.process_candidate(candidate, unified, self.hiring_profile)

        # Extract current top-100 from the ranking heap to carry forward
        # The heap stores (score, candidate_id, ucp, candidate)
        return [(score, candidate) for score, cid, ucp, candidate in ranking_engine._heap]

    def _generate_submission(self, output_dir: str, output_csv: str = None):
        """Generate the submission CSV file."""
        submissions_dir = ensure_dir(Path(output_dir) / "submissions")
        csv_path = Path(output_csv) if output_csv else submissions_dir / "submission.csv"

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["candidate_id", "rank", "score", "reasoning"])
            for rc in self.ranked_candidates:
                # Find explanation for this candidate
                reasoning = ""
                for exp in self.explanations:
                    if exp.candidate_id == rc.candidate_id:
                        reasoning = exp.reasoning
                        break
                writer.writerow([
                    rc.candidate_id,
                    rc.final_rank,
                    f"{rc.final_score:.6f}",
                    reasoning,
                ])

        logger.info(f"Submission written: {csv_path}")
        return str(csv_path)

    def _generate_reports(self, output_dir: str):
        """Generate runtime and explanation reports."""
        reports_dir = ensure_dir(Path(output_dir) / "reports")

        # Runtime report
        runtime_report = {
            "metrics": self.metrics,
            "timings": get_timings(),
            "pipeline_config": {
                "top_k": self.top_k,
                "stage1_cutoff": self.stage1_cutoff,
            }
        }
        with open(reports_dir / "runtime_report.json", "w", encoding="utf-8") as f:
            json.dump(runtime_report, f, indent=2, default=str)

        # Explanations report
        explanations_data = []
        for exp in self.explanations:
            explanations_data.append({
                "candidate_id": exp.candidate_id,
                "rank": exp.rank,
                "score": exp.score,
                "strengths": exp.strengths,
                "improvement_areas": exp.improvement_areas,
                "decision_trace": exp.decision_trace,
                "reasoning": exp.reasoning,
                "confidence": exp.confidence_summary,
                "module_contributions": exp.module_contributions,
            })
        with open(reports_dir / "explanations.json", "w", encoding="utf-8") as f:
            json.dump(explanations_data, f, indent=2)

        # Ranking metadata
        ranking_data = []
        for rc in self.ranked_candidates:
            ranking_data.append({
                "candidate_id": rc.candidate_id,
                "rank": rc.final_rank,
                "score": rc.final_score,
                "name": rc.candidate_name,
                "title": rc.current_title,
                "experience_years": rc.years_experience,
                "confidence": rc.ranking_metadata.ranking_confidence,
                "strengths": rc.ranking_metadata.dominant_strengths,
            })
        with open(reports_dir / "ranking_metadata.json", "w", encoding="utf-8") as f:
            json.dump(ranking_data, f, indent=2)

        logger.info(f"Reports written to {reports_dir}")

    @property
    def is_running(self) -> bool:
        return self._is_running
