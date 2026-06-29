"""
JD Intelligence Engine — Complete Job Description Analysis Pipeline.
Combines all JD analysis steps into a single engine that produces a HiringProfile.
"""

import re
import numpy as np
from typing import Optional
from models.hiring_profile import (
    HiringProfile, Competency, SemanticConcept,
    HiringConstraint, HiringPhilosophy,
    ExperienceExpectation, RoleMetadata
)
from src.parser.jd_loader import load_jd_from_docx
from src.utils.logger import get_logger
from src.utils.timer import Timer
from src.utils.text_utils import normalize_text, extract_sentences, text_to_lower
from src.utils.file_utils import get_data_path

logger = get_logger("jd_engine")

# Section classification patterns
REQUIREMENT_PATTERNS = [
    r"must\s+have", r"required", r"essential", r"mandatory",
    r"strong\s+(?:experience|knowledge|skills)", r"proficien",
    r"you\s+(?:will|should|need)", r"expect(?:ed)?",
]
PREFERRED_PATTERNS = [
    r"nice\s+to\s+have", r"prefer(?:red|ably)?", r"bonus",
    r"advantag", r"ideal(?:ly)?", r"plus",
]
DISQUALIFIER_PATTERNS = [
    r"not\s+looking", r"do\s+not", r"avoid", r"don't\s+want",
    r"we\s+are\s+not", r"should\s+not",
]

# Hiring philosophy dimensions
PHILOSOPHY_PATTERNS = {
    "product_mindset": [
        r"product", r"user[\s-]?facing", r"ship(?:ping)?", r"launch",
        r"impact", r"customer", r"real[\s-]?world",
    ],
    "production_experience": [
        r"production", r"deploy", r"scale", r"infrastructure",
        r"reliability", r"monitor", r"ops",
    ],
    "startup_adaptability": [
        r"startup", r"fast[\s-]?paced", r"agile", r"scrappy",
        r"ownership", r"wear\s+many\s+hats", r"ambiguity",
    ],
    "research_orientation": [
        r"research", r"paper", r"novel", r"state[\s-]?of[\s-]?the[\s-]?art",
        r"experiment", r"hypothesis",
    ],
    "execution_speed": [
        r"fast", r"rapid", r"quick", r"velocity",
        r"iterate", r"move\s+fast", r"deadline",
    ],
}

# Technical skill extraction patterns
TECH_SKILL_PATTERNS = [
    # AI/ML
    r"(?:large\s+)?language\s+model", r"LLM", r"transformer",
    r"NLP", r"natural\s+language", r"GPT", r"BERT", r"embedding",
    r"RAG", r"retrieval", r"vector\s+(?:search|database|store)",
    r"FAISS", r"Pinecone", r"Milvus", r"Weaviate", r"Chroma",
    r"LangChain", r"LlamaIndex", r"fine[\s-]?tun",
    r"LoRA", r"PEFT", r"prompt\s+engineering",
    r"machine\s+learning", r"deep\s+learning", r"neural\s+network",
    r"TensorFlow", r"PyTorch", r"scikit[\s-]?learn",
    r"reinforcement\s+learning", r"computer\s+vision",
    # Programming
    r"Python", r"Java(?:Script)?", r"TypeScript", r"Go(?:lang)?",
    r"Rust", r"C\+\+", r"SQL", r"NoSQL",
    # Infrastructure
    r"Docker", r"Kubernetes", r"AWS", r"GCP", r"Azure",
    r"Spark", r"Kafka", r"Airflow", r"MLflow",
    # Evaluation
    r"evaluation", r"metric", r"NDCG", r"MAP", r"MRR",
    r"A/B\s+test", r"benchmark",
    # Data
    r"data\s+engineer", r"data\s+pipeline", r"ETL",
    r"data\s+warehouse", r"Snowflake", r"dbt",
]


class JDIntelligenceEngine:
    """
    Dynamic Job Description Intelligence Engine.
    Transforms an unstructured JD into a structured HiringProfile.
    """

    def __init__(self, embedding_model=None):
        self.embedding_model = embedding_model
        self._hiring_profile: Optional[HiringProfile] = None

    def analyze(self, jd_path: str = None) -> HiringProfile:
        """
        Complete JD analysis pipeline.
        Returns an immutable HiringProfile.
        """
        with Timer("JD Intelligence Engine"):
            # Step 1: Load document
            if jd_path is None:
                jd_path = get_data_path("job_description.docx")
            jd_data = load_jd_from_docx(jd_path)

            if not jd_data["raw_text"]:
                logger.warning("Empty JD document, returning default profile")
                return HiringProfile()

            # Step 2: Extract competencies
            required, preferred = self._extract_competencies(jd_data)

            # Step 3: Extract semantic concepts
            concepts = self._extract_concepts(jd_data)

            # Step 4: Estimate priorities
            priorities = self._estimate_priorities(required, preferred, jd_data)

            # Step 5: Extract constraints
            constraints = self._extract_constraints(jd_data)

            # Step 6: Detect hiring philosophy
            philosophy = self._detect_philosophy(jd_data)

            # Step 7: Extract experience expectations
            experience = self._extract_experience(jd_data)

            # Step 8: Extract role metadata
            role_meta = self._extract_role_metadata(jd_data)

            # Step 9: Extract behavioral expectations
            behavioral = self._extract_behavioral_expectations(jd_data)

            # Step 10: Extract disqualifiers
            disqualifiers = self._extract_disqualifiers(jd_data)

            # Step 11: Compute JD embeddings
            jd_embeddings = self._compute_embeddings(jd_data)

            # Step 12: Compute feature importance
            feature_importance = self._compute_feature_importance(
                required, preferred, philosophy, constraints
            )

            # Build the HiringProfile
            profile = HiringProfile(
                required_competencies=required,
                preferred_competencies=preferred,
                semantic_concepts=concepts,
                jd_embeddings=jd_embeddings,
                jd_full_text=jd_data["raw_text"],
                jd_sections=jd_data["sections"],
                hiring_constraints=constraints,
                hiring_philosophy=philosophy,
                experience_expectation=experience,
                role_metadata=role_meta,
                feature_importance=feature_importance,
                competency_priorities=priorities,
                behavioral_expectations=behavioral,
                disqualifiers=disqualifiers,
            )

            self._hiring_profile = profile
            logger.info(
                f"HiringProfile built: {len(required)} required, "
                f"{len(preferred)} preferred competencies, "
                f"{len(concepts)} semantic concepts"
            )
            return profile

    def _extract_competencies(self, jd_data: dict) -> tuple[list[Competency], list[Competency]]:
        """Extract required and preferred competencies from JD."""
        required = []
        preferred = []
        text = jd_data["raw_text"].lower()
        sections = jd_data.get("sections", {})

        # Find skills mentioned in the JD
        found_skills = set()
        for pattern in TECH_SKILL_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                skill = match.strip()
                if skill and len(skill) > 1:
                    found_skills.add(skill)

        # Classify each skill based on context
        for skill in found_skills:
            # Check if in required sections
            is_required = False
            is_preferred = False
            source_section = ""

            for section_name, section_text in sections.items():
                section_lower = section_text.lower()
                name_lower = section_name.lower()

                if skill.lower() in section_lower:
                    source_section = section_name

                    # Check section name for classification hints
                    if any(kw in name_lower for kw in ["required", "must", "essential", "responsibilities"]):
                        is_required = True
                    elif any(kw in name_lower for kw in ["preferred", "nice", "bonus", "plus"]):
                        is_preferred = True
                    else:
                        # Check surrounding context
                        for pat in REQUIREMENT_PATTERNS:
                            if re.search(pat, section_lower):
                                is_required = True
                                break
                        if not is_required:
                            for pat in PREFERRED_PATTERNS:
                                if re.search(pat, section_lower):
                                    is_preferred = True
                                    break

            # Default to required if not clearly preferred
            if not is_required and not is_preferred:
                is_required = True

            # Count frequency as proxy for importance
            freq = text.count(skill.lower())
            importance = min(1.0, freq * 0.15)  # Scale based on frequency

            comp = Competency(
                name=skill,
                category="mandatory" if is_required else "preferred",
                importance=importance,
                section_source=source_section,
            )

            if is_required:
                required.append(comp)
            else:
                preferred.append(comp)

        # Sort by importance
        required.sort(key=lambda c: c.importance, reverse=True)
        preferred.sort(key=lambda c: c.importance, reverse=True)

        logger.info(f"Extracted {len(required)} required, {len(preferred)} preferred competencies")
        return required, preferred

    def _extract_concepts(self, jd_data: dict) -> list[SemanticConcept]:
        """Extract semantic concepts from JD."""
        concepts = []
        text = jd_data["raw_text"]
        sentences = extract_sentences(text)

        # Group related concepts
        concept_clusters = {
            "retrieval_engineering": {
                "primary": "Retrieval Engineering",
                "terms": ["retrieval", "search", "vector", "embedding", "ranking",
                          "semantic search", "information retrieval", "FAISS", "Pinecone"],
            },
            "llm_engineering": {
                "primary": "LLM Engineering",
                "terms": ["LLM", "language model", "transformer", "GPT", "fine-tuning",
                          "prompt engineering", "RAG", "LangChain"],
            },
            "production_ml": {
                "primary": "Production ML",
                "terms": ["production", "deployment", "MLOps", "monitoring",
                          "evaluation", "A/B testing", "infrastructure"],
            },
            "data_engineering": {
                "primary": "Data Engineering",
                "terms": ["data pipeline", "ETL", "Spark", "Kafka", "Airflow",
                          "data warehouse", "streaming"],
            },
            "software_engineering": {
                "primary": "Software Engineering",
                "terms": ["Python", "API", "microservices", "Docker", "Kubernetes",
                          "CI/CD", "testing", "code quality"],
            },
        }

        text_lower = text.lower()
        for key, cluster in concept_clusters.items():
            # Check how many terms are present
            present_terms = [
                t for t in cluster["terms"]
                if t.lower() in text_lower
            ]
            if present_terms:
                importance = min(1.0, len(present_terms) / len(cluster["terms"]))
                concepts.append(SemanticConcept(
                    primary_term=cluster["primary"],
                    related_terms=present_terms,
                    importance=importance,
                ))

        concepts.sort(key=lambda c: c.importance, reverse=True)
        return concepts

    def _estimate_priorities(
        self,
        required: list[Competency],
        preferred: list[Competency],
        jd_data: dict
    ) -> dict[str, float]:
        """Dynamically estimate competency priorities."""
        priorities = {}
        text_lower = jd_data["raw_text"].lower()

        for comp in required + preferred:
            # Factors: frequency, section importance, category
            freq = text_lower.count(comp.name.lower())
            category_weight = 1.5 if comp.category == "mandatory" else 1.0
            priority = min(1.0, (freq * 0.1 * category_weight))
            priorities[comp.name] = max(0.1, priority)

        # Normalize priorities to sum to 1
        total = sum(priorities.values())
        if total > 0:
            priorities = {k: v / total for k, v in priorities.items()}

        return priorities

    def _extract_constraints(self, jd_data: dict) -> list[HiringConstraint]:
        """Extract explicit hiring constraints."""
        constraints = []
        text = jd_data["raw_text"].lower()

        # Experience constraints
        exp_match = re.search(r"(\d+)\+?\s*(?:to\s+(\d+))?\s*years?", text)
        if exp_match:
            constraints.append(HiringConstraint(
                name="experience_years",
                value=exp_match.group(0),
                constraint_type="requirement",
            ))

        # Location constraints
        for keyword in ["remote", "hybrid", "onsite", "on-site", "in-office"]:
            if keyword in text:
                constraints.append(HiringConstraint(
                    name="work_mode",
                    value=keyword,
                    constraint_type="preference",
                ))

        # Production experience
        if "production" in text:
            constraints.append(HiringConstraint(
                name="production_experience",
                value="required",
                constraint_type="requirement",
            ))

        return constraints

    def _detect_philosophy(self, jd_data: dict) -> list[HiringPhilosophy]:
        """Detect latent hiring philosophy dimensions."""
        philosophy = []
        text = jd_data["raw_text"].lower()

        for dimension, patterns in PHILOSOPHY_PATTERNS.items():
            matches = sum(
                len(re.findall(p, text, re.IGNORECASE))
                for p in patterns
            )
            if matches > 0:
                strength = min(1.0, matches * 0.15)
                philosophy.append(HiringPhilosophy(
                    dimension=dimension,
                    strength=strength,
                ))

        philosophy.sort(key=lambda p: p.strength, reverse=True)
        return philosophy

    def _extract_experience(self, jd_data: dict) -> ExperienceExpectation:
        """Extract experience expectations from JD."""
        text = jd_data["raw_text"]
        exp = ExperienceExpectation()

        # Find year ranges
        patterns = [
            r"(\d+)\s*[-–]\s*(\d+)\s*years?",
            r"(\d+)\+\s*years?",
            r"at\s+least\s+(\d+)\s*years?",
            r"minimum\s+(\d+)\s*years?",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2 and groups[1]:
                    exp.min_years = float(groups[0])
                    exp.max_years = float(groups[1])
                    exp.preferred_years = (exp.min_years + exp.max_years) / 2
                elif groups[0]:
                    exp.min_years = float(groups[0])
                    exp.preferred_years = exp.min_years + 2
                break

        # Detect seniority
        text_lower = text.lower()
        if "senior" in text_lower or "sr." in text_lower:
            exp.seniority_level = "senior"
        elif "lead" in text_lower or "principal" in text_lower:
            exp.seniority_level = "lead"
        elif "junior" in text_lower or "entry" in text_lower:
            exp.seniority_level = "junior"
        else:
            exp.seniority_level = "mid"

        return exp

    def _extract_role_metadata(self, jd_data: dict) -> RoleMetadata:
        """Extract role metadata."""
        text = jd_data["raw_text"]
        sections = jd_data.get("sections", {})

        meta = RoleMetadata()

        # Try to find title from first heading or section
        for para in jd_data.get("paragraphs", []):
            if para.get("type") == "heading":
                meta.title = para["text"]
                break

        # Detect work mode
        text_lower = text.lower()
        if "remote" in text_lower:
            meta.work_mode = "remote"
        elif "hybrid" in text_lower:
            meta.work_mode = "hybrid"
        elif "onsite" in text_lower or "on-site" in text_lower:
            meta.work_mode = "onsite"

        return meta

    def _extract_behavioral_expectations(self, jd_data: dict) -> list[str]:
        """Extract behavioral expectations from JD."""
        expectations = []
        text_lower = jd_data["raw_text"].lower()

        behavioral_terms = {
            "collaboration": ["collaborat", "team", "cross-functional"],
            "communication": ["communicat", "present", "articulate"],
            "ownership": ["ownership", "autonomous", "self-driven", "initiative"],
            "learning": ["learn", "curios", "growth mindset"],
            "problem_solving": ["problem solving", "analytical", "critical thinking"],
        }

        for term, patterns in behavioral_terms.items():
            if any(p in text_lower for p in patterns):
                expectations.append(term)

        return expectations

    def _extract_disqualifiers(self, jd_data: dict) -> list[str]:
        """Extract explicit disqualifiers from JD."""
        disqualifiers = []
        text = jd_data["raw_text"].lower()

        for pattern in DISQUALIFIER_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                # Get surrounding context
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 100)
                context = text[start:end].strip()
                disqualifiers.append(context)

        return disqualifiers

    def _compute_embeddings(self, jd_data: dict) -> list[list[float]]:
        """Compute JD sentence embeddings."""
        if self.embedding_model is None:
            return []

        sentences = extract_sentences(jd_data["raw_text"])
        if not sentences:
            return []

        try:
            embeddings = self.embedding_model.encode(
                sentences,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.warning(f"Failed to compute JD embeddings: {e}")
            return []

    def _compute_feature_importance(
        self,
        required: list[Competency],
        preferred: list[Competency],
        philosophy: list[HiringPhilosophy],
        constraints: list[HiringConstraint],
    ) -> dict[str, float]:
        """Compute dynamic feature importance for the ranking engine."""
        importance = {
            "technical_alignment": 0.25,
            "semantic_relevance": 0.20,
            "evidence_strength": 0.20,
            "authenticity": 0.10,
            "career_narrative": 0.10,
            "behavioral": 0.08,
            "recruitability": 0.07,
        }

        # Adjust based on philosophy
        for phil in philosophy:
            if phil.dimension == "production_experience" and phil.strength > 0.5:
                importance["evidence_strength"] += 0.05
                importance["technical_alignment"] += 0.03
            if phil.dimension == "startup_adaptability" and phil.strength > 0.5:
                importance["career_narrative"] += 0.03
                importance["behavioral"] += 0.02

        # Normalize to sum to 1
        total = sum(importance.values())
        return {k: v / total for k, v in importance.items()}

    @property
    def hiring_profile(self) -> Optional[HiringProfile]:
        """Get the cached hiring profile."""
        return self._hiring_profile
