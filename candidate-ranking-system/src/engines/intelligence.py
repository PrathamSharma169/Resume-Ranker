"""
Intelligence Engines — All intelligence analysis modules.
Evidence, Authenticity, Narrative, Behavioral, and Recruitability engines.
Each produces an independent profile that contributes to the final ranking.
"""

import re
import numpy as np
from datetime import datetime
from typing import Optional
from models.candidate import CandidateObject
from models.hiring_profile import HiringProfile
from models.feature_vector import FeatureVector
from models.evidence import EvidenceProfile, CompetencyEvidence
from models.authenticity import AuthenticityProfile
from models.narrative import NarrativeProfile, CareerTransition
from models.behavior import BehavioralProfile
from models.recruitability import RecruitabilityProfile
from src.utils.logger import get_logger
from src.utils.math_utils import clip_score, safe_divide, weighted_average
from src.utils.text_utils import (
    text_to_lower, contains_any, count_term_occurrences,
    estimate_seniority, encode_company_size
)

logger = get_logger("intelligence")


# ============================================================================
# Evidence Intelligence Engine
# ============================================================================

class EvidenceEngine:
    """Measures how strongly candidate claims are supported by evidence."""

    def analyze(
        self,
        candidate: CandidateObject,
        hiring_profile: HiringProfile,
        features: FeatureVector,
    ) -> EvidenceProfile:
        """Analyze evidence for all required competencies."""
        profile = EvidenceProfile(candidate_id=candidate.candidate_id)
        competencies = hiring_profile.all_competency_names

        if not competencies:
            profile.overall_evidence_score = 0.5
            return profile

        # Build searchable text corpus from candidate
        summary_lower = text_to_lower(candidate.profile.summary)
        headline_lower = text_to_lower(candidate.profile.headline)
        career_texts = [text_to_lower(e.description) for e in candidate.career_history if e.description]
        career_combined = " ".join(career_texts)
        skill_names_lower = [text_to_lower(s.name) for s in candidate.skills]
        cert_names = [text_to_lower(c.name) for c in candidate.certifications]
        assessments = candidate.redrob_signals.skill_assessment_scores

        total_confidence = 0.0
        for comp_name in competencies:
            comp_lower = comp_name.lower()
            evidence = CompetencyEvidence(competency_name=comp_name)

            # Check each evidence source
            evidence.mentioned_in_skills = any(comp_lower in s for s in skill_names_lower)
            evidence.mentioned_in_summary = comp_lower in summary_lower or comp_lower in headline_lower
            evidence.mentioned_in_career = comp_lower in career_combined
            evidence.mentioned_in_certifications = any(comp_lower in c for c in cert_names)

            # Check assessments
            for assess_name, score in assessments.items():
                if comp_lower in assess_name.lower():
                    evidence.assessment_score = score
                    break

            # Skill duration and endorsements
            for skill in candidate.skills:
                if comp_lower in skill.name.lower():
                    evidence.skill_duration_months = skill.duration_months
                    evidence.endorsement_count = skill.endorsements
                    break

            # Count career mentions
            evidence.career_mentions_count = sum(
                1 for t in career_texts if comp_lower in t
            )

            # Calculate source count and confidence
            sources = sum([
                evidence.mentioned_in_skills,
                evidence.mentioned_in_summary,
                evidence.mentioned_in_career,
                evidence.mentioned_in_certifications,
                evidence.assessment_score > 0,
            ])
            evidence.source_count = sources

            # Confidence formula: more sources = higher confidence
            base_confidence = min(1.0, sources * 0.25)

            # Boost for strong evidence
            if evidence.assessment_score > 60:
                base_confidence += 0.15
            if evidence.skill_duration_months > 24:
                base_confidence += 0.10
            if evidence.endorsement_count > 10:
                base_confidence += 0.05
            if evidence.career_mentions_count > 1:
                base_confidence += 0.10

            evidence.confidence = clip_score(base_confidence)
            total_confidence += evidence.confidence
            profile.competency_evidence.append(evidence)

        # Aggregate metrics
        n = len(competencies)
        profile.overall_evidence_score = clip_score(total_confidence / n) if n > 0 else 0
        profile.evidence_coverage = safe_divide(
            sum(1 for e in profile.competency_evidence if e.source_count > 0), n
        )
        profile.evidence_density = safe_divide(
            sum(e.source_count for e in profile.competency_evidence), n
        )
        profile.strong_evidence_count = sum(
            1 for e in profile.competency_evidence if e.confidence > 0.6
        )
        profile.weak_evidence_count = sum(
            1 for e in profile.competency_evidence if e.confidence < 0.3
        )
        profile.unsupported_claims = [
            e.competency_name for e in profile.competency_evidence if e.source_count == 0
        ]

        return profile


# ============================================================================
# Authenticity Engine
# ============================================================================

class AuthenticityEngine:
    """Measures internal profile consistency and coherence."""

    def analyze(
        self,
        candidate: CandidateObject,
        evidence_profile: EvidenceProfile,
        features: FeatureVector,
    ) -> AuthenticityProfile:
        """Analyze profile authenticity."""
        profile = AuthenticityProfile(candidate_id=candidate.candidate_id)
        inconsistencies = []

        # 1. Semantic coherence: headline vs summary vs career
        profile.semantic_coherence = self._check_semantic_coherence(candidate)

        # 2. Career coherence: progression consistency
        profile.career_coherence = self._check_career_coherence(candidate)

        # 3. Evidence alignment: skills match experience
        profile.evidence_alignment = self._check_evidence_alignment(candidate, evidence_profile)

        # 4. Timeline consistency
        profile.timeline_consistency = self._check_timeline(candidate, inconsistencies)

        # 5. Education alignment
        profile.education_alignment = self._check_education_alignment(candidate)

        # 6. Profile support
        profile.profile_support = self._check_profile_support(candidate)

        # Overall score (weighted average)
        profile.overall_authenticity = weighted_average(
            [profile.semantic_coherence, profile.career_coherence,
             profile.evidence_alignment, profile.timeline_consistency,
             profile.education_alignment, profile.profile_support],
            [0.25, 0.25, 0.20, 0.15, 0.05, 0.10]
        )
        profile.inconsistencies = inconsistencies

        return profile

    def _check_semantic_coherence(self, candidate: CandidateObject) -> float:
        """Check if headline, summary, and career tell a consistent story."""
        headline = text_to_lower(candidate.profile.headline)
        summary = text_to_lower(candidate.profile.summary)
        current_title = text_to_lower(candidate.profile.current_title)

        if not headline or not summary:
            return 0.5

        # Check if current title appears in headline
        score = 0.5
        title_words = current_title.split()
        if title_words:
            title_match = sum(1 for w in title_words if w in headline) / len(title_words)
            score += title_match * 0.3

        # Check career keywords appear in summary
        career_keywords = set()
        for entry in candidate.career_history[:3]:
            for word in text_to_lower(entry.title).split():
                if len(word) > 3:
                    career_keywords.add(word)

        if career_keywords:
            keyword_match = sum(1 for k in career_keywords if k in summary)
            score += min(0.2, keyword_match * 0.05)

        return clip_score(score)

    def _check_career_coherence(self, candidate: CandidateObject) -> float:
        """Check career progression makes logical sense."""
        if len(candidate.career_history) < 2:
            return 0.7  # can't assess with one job

        score = 0.7  # baseline
        transitions = 0
        coherent_transitions = 0

        for i in range(len(candidate.career_history) - 1):
            current = candidate.career_history[i]
            prev = candidate.career_history[i + 1]

            transitions += 1
            # Check if industries are related
            if current.industry and prev.industry:
                if current.industry == prev.industry:
                    coherent_transitions += 1
                elif any(w in text_to_lower(current.industry)
                         for w in text_to_lower(prev.industry).split()
                         if len(w) > 3):
                    coherent_transitions += 0.5

        if transitions > 0:
            coherence_ratio = coherent_transitions / transitions
            score = 0.4 + coherence_ratio * 0.6

        return clip_score(score)

    def _check_evidence_alignment(self, candidate: CandidateObject, evidence: EvidenceProfile) -> float:
        """Check if skills are supported by career evidence."""
        if not evidence.competency_evidence:
            return 0.5

        # High evidence coverage = good alignment
        return clip_score(evidence.evidence_coverage * 0.5 + evidence.overall_evidence_score * 0.5)

    def _check_timeline(self, candidate: CandidateObject, inconsistencies: list) -> float:
        """Check career timeline for inconsistencies."""
        score = 1.0
        career = candidate.career_history

        if len(career) < 2:
            return 0.9

        # Check for overlapping dates
        for i in range(len(career)):
            for j in range(i + 1, len(career)):
                try:
                    if career[i].start_date and career[j].end_date:
                        start_i = career[i].start_date
                        end_j = career[j].end_date
                        if end_j and start_i < end_j and not career[i].is_current:
                            # Slight overlap is common, large overlap is suspicious
                            pass  # Don't penalize heavily, overlaps are common
                except (ValueError, TypeError):
                    pass

        # Check total experience vs sum of durations
        total_months = sum(e.duration_months for e in career)
        stated_years = candidate.profile.years_of_experience
        if stated_years > 0:
            computed_years = total_months / 12.0
            ratio = safe_divide(computed_years, stated_years, 1.0)
            if ratio < 0.5 or ratio > 2.0:
                score -= 0.2
                inconsistencies.append(
                    f"Experience mismatch: stated {stated_years:.1f}y vs computed {computed_years:.1f}y"
                )

        return clip_score(score)

    def _check_education_alignment(self, candidate: CandidateObject) -> float:
        """Check if education supports the career direction."""
        if not candidate.education:
            return 0.5

        tech_fields = ["computer", "software", "engineering", "data", "mathematics",
                       "statistics", "physics", "information", "artificial", "machine"]
        current_title = text_to_lower(candidate.profile.current_title)
        is_tech_role = any(t in current_title for t in ["engineer", "developer",
                                                          "scientist", "analyst", "ml", "ai"])

        if is_tech_role:
            has_tech_edu = any(
                any(f in text_to_lower(e.field_of_study) for f in tech_fields)
                for e in candidate.education
            )
            return 0.8 if has_tech_edu else 0.5

        return 0.6

    def _check_profile_support(self, candidate: CandidateObject) -> float:
        """Check if profile sections mutually support each other."""
        score = 0.5
        if candidate.profile.summary and len(candidate.profile.summary) > 50:
            score += 0.15
        if candidate.career_history:
            score += 0.15
        if candidate.skills:
            score += 0.10
        if candidate.education:
            score += 0.05
        if candidate.certifications:
            score += 0.05
        return clip_score(score)


# ============================================================================
# Career Narrative Engine
# ============================================================================

class NarrativeEngine:
    """Evaluates professional evolution and career trajectory."""

    def analyze(
        self,
        candidate: CandidateObject,
        hiring_profile: HiringProfile,
        features: FeatureVector,
    ) -> NarrativeProfile:
        """Analyze career narrative."""
        profile = NarrativeProfile(candidate_id=candidate.candidate_id)
        career = candidate.career_history

        if not career:
            profile.narrative_strength = 0.3
            return profile

        # Build transitions
        profile.transitions = self._build_transitions(career)

        # Progression analysis
        profile.career_progression = self._analyze_progression(career, profile.transitions)

        # Specialization trend
        profile.specialization_trend = self._analyze_specialization(career, hiring_profile)

        # Growth score
        profile.growth_score = self._analyze_growth(career)

        # Domain alignment
        profile.domain_alignment = self._analyze_domain_alignment(career, hiring_profile)

        # Career direction
        profile.career_direction = self._determine_direction(profile)

        # Overall narrative strength
        profile.narrative_strength = weighted_average(
            [profile.career_progression, profile.specialization_trend,
             profile.growth_score, profile.domain_alignment],
            [0.30, 0.25, 0.25, 0.20]
        )

        return profile

    def _build_transitions(self, career: list) -> list[CareerTransition]:
        """Build career transitions from history."""
        transitions = []
        for i in range(len(career) - 1):
            current = career[i]
            prev = career[i + 1]

            # Estimate transition quality via seniority
            current_seniority = estimate_seniority(current.title)
            prev_seniority = estimate_seniority(prev.title)

            transition = CareerTransition(
                from_title=prev.title,
                to_title=current.title,
                from_industry=prev.industry,
                to_industry=current.industry,
                is_advancement=current_seniority > prev_seniority,
                is_lateral=current_seniority == prev_seniority,
            )

            # Check if specializing
            if current.industry == prev.industry:
                transition.transition_quality = 0.8
                transition.is_specialization = current_seniority >= prev_seniority
            else:
                transition.transition_quality = 0.5

            transitions.append(transition)

        return transitions

    def _analyze_progression(self, career: list, transitions: list) -> float:
        """Analyze overall career progression."""
        if not transitions:
            return 0.6

        advancements = sum(1 for t in transitions if t.is_advancement)
        laterals = sum(1 for t in transitions if t.is_lateral)
        total = len(transitions)

        advancement_ratio = safe_divide(advancements, total)
        stability = safe_divide(laterals + advancements, total)

        return clip_score(0.3 + advancement_ratio * 0.4 + stability * 0.3)

    def _analyze_specialization(self, career: list, hiring_profile: HiringProfile) -> float:
        """Analyze specialization toward the target role."""
        if not career:
            return 0.3

        target_keywords = set()
        for comp in hiring_profile.required_competencies[:10]:
            target_keywords.update(comp.name.lower().split())

        # Check recent vs older roles
        recent = career[:2]  # most recent roles
        older = career[2:]

        recent_alignment = 0
        for entry in recent:
            text_lower = text_to_lower(entry.title + " " + entry.description)
            matches = sum(1 for kw in target_keywords if kw in text_lower)
            recent_alignment += min(1.0, matches * 0.15)

        older_alignment = 0
        for entry in older:
            text_lower = text_to_lower(entry.title + " " + entry.description)
            matches = sum(1 for kw in target_keywords if kw in text_lower)
            older_alignment += min(1.0, matches * 0.15)

        recent_avg = safe_divide(recent_alignment, len(recent))
        older_avg = safe_divide(older_alignment, max(1, len(older)))

        # Increasing alignment toward target = good specialization
        if recent_avg > older_avg:
            return clip_score(0.5 + recent_avg * 0.5)
        return clip_score(0.3 + recent_avg * 0.4)

    def _analyze_growth(self, career: list) -> float:
        """Analyze professional growth."""
        if len(career) < 2:
            return 0.5

        # Company size growth
        sizes = [encode_company_size(e.company_size) for e in career]
        size_trend = 0
        for i in range(len(sizes) - 1):
            if sizes[i] > sizes[i + 1]:
                size_trend += 1
            elif sizes[i] == sizes[i + 1]:
                size_trend += 0.5

        growth_ratio = safe_divide(size_trend, max(1, len(sizes) - 1))

        # Seniority growth
        seniorities = [estimate_seniority(e.title) for e in career]
        seniority_growth = 0
        for i in range(len(seniorities) - 1):
            if seniorities[i] >= seniorities[i + 1]:
                seniority_growth += 1

        seniority_ratio = safe_divide(seniority_growth, max(1, len(seniorities) - 1))

        return clip_score(0.3 + growth_ratio * 0.3 + seniority_ratio * 0.4)

    def _analyze_domain_alignment(self, career: list, hiring_profile: HiringProfile) -> float:
        """Analyze how well the career aligns with the target domain."""
        if not career:
            return 0.3

        target_keywords = set()
        for comp in hiring_profile.required_competencies:
            target_keywords.update(comp.name.lower().split())

        alignments = []
        for entry in career:
            text = text_to_lower(entry.title + " " + entry.description)
            matches = sum(1 for kw in target_keywords if kw in text and len(kw) > 2)
            alignments.append(min(1.0, matches * 0.12))

        return clip_score(np.mean(alignments)) if alignments else 0.3

    def _determine_direction(self, profile: NarrativeProfile) -> str:
        """Determine overall career direction."""
        if profile.career_progression > 0.7:
            return "ascending"
        elif profile.career_progression > 0.5:
            return "lateral"
        elif profile.career_progression > 0.3:
            return "mixed"
        return "declining"


# ============================================================================
# Behavioral Intelligence Engine
# ============================================================================

class BehavioralEngine:
    """Evaluates candidate engagement and platform behavior."""

    def __init__(self):
        # Corpus statistics for normalization (updated during first pass)
        self.stats = {}

    def analyze(
        self,
        candidate: CandidateObject,
        features: FeatureVector,
    ) -> BehavioralProfile:
        """Analyze behavioral signals."""
        signals = candidate.redrob_signals
        profile = BehavioralProfile(candidate_id=candidate.candidate_id)

        # Engagement: activity-related signals
        profile.engagement_score = self._compute_engagement(signals)

        # Responsiveness: recruiter interaction
        profile.responsiveness_score = self._compute_responsiveness(signals)

        # Activity: platform activity
        profile.activity_score = self._compute_activity(signals)

        # Recruiter interest
        profile.recruiter_interest_score = self._compute_recruiter_interest(signals)

        # Verification
        profile.verification_score = self._compute_verification(signals)

        # Hiring readiness
        profile.hiring_readiness_score = self._compute_hiring_readiness(signals)

        # Profile quality
        profile.profile_quality_score = signals.profile_completeness_score / 100.0

        # Overall
        profile.overall_behavioral_score = weighted_average(
            [profile.engagement_score, profile.responsiveness_score,
             profile.activity_score, profile.recruiter_interest_score,
             profile.verification_score, profile.hiring_readiness_score,
             profile.profile_quality_score],
            [0.15, 0.20, 0.10, 0.15, 0.10, 0.15, 0.15]
        )

        return profile

    def _compute_engagement(self, signals) -> float:
        """Compute engagement score."""
        score = 0.3
        if signals.applications_submitted_30d > 0:
            score += min(0.2, signals.applications_submitted_30d * 0.03)
        if signals.connection_count > 100:
            score += 0.1
        if signals.endorsements_received > 10:
            score += 0.1
        if signals.github_activity_score > 30:
            score += 0.15
        if signals.interview_completion_rate > 0.7:
            score += 0.15
        return clip_score(score)

    def _compute_responsiveness(self, signals) -> float:
        """Compute responsiveness score."""
        score = signals.recruiter_response_rate
        # Penalize slow response times
        if signals.avg_response_time_hours < 24:
            score = min(1.0, score + 0.15)
        elif signals.avg_response_time_hours > 120:
            score = max(0.0, score - 0.1)
        return clip_score(score)

    def _compute_activity(self, signals) -> float:
        """Compute platform activity score."""
        score = 0.3
        if signals.profile_views_received_30d > 10:
            score += 0.15
        if signals.search_appearance_30d > 50:
            score += 0.15
        if signals.applications_submitted_30d > 0:
            score += 0.1

        # Recency of activity
        try:
            last_active = datetime.strptime(signals.last_active_date, "%Y-%m-%d")
            days_inactive = (datetime.now() - last_active).days
            if days_inactive < 30:
                score += 0.2
            elif days_inactive < 90:
                score += 0.1
        except (ValueError, TypeError):
            pass

        return clip_score(score)

    def _compute_recruiter_interest(self, signals) -> float:
        """Compute recruiter interest signals."""
        score = 0.3
        if signals.saved_by_recruiters_30d > 5:
            score += 0.3
        elif signals.saved_by_recruiters_30d > 0:
            score += 0.15
        if signals.profile_views_received_30d > 20:
            score += 0.2
        if signals.search_appearance_30d > 100:
            score += 0.2
        return clip_score(score)

    def _compute_verification(self, signals) -> float:
        """Compute verification trust score."""
        score = 0.3
        if signals.verified_email:
            score += 0.25
        if signals.verified_phone:
            score += 0.25
        if signals.linkedin_connected:
            score += 0.2
        return clip_score(score)

    def _compute_hiring_readiness(self, signals) -> float:
        """Compute hiring readiness."""
        score = 0.3
        if signals.open_to_work_flag:
            score += 0.25
        if signals.notice_period_days <= 30:
            score += 0.2
        elif signals.notice_period_days <= 60:
            score += 0.1
        if signals.offer_acceptance_rate > 0.5:
            score += 0.15
        if signals.interview_completion_rate > 0.8:
            score += 0.1
        return clip_score(score)


# ============================================================================
# Recruitability Engine
# ============================================================================

class RecruitabilityEngine:
    """Estimates hiring feasibility based on practical constraints."""

    def analyze(
        self,
        candidate: CandidateObject,
        hiring_profile: HiringProfile,
        behavioral_profile: BehavioralProfile,
        features: FeatureVector,
    ) -> RecruitabilityProfile:
        """Analyze recruitability."""
        signals = candidate.redrob_signals
        profile = RecruitabilityProfile(candidate_id=candidate.candidate_id)

        # Availability
        profile.availability_score = self._compute_availability(signals)

        # Hiring compatibility (constraint satisfaction)
        profile.hiring_compatibility = self._compute_hiring_compatibility(
            candidate, hiring_profile
        )

        # Constraint compatibility (work mode, location)
        profile.constraint_compatibility = self._compute_constraint_compatibility(
            candidate, hiring_profile
        )

        # Behavioral support
        profile.behavioral_support = behavioral_profile.overall_behavioral_score

        # Recruiter success estimate
        profile.recruiter_success_estimate = weighted_average(
            [profile.availability_score, profile.hiring_compatibility,
             profile.behavioral_support, profile.constraint_compatibility],
            [0.30, 0.25, 0.25, 0.20]
        )

        # Overall
        profile.recruitability_score = profile.recruiter_success_estimate

        return profile

    def _compute_availability(self, signals) -> float:
        """Compute candidate availability."""
        score = 0.4
        if signals.open_to_work_flag:
            score += 0.25
        # Notice period (lower = more available)
        if signals.notice_period_days <= 15:
            score += 0.25
        elif signals.notice_period_days <= 30:
            score += 0.2
        elif signals.notice_period_days <= 60:
            score += 0.1
        elif signals.notice_period_days <= 90:
            score += 0.0
        else:
            score -= 0.1
        return clip_score(score)

    def _compute_hiring_compatibility(self, candidate: CandidateObject, hp: HiringProfile) -> float:
        """Compute compatibility with hiring constraints."""
        score = 0.5
        exp = hp.experience_expectation

        # Experience match
        years = candidate.profile.years_of_experience
        if exp.min_years <= years <= exp.max_years:
            score += 0.3
        elif years >= exp.min_years * 0.8:
            score += 0.15

        # Seniority alignment
        candidate_seniority = estimate_seniority(candidate.profile.current_title)
        if exp.seniority_level == "senior" and candidate_seniority >= 3:
            score += 0.2
        elif exp.seniority_level == "mid" and candidate_seniority >= 2:
            score += 0.2

        return clip_score(score)

    def _compute_constraint_compatibility(self, candidate: CandidateObject, hp: HiringProfile) -> float:
        """Compute work mode and location compatibility."""
        score = 0.5
        signals = candidate.redrob_signals

        # Work mode compatibility
        role_mode = hp.role_metadata.work_mode.lower()
        cand_mode = signals.preferred_work_mode.lower()

        if role_mode == "flexible" or cand_mode == "flexible":
            score += 0.25
        elif role_mode == cand_mode:
            score += 0.3
        elif role_mode == "remote" and cand_mode in ["remote", "hybrid"]:
            score += 0.2
        elif role_mode == "hybrid" and cand_mode in ["remote", "hybrid", "flexible"]:
            score += 0.15

        # Relocation willingness (if onsite)
        if role_mode == "onsite" and signals.willing_to_relocate:
            score += 0.15

        return clip_score(score)
