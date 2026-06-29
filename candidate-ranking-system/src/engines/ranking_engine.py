"""
Ranking Engine — Adaptive Ensemble Ranking with Top-K Heap Management.
Combines all intelligence profiles into a final ranking using context-aware reasoning.
"""

import heapq
import numpy as np
from typing import Optional
from models.candidate import CandidateObject
from models.hiring_profile import HiringProfile
from models.feature_vector import FeatureVector
from models.evidence import EvidenceProfile
from models.authenticity import AuthenticityProfile
from models.narrative import NarrativeProfile
from models.behavior import BehavioralProfile
from models.recruitability import RecruitabilityProfile
from models.ranking import UnifiedCandidateProfile, RankedCandidate, RankingMetadata
from models.explanation import CandidateExplanation
from src.utils.logger import get_logger
from src.utils.math_utils import weighted_average, clip_score
from src.utils.timer import Timer

logger = get_logger("ranking_engine")


class RankingEngine:
    """
    Adaptive Ensemble Ranking Engine.
    Performs context-aware multi-dimensional ranking using a streaming Top-K heap.
    """

    def __init__(self, top_k: int = 100):
        self.top_k = top_k
        # Min-heap: stores (score, candidate_id, unified_profile, candidate)
        self._heap: list[tuple[float, str, UnifiedCandidateProfile, CandidateObject]] = []
        self._candidates_processed = 0
        # Deduplication: track the best score seen for each candidate_id
        self._best_scores: dict[str, float] = {}

    def build_unified_profile(
        self,
        candidate: CandidateObject,
        feature_vector: FeatureVector,
        evidence_profile: EvidenceProfile,
        authenticity_profile: AuthenticityProfile,
        narrative_profile: NarrativeProfile,
        behavioral_profile: BehavioralProfile,
        recruitability_profile: RecruitabilityProfile,
        hiring_profile: HiringProfile,
    ) -> UnifiedCandidateProfile:
        """
        Build a Unified Candidate Profile by fusing all intelligence modules.
        Dynamic Feature Fusion Engine.
        """
        ucp = UnifiedCandidateProfile(
            candidate_id=candidate.candidate_id,
            feature_vector=feature_vector,
            evidence_profile=evidence_profile,
            authenticity_profile=authenticity_profile,
            narrative_profile=narrative_profile,
            behavioral_profile=behavioral_profile,
            recruitability_profile=recruitability_profile,
        )

        # Fuse scores with dynamic weighting from HiringProfile
        importance = hiring_profile.feature_importance
        if not importance:
            importance = {
                "technical_alignment": 0.25,
                "semantic_relevance": 0.20,
                "evidence_strength": 0.20,
                "authenticity": 0.10,
                "career_narrative": 0.10,
                "behavioral": 0.08,
                "recruitability": 0.07,
            }

        # Compute fused dimension scores
        ucp.fused_technical = clip_score(
            feature_vector.technical_features.skill_coverage * 0.35 +
            feature_vector.technical_features.relevant_skills_ratio * 0.25 +
            feature_vector.technical_features.avg_proficiency * 0.15 +
            feature_vector.technical_features.assessment_score_avg * 0.15 +
            feature_vector.profile_features.title_relevance * 0.10
        )

        ucp.fused_semantic = clip_score(
            feature_vector.semantic_features.overall_semantic_score
        )

        ucp.fused_evidence = clip_score(
            evidence_profile.overall_evidence_score * 0.5 +
            evidence_profile.evidence_coverage * 0.3 +
            evidence_profile.evidence_density * 0.2 * 0.25  # density scaled down
        )

        ucp.fused_authenticity = clip_score(
            authenticity_profile.overall_authenticity
        )

        ucp.fused_narrative = clip_score(
            narrative_profile.narrative_strength
        )

        ucp.fused_behavioral = clip_score(
            behavioral_profile.overall_behavioral_score
        )

        ucp.fused_recruitability = clip_score(
            recruitability_profile.recruitability_score
        )

        return ucp

    def compute_final_score(
        self,
        ucp: UnifiedCandidateProfile,
        hiring_profile: HiringProfile,
    ) -> float:
        """
        Compute the final ranking score using adaptive ensemble reasoning.
        This is NOT a simple weighted average — it considers feature interactions.
        """
        importance = hiring_profile.feature_importance
        if not importance:
            importance = {
                "technical_alignment": 0.25,
                "semantic_relevance": 0.20,
                "evidence_strength": 0.20,
                "authenticity": 0.10,
                "career_narrative": 0.10,
                "behavioral": 0.08,
                "recruitability": 0.07,
            }

        # Base weighted score
        base_score = weighted_average(
            [ucp.fused_technical, ucp.fused_semantic, ucp.fused_evidence,
             ucp.fused_authenticity, ucp.fused_narrative,
             ucp.fused_behavioral, ucp.fused_recruitability],
            [importance.get("technical_alignment", 0.25),
             importance.get("semantic_relevance", 0.20),
             importance.get("evidence_strength", 0.20),
             importance.get("authenticity", 0.10),
             importance.get("career_narrative", 0.10),
             importance.get("behavioral", 0.08),
             importance.get("recruitability", 0.07)]
        )

        # Feature interactions (bonuses for consistent profiles)
        # High tech + high evidence = bonus (well-supported claims)
        if ucp.fused_technical > 0.6 and ucp.fused_evidence > 0.6:
            base_score += 0.03

        # High semantic + high narrative = bonus (career aligned with role)
        if ucp.fused_semantic > 0.5 and ucp.fused_narrative > 0.5:
            base_score += 0.02

        # High authenticity + high evidence = strong trust signal
        if ucp.fused_authenticity > 0.7 and ucp.fused_evidence > 0.5:
            base_score += 0.02

        # Penalty for low authenticity (suspicious profile)
        if ucp.fused_authenticity < 0.3:
            base_score -= 0.05

        return clip_score(base_score)

    def process_candidate(
        self,
        candidate: CandidateObject,
        ucp: UnifiedCandidateProfile,
        hiring_profile: HiringProfile,
    ) -> None:
        """
        Process a single candidate through the ranking engine.
        Uses a min-heap to maintain Top-K candidates.
        Deduplicates by candidate_id — only keeps the best score per candidate.
        """
        self._candidates_processed += 1
        score = self.compute_final_score(ucp, hiring_profile)
        cid = candidate.candidate_id

        # Deduplication: if we've seen this candidate before, only keep
        # the entry with the higher score.
        if cid in self._best_scores:
            if score <= self._best_scores[cid]:
                # Already have a better or equal score for this candidate — skip
                return
            # New score is better — remove old entry from heap, then re-insert
            self._heap = [entry for entry in self._heap if entry[1] != cid]
            heapq.heapify(self._heap)

        # Update best known score
        self._best_scores[cid] = score

        if len(self._heap) < self.top_k:
            heapq.heappush(self._heap, (score, cid, ucp, candidate))
        elif score > self._heap[0][0]:
            heapq.heapreplace(self._heap, (score, cid, ucp, candidate))

    def get_ranked_results(self, hiring_profile: HiringProfile) -> list[RankedCandidate]:
        """
        Get final ranked results sorted by score (highest first).
        Generates ranking metadata and explanations.
        """
        # Sort heap by score descending, then candidate_id ascending for tie-breaking
        sorted_candidates = sorted(self._heap, key=lambda x: (-x[0], x[1]))

        results = []
        for rank, (score, cid, ucp, candidate) in enumerate(sorted_candidates, 1):
            # Build ranking metadata
            metadata = self._build_ranking_metadata(ucp, score)

            ranked = RankedCandidate(
                candidate_id=cid,
                final_rank=rank,
                final_score=round(score, 6),
                unified_profile=ucp,
                ranking_metadata=metadata,
                candidate_name=candidate.profile.anonymized_name,
                current_title=candidate.profile.current_title,
                years_experience=candidate.profile.years_of_experience,
            )
            results.append(ranked)

        logger.info(
            f"Ranking complete: {len(results)} candidates ranked "
            f"from {self._candidates_processed} processed"
        )
        return results

    def generate_explanations(
        self,
        ranked_candidates: list[RankedCandidate],
        hiring_profile: HiringProfile,
    ) -> list[CandidateExplanation]:
        """Generate deterministic explanations for all ranked candidates."""
        explanations = []

        for rc in ranked_candidates:
            explanation = self._build_explanation(rc, hiring_profile)
            explanations.append(explanation)

        return explanations

    def _build_ranking_metadata(self, ucp: UnifiedCandidateProfile, score: float) -> RankingMetadata:
        """Build ranking metadata from unified profile."""
        # Identify dominant strengths
        dimensions = {
            "Technical Alignment": ucp.fused_technical,
            "Semantic Relevance": ucp.fused_semantic,
            "Evidence Strength": ucp.fused_evidence,
            "Profile Authenticity": ucp.fused_authenticity,
            "Career Narrative": ucp.fused_narrative,
            "Behavioral Intelligence": ucp.fused_behavioral,
            "Recruitability": ucp.fused_recruitability,
        }

        sorted_dims = sorted(dimensions.items(), key=lambda x: x[1], reverse=True)
        strengths = [name for name, val in sorted_dims if val > 0.5][:4]
        supporting = [name for name, val in sorted_dims if val > 0.4][:5]

        # Confidence estimation
        values = list(dimensions.values())
        consistency = 1.0 - np.std(values) if values else 0.5
        completeness = sum(1 for v in values if v > 0.1) / len(values) if values else 0
        confidence = clip_score(consistency * 0.5 + completeness * 0.3 + score * 0.2)

        return RankingMetadata(
            dominant_strengths=strengths,
            supporting_modules=supporting,
            feature_contributions=dimensions,
            ranking_confidence=round(confidence, 4),
        )

    def _build_explanation(
        self,
        rc: RankedCandidate,
        hiring_profile: HiringProfile,
    ) -> CandidateExplanation:
        """Build a deterministic explanation for a ranked candidate."""
        ucp = rc.unified_profile
        meta = rc.ranking_metadata

        explanation = CandidateExplanation(
            candidate_id=rc.candidate_id,
            rank=rc.final_rank,
            score=rc.final_score,
        )

        # Strengths
        if ucp.fused_technical > 0.5:
            cov = ucp.feature_vector.technical_features.skill_coverage
            explanation.strengths.append(
                f"Strong technical alignment ({cov:.0%} skill coverage)"
            )
        if ucp.fused_evidence > 0.5:
            explanation.strengths.append("Well-supported claims with multi-source evidence")
        if ucp.fused_narrative > 0.5:
            direction = ucp.narrative_profile.career_direction
            explanation.strengths.append(f"Strong career narrative ({direction} trajectory)")
        if ucp.fused_semantic > 0.4:
            sim = ucp.feature_vector.semantic_features.overall_semantic_score
            explanation.strengths.append(f"Good semantic alignment with role ({sim:.0%})")
        if ucp.fused_authenticity > 0.6:
            explanation.strengths.append("High profile authenticity and consistency")
        if ucp.fused_behavioral > 0.5:
            explanation.strengths.append("Strong platform engagement and hiring readiness")
        if ucp.fused_recruitability > 0.5:
            explanation.strengths.append("High recruitability and availability")

        # Improvement areas
        if ucp.fused_technical < 0.3:
            explanation.improvement_areas.append("Limited skill coverage for required competencies")
        if ucp.fused_evidence < 0.3:
            explanation.improvement_areas.append("Weak evidence supporting technical claims")
        if ucp.fused_authenticity < 0.4:
            explanation.improvement_areas.append("Profile consistency could be improved")
        if ucp.fused_behavioral < 0.3:
            explanation.improvement_areas.append("Low platform engagement signals")

        # Decision trace
        for name, val in sorted(
            meta.feature_contributions.items(), key=lambda x: x[1], reverse=True
        ):
            explanation.decision_trace.append(f"{name}: {val:.3f}")

        # Module contributions
        explanation.module_contributions = meta.feature_contributions

        # Build human-readable reasoning for CSV
        explanation.reasoning = self._build_reasoning_text(explanation, rc)

        # Confidence
        explanation.confidence_summary = (
            f"Ranking confidence: {meta.ranking_confidence:.0%}"
        )

        return explanation

    def _build_reasoning_text(self, exp: CandidateExplanation, rc: RankedCandidate) -> str:
        """Build concise human-readable reasoning for the submission CSV."""
        parts = []

        if exp.strengths:
            parts.append(". ".join(exp.strengths[:3]))

        parts.append(
            f"{rc.years_experience:.0f} years experience as {rc.current_title}"
        )

        if exp.improvement_areas:
            parts.append(f"Areas for improvement: {exp.improvement_areas[0]}")

        return ". ".join(parts)

    @property
    def candidates_processed(self) -> int:
        return self._candidates_processed

    @property
    def heap_size(self) -> int:
        return len(self._heap)

    def reset(self):
        """Reset the ranking engine."""
        self._heap.clear()
        self._candidates_processed = 0
