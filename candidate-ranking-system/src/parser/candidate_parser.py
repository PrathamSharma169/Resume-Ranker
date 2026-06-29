"""
Candidate Parser — Stream and parse candidate profiles from JSONL.
Converts raw JSON into typed CandidateObject dataclasses.
Memory-efficient streaming with schema validation.
"""

import json
from pathlib import Path
from typing import Generator, Optional, Union
from models.candidate import (
    CandidateObject, Profile, CareerEntry, Education,
    Skill, Certification, Language, RedrobSignals, SalaryRange
)
from src.utils.logger import get_logger
from src.utils.json_utils import safe_get, safe_get_float, safe_get_int, safe_get_bool, safe_get_str, safe_get_list

logger = get_logger("candidate_parser")


def parse_candidate(data: dict) -> Optional[CandidateObject]:
    """
    Parse a single candidate JSON dict into a CandidateObject.
    Returns None if the candidate is malformed.
    """
    try:
        candidate_id = safe_get_str(data, "candidate_id")
        if not candidate_id:
            return None

        # Parse profile
        profile_data = data.get("profile", {})
        profile = Profile(
            anonymized_name=safe_get_str(profile_data, "anonymized_name"),
            headline=safe_get_str(profile_data, "headline"),
            summary=safe_get_str(profile_data, "summary"),
            location=safe_get_str(profile_data, "location"),
            country=safe_get_str(profile_data, "country"),
            years_of_experience=safe_get_float(profile_data, "years_of_experience"),
            current_title=safe_get_str(profile_data, "current_title"),
            current_company=safe_get_str(profile_data, "current_company"),
            current_company_size=safe_get_str(profile_data, "current_company_size"),
            current_industry=safe_get_str(profile_data, "current_industry"),
        )

        # Parse career history
        career_history = []
        for entry in safe_get_list(data, "career_history"):
            career_history.append(CareerEntry(
                company=safe_get_str(entry, "company"),
                title=safe_get_str(entry, "title"),
                start_date=safe_get_str(entry, "start_date"),
                end_date=entry.get("end_date"),
                duration_months=safe_get_int(entry, "duration_months"),
                is_current=safe_get_bool(entry, "is_current"),
                industry=safe_get_str(entry, "industry"),
                company_size=safe_get_str(entry, "company_size"),
                description=safe_get_str(entry, "description"),
            ))

        # Parse education
        education = []
        for entry in safe_get_list(data, "education"):
            education.append(Education(
                institution=safe_get_str(entry, "institution"),
                degree=safe_get_str(entry, "degree"),
                field_of_study=safe_get_str(entry, "field_of_study"),
                start_year=safe_get_int(entry, "start_year"),
                end_year=safe_get_int(entry, "end_year"),
                grade=entry.get("grade"),
                tier=safe_get_str(entry, "tier", "unknown"),
            ))

        # Parse skills
        skills = []
        for entry in safe_get_list(data, "skills"):
            skills.append(Skill(
                name=safe_get_str(entry, "name"),
                proficiency=safe_get_str(entry, "proficiency", "beginner"),
                endorsements=safe_get_int(entry, "endorsements"),
                duration_months=safe_get_int(entry, "duration_months"),
            ))

        # Parse certifications
        certifications = []
        for entry in safe_get_list(data, "certifications"):
            certifications.append(Certification(
                name=safe_get_str(entry, "name"),
                issuer=safe_get_str(entry, "issuer"),
                year=safe_get_int(entry, "year"),
            ))

        # Parse languages
        languages = []
        for entry in safe_get_list(data, "languages"):
            languages.append(Language(
                language=safe_get_str(entry, "language"),
                proficiency=safe_get_str(entry, "proficiency", "basic"),
            ))

        # Parse redrob signals
        signals_data = data.get("redrob_signals", {})
        salary_data = signals_data.get("expected_salary_range_inr_lpa", {})
        salary = SalaryRange(
            min_lpa=safe_get_float(salary_data, "min"),
            max_lpa=safe_get_float(salary_data, "max"),
        ) if salary_data else None

        redrob_signals = RedrobSignals(
            profile_completeness_score=safe_get_float(signals_data, "profile_completeness_score"),
            signup_date=safe_get_str(signals_data, "signup_date"),
            last_active_date=safe_get_str(signals_data, "last_active_date"),
            open_to_work_flag=safe_get_bool(signals_data, "open_to_work_flag"),
            profile_views_received_30d=safe_get_int(signals_data, "profile_views_received_30d"),
            applications_submitted_30d=safe_get_int(signals_data, "applications_submitted_30d"),
            recruiter_response_rate=safe_get_float(signals_data, "recruiter_response_rate"),
            avg_response_time_hours=safe_get_float(signals_data, "avg_response_time_hours"),
            skill_assessment_scores=signals_data.get("skill_assessment_scores", {}),
            connection_count=safe_get_int(signals_data, "connection_count"),
            endorsements_received=safe_get_int(signals_data, "endorsements_received"),
            notice_period_days=safe_get_int(signals_data, "notice_period_days"),
            expected_salary_range=salary,
            preferred_work_mode=safe_get_str(signals_data, "preferred_work_mode", "flexible"),
            willing_to_relocate=safe_get_bool(signals_data, "willing_to_relocate"),
            github_activity_score=safe_get_float(signals_data, "github_activity_score", -1.0),
            search_appearance_30d=safe_get_int(signals_data, "search_appearance_30d"),
            saved_by_recruiters_30d=safe_get_int(signals_data, "saved_by_recruiters_30d"),
            interview_completion_rate=safe_get_float(signals_data, "interview_completion_rate"),
            offer_acceptance_rate=safe_get_float(signals_data, "offer_acceptance_rate", -1.0),
            verified_email=safe_get_bool(signals_data, "verified_email"),
            verified_phone=safe_get_bool(signals_data, "verified_phone"),
            linkedin_connected=safe_get_bool(signals_data, "linkedin_connected"),
        )

        return CandidateObject(
            candidate_id=candidate_id,
            profile=profile,
            career_history=career_history,
            education=education,
            skills=skills,
            certifications=certifications,
            languages=languages,
            redrob_signals=redrob_signals,
        )

    except Exception as e:
        logger.debug(f"Failed to parse candidate: {e}")
        return None


def stream_candidates(filepath: Union[str, Path]) -> Generator[CandidateObject, None, None]:
    """
    Stream candidates from a JSONL file line by line.
    Memory-efficient: only one candidate is in memory at a time.

    Supports both .jsonl and .json files.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        logger.error(f"Candidate file not found: {filepath}")
        return

    logger.info(f"Streaming candidates from: {filepath}")
    parsed_count = 0
    error_count = 0

    if filepath.suffix == ".json":
        # Handle JSON array format (sample_candidates.json)
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                candidates = json.load(f)
                if isinstance(candidates, list):
                    for data in candidates:
                        candidate = parse_candidate(data)
                        if candidate:
                            parsed_count += 1
                            yield candidate
                        else:
                            error_count += 1
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON file: {e}")

    elif filepath.suffix == ".jsonl":
        # Handle JSONL format (one candidate per line)
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    candidate = parse_candidate(data)
                    if candidate:
                        parsed_count += 1
                        yield candidate
                    else:
                        error_count += 1
                except json.JSONDecodeError:
                    error_count += 1
                    if error_count <= 5:
                        logger.warning(f"Malformed JSON at line {line_num}")

                if parsed_count % 10000 == 0 and parsed_count > 0:
                    logger.info(f"Streamed {parsed_count} candidates...")

    logger.info(f"Streaming complete: {parsed_count} parsed, {error_count} errors")


def load_sample_candidates(filepath: Union[str, Path] = None) -> list[CandidateObject]:
    """Load all candidates from sample file into memory (for development/testing)."""
    if filepath is None:
        from src.utils.file_utils import get_data_path
        filepath = get_data_path("sample_candidates.json")
    return list(stream_candidates(filepath))
