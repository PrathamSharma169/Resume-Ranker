"""
Feature Engineering Engine
Converts CandidateObjects into FeatureVectors with numerical, categorical,
semantic, and statistical features. Includes cheap scoring for progressive filtering.
"""

import numpy as np
from typing import Optional
from models.candidate import CandidateObject
from models.hiring_profile import HiringProfile
from models.feature_vector import (
    FeatureVector, ProfileFeatures, TechnicalFeatures,
    CareerFeatures, EducationFeatures, BehavioralFeatures,
    SemanticFeatures, StatisticalFeatures
)
from src.utils.logger import get_logger
from src.utils.math_utils import safe_divide, clip_score, RunningStatistics
from src.utils.text_utils import (
    text_to_lower, encode_company_size, estimate_seniority, contains_any
)

logger = get_logger("feature_engineering")

# Degree level encoding
DEGREE_LEVELS = {
    "bachelor": 1, "b.tech": 1, "b.e.": 1, "b.sc": 1, "bsc": 1, "ba": 1, "bba": 1,
    "master": 2, "m.tech": 2, "m.e.": 2, "m.sc": 2, "msc": 2, "mba": 2, "ma": 2,
    "phd": 3, "ph.d": 3, "doctorate": 3, "doctor": 3,
}


class FeatureEngineeringEngine:
    """
    Adaptive Feature Engineering Engine.
    Extracts structured features from candidates using the HiringProfile as context.
    """

    def __init__(self, embedding_model=None):
        self.embedding_model = embedding_model
        # Corpus statistics (populated during first pass)
        self.experience_stats = RunningStatistics()
        self.skills_stats = RunningStatistics()
        self.endorsement_stats = RunningStatistics()
        self.response_rate_stats = RunningStatistics()
        self.completeness_stats = RunningStatistics()

    def extract_features(
        self,
        candidate: CandidateObject,
        hiring_profile: HiringProfile,
    ) -> FeatureVector:
        """Extract complete feature vector for a candidate."""
        fv = FeatureVector(candidate_id=candidate.candidate_id)

        # Profile features
        fv.profile_features = self._extract_profile_features(candidate, hiring_profile)

        # Technical features
        fv.technical_features = self._extract_technical_features(candidate, hiring_profile)

        # Career features
        fv.career_features = self._extract_career_features(candidate, hiring_profile)

        # Education features
        fv.education_features = self._extract_education_features(candidate)

        # Behavioral features (raw — intelligence engines will analyze further)
        fv.behavioral_features = self._extract_behavioral_features(candidate)

        # Semantic features (requires embedding model)
        fv.semantic_features = self._extract_semantic_features(candidate, hiring_profile)

        # Cheap score for progressive filtering
        fv.cheap_score = self._compute_cheap_score(fv, hiring_profile)

        # Update corpus statistics
        self._update_statistics(candidate, fv)

        return fv

    def compute_statistical_features(self, fv: FeatureVector) -> StatisticalFeatures:
        """Compute corpus-relative statistical features (call after first pass)."""
        return StatisticalFeatures(
            experience_z_score=self.experience_stats.z_score(
                fv.profile_features.years_experience
            ),
            skills_z_score=self.skills_stats.z_score(
                fv.technical_features.total_skills
            ),
            endorsements_z_score=self.endorsement_stats.z_score(
                fv.technical_features.avg_endorsements
            ),
            response_rate_z_score=self.response_rate_stats.z_score(
                fv.behavioral_features.response_rate
            ),
            completeness_z_score=self.completeness_stats.z_score(
                fv.behavioral_features.profile_completeness
            ),
        )

    def _extract_profile_features(self, c: CandidateObject, hp: HiringProfile) -> ProfileFeatures:
        """Extract features from candidate profile."""
        pf = ProfileFeatures()
        pf.years_experience = c.profile.years_of_experience

        # Title relevance
        title_lower = text_to_lower(c.profile.current_title)
        required_skills = [text_to_lower(s.name) for s in hp.required_competencies[:10]]
        pf.title_relevance = self._compute_text_relevance(title_lower, required_skills)

        # Industry relevance
        industry_lower = text_to_lower(c.profile.current_industry)
        concepts = [text_to_lower(sc.primary_term) for sc in hp.semantic_concepts]
        pf.industry_relevance = self._compute_text_relevance(industry_lower, concepts)

        # Company size
        pf.company_size_encoded = encode_company_size(c.profile.current_company_size) / 8.0

        return pf

    def _extract_technical_features(self, c: CandidateObject, hp: HiringProfile) -> TechnicalFeatures:
        """Extract technical features."""
        tf = TechnicalFeatures()
        tf.total_skills = len(c.skills)

        if not c.skills:
            return tf

        # Required skills matching
        required = set(text_to_lower(comp.name) for comp in hp.required_competencies)
        all_required = set(text_to_lower(comp.name) for comp in hp.required_competencies + hp.preferred_competencies)
        candidate_skills = set(text_to_lower(s.name) for s in c.skills)

        # Fuzzy matching: check if any candidate skill contains the required term
        relevant_count = 0
        for req in all_required:
            for cs in candidate_skills:
                if req in cs or cs in req:
                    relevant_count += 1
                    break

        tf.relevant_skills_count = relevant_count
        tf.relevant_skills_ratio = safe_divide(relevant_count, len(all_required))
        tf.skill_coverage = safe_divide(relevant_count, max(1, len(required)))

        # Proficiency analysis
        proficiency_map = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
        proficiencies = [proficiency_map.get(s.proficiency, 1) for s in c.skills]
        tf.avg_proficiency = np.mean(proficiencies) / 4.0 if proficiencies else 0

        # Endorsements
        endorsements = [s.endorsements for s in c.skills]
        tf.avg_endorsements = np.mean(endorsements) if endorsements else 0

        # Duration
        durations = [s.duration_months for s in c.skills if s.duration_months > 0]
        tf.avg_skill_duration = np.mean(durations) if durations else 0

        # Advanced/Expert ratio
        advanced_count = sum(1 for s in c.skills if s.proficiency in ("advanced", "expert"))
        tf.advanced_expert_ratio = safe_divide(advanced_count, len(c.skills))

        # Assessments
        scores = list(c.redrob_signals.skill_assessment_scores.values())
        tf.assessment_score_avg = np.mean(scores) / 100.0 if scores else 0

        # Relevant assessments
        relevant_scores = []
        for assess_name, score in c.redrob_signals.skill_assessment_scores.items():
            assess_lower = text_to_lower(assess_name)
            if any(req in assess_lower for req in required):
                relevant_scores.append(score)
        tf.relevant_assessment_avg = np.mean(relevant_scores) / 100.0 if relevant_scores else 0

        # Certifications
        tf.certification_count = len(c.certifications)

        return tf

    def _extract_career_features(self, c: CandidateObject, hp: HiringProfile) -> CareerFeatures:
        """Extract career features."""
        cf = CareerFeatures()
        cf.total_companies = len(c.career_history)

        if not c.career_history:
            return cf

        durations = [e.duration_months for e in c.career_history]
        cf.total_career_months = sum(durations)
        cf.avg_tenure_months = np.mean(durations) if durations else 0

        # Current tenure
        current_entries = [e for e in c.career_history if e.is_current]
        cf.current_tenure_months = current_entries[0].duration_months if current_entries else 0

        # Company size analysis
        sizes = [encode_company_size(e.company_size) for e in c.career_history]
        cf.startup_experience = any(s <= 2 for s in sizes)
        cf.large_company_experience = any(s >= 6 for s in sizes)

        # Relevant career description content
        required_terms = [text_to_lower(comp.name) for comp in hp.required_competencies[:10]]
        relevant_months = 0
        for entry in c.career_history:
            desc_lower = text_to_lower(entry.description)
            if any(term in desc_lower for term in required_terms):
                relevant_months += entry.duration_months
        cf.relevant_experience_months = relevant_months

        return cf

    def _extract_education_features(self, c: CandidateObject) -> EducationFeatures:
        """Extract education features."""
        ef = EducationFeatures()
        ef.education_count = len(c.education)

        if not c.education:
            return ef

        # Highest degree
        max_level = 0
        best_tier = 4
        for edu in c.education:
            degree_lower = text_to_lower(edu.degree)
            for keyword, level in DEGREE_LEVELS.items():
                if keyword in degree_lower:
                    max_level = max(max_level, level)
                    break

            # Institution tier
            tier_map = {"tier_1": 1, "tier_2": 2, "tier_3": 3}
            tier_val = tier_map.get(edu.tier, 4)
            best_tier = min(best_tier, tier_val)

        ef.highest_degree_level = max_level
        ef.institution_tier = best_tier

        return ef

    def _extract_behavioral_features(self, c: CandidateObject) -> BehavioralFeatures:
        """Extract raw behavioral features."""
        s = c.redrob_signals
        return BehavioralFeatures(
            profile_completeness=s.profile_completeness_score,
            open_to_work=s.open_to_work_flag,
            profile_views_30d=s.profile_views_received_30d,
            applications_30d=s.applications_submitted_30d,
            response_rate=s.recruiter_response_rate,
            avg_response_time=s.avg_response_time_hours,
            connection_count=s.connection_count,
            endorsements_received=s.endorsements_received,
            notice_period_days=s.notice_period_days,
            github_activity=s.github_activity_score,
            search_appearances_30d=s.search_appearance_30d,
            saved_by_recruiters_30d=s.saved_by_recruiters_30d,
            interview_completion_rate=s.interview_completion_rate,
            offer_acceptance_rate=s.offer_acceptance_rate,
            verified_email=s.verified_email,
            verified_phone=s.verified_phone,
            linkedin_connected=s.linkedin_connected,
            willing_to_relocate=s.willing_to_relocate,
            preferred_work_mode=s.preferred_work_mode,
        )

    def _extract_semantic_features(self, c: CandidateObject, hp: HiringProfile) -> SemanticFeatures:
        """Extract semantic similarity features."""
        sf = SemanticFeatures()

        if self.embedding_model is None or not hp.jd_full_text:
            return sf

        try:
            # Compute candidate text embeddings
            candidate_texts = []
            text_labels = []

            if c.profile.summary:
                candidate_texts.append(c.profile.summary[:500])
                text_labels.append("summary")
            if c.career_text:
                candidate_texts.append(c.career_text[:500])
                text_labels.append("career")
            if c.profile.headline:
                candidate_texts.append(c.profile.headline)
                text_labels.append("headline")

            skill_text = ", ".join(c.skill_names[:30])
            if skill_text:
                candidate_texts.append(skill_text)
                text_labels.append("skills")

            if not candidate_texts:
                return sf

            # Encode candidate texts
            cand_embeddings = self.embedding_model.encode(
                candidate_texts,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

            # Encode JD text (or use cached)
            jd_text = hp.jd_full_text[:1000]
            jd_embedding = self.embedding_model.encode(
                [jd_text],
                show_progress_bar=False,
                convert_to_numpy=True,
            )[0]

            # Compute similarities
            from src.utils.math_utils import cosine_similarity

            for emb, label in zip(cand_embeddings, text_labels):
                sim = cosine_similarity(emb, jd_embedding)
                if label == "summary":
                    sf.summary_jd_similarity = sim
                    sf.summary_embedding = emb.tolist()
                elif label == "career":
                    sf.career_jd_similarity = sim
                    sf.career_embedding = emb.tolist()
                elif label == "headline":
                    sf.headline_jd_similarity = sim
                elif label == "skills":
                    sf.skills_jd_similarity = sim

            # Overall
            sims = [sf.summary_jd_similarity, sf.career_jd_similarity,
                    sf.skills_jd_similarity, sf.headline_jd_similarity]
            non_zero = [s for s in sims if s > 0]
            sf.overall_semantic_score = np.mean(non_zero) if non_zero else 0

        except Exception as e:
            logger.debug(f"Semantic feature extraction failed: {e}")

        return sf

    def _compute_cheap_score(self, fv: FeatureVector, hp: HiringProfile) -> float:
        """Compute a quick score for progressive filtering (no embeddings needed)."""
        score = 0.0

        # Technical alignment (skill matching)
        score += fv.technical_features.skill_coverage * 0.25
        score += fv.technical_features.relevant_skills_ratio * 0.15

        # Experience alignment
        exp = hp.experience_expectation
        years = fv.profile_features.years_experience
        if exp.min_years <= years <= exp.max_years:
            score += 0.15
        elif years >= exp.min_years * 0.7:
            score += 0.08

        # Title relevance
        score += fv.profile_features.title_relevance * 0.15

        # Assessment scores
        score += fv.technical_features.assessment_score_avg * 0.10
        score += fv.technical_features.relevant_assessment_avg * 0.10

        # Profile completeness
        score += (fv.behavioral_features.profile_completeness / 100.0) * 0.05

        # Proficiency
        score += fv.technical_features.avg_proficiency * 0.05

        return clip_score(score)

    def _compute_text_relevance(self, text: str, keywords: list[str]) -> float:
        """Compute relevance of text to keywords."""
        if not text or not keywords:
            return 0.0
        matches = sum(1 for kw in keywords if kw in text)
        return clip_score(matches * 0.15)

    def _update_statistics(self, c: CandidateObject, fv: FeatureVector) -> None:
        """Update running statistics for corpus normalization."""
        self.experience_stats.update(c.profile.years_of_experience)
        self.skills_stats.update(len(c.skills))
        self.endorsement_stats.update(fv.technical_features.avg_endorsements)
        self.response_rate_stats.update(c.redrob_signals.recruiter_response_rate)
        self.completeness_stats.update(c.redrob_signals.profile_completeness_score)
