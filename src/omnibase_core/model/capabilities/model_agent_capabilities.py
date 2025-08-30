"""
Model for agent capabilities and skill matching.

This model represents agent capabilities, skill proficiencies,
and matching algorithms for intelligent work assignment in
multi-agent Claude Code environments.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SkillLevel(str, Enum):
    """Skill proficiency levels."""

    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class CapabilityType(str, Enum):
    """Types of agent capabilities."""

    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    TOOL = "tool"
    DOMAIN_KNOWLEDGE = "domain_knowledge"
    METHODOLOGY = "methodology"
    PLATFORM = "platform"
    DATABASE = "database"
    PROTOCOL = "protocol"
    ARCHITECTURE = "architecture"
    TESTING = "testing"


class MatchingAlgorithm(str, Enum):
    """Algorithms for capability matching."""

    EXACT_MATCH = "exact_match"
    FUZZY_MATCH = "fuzzy_match"
    WEIGHTED_SCORE = "weighted_score"
    MACHINE_LEARNING = "machine_learning"
    HYBRID = "hybrid"


class ModelSkillProficiency(BaseModel):
    """Model for individual skill proficiency."""

    skill_name: str = Field(description="Name of the skill")
    skill_type: CapabilityType = Field(description="Type/category of the skill")
    level: SkillLevel = Field(description="Proficiency level for this skill")
    confidence_score: float = Field(
        default=1.0, description="Confidence in the proficiency assessment (0.0-1.0)"
    )
    experience_years: Optional[float] = Field(
        default=None, description="Years of experience with this skill"
    )
    last_used: Optional[datetime] = Field(
        default=None, description="When this skill was last used"
    )
    usage_frequency: int = Field(
        default=0, description="Number of times this skill has been used"
    )
    success_rate: float = Field(
        default=1.0, description="Success rate when using this skill (0.0-1.0)"
    )
    learning_curve: float = Field(
        default=0.0, description="Rate of improvement in this skill"
    )
    related_skills: List[str] = Field(
        default_factory=list, description="List of related skill names"
    )
    certifications: List[str] = Field(
        default_factory=list, description="Relevant certifications for this skill"
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Evidence of proficiency (projects, tickets, etc.)",
    )
    metadata: Optional[Dict[str, str]] = Field(
        default=None, description="Additional metadata about the skill"
    )

    @property
    def proficiency_score(self) -> float:
        """Calculate normalized proficiency score (0.0-1.0)."""
        level_scores = {
            SkillLevel.NOVICE: 0.2,
            SkillLevel.BEGINNER: 0.4,
            SkillLevel.INTERMEDIATE: 0.6,
            SkillLevel.ADVANCED: 0.8,
            SkillLevel.EXPERT: 1.0,
        }

        base_score = level_scores.get(self.level, 0.6)

        # Adjust based on confidence and success rate
        adjusted_score = base_score * self.confidence_score * self.success_rate

        return min(1.0, max(0.0, adjusted_score))

    @property
    def is_current(self) -> bool:
        """Check if skill knowledge is current (used recently)."""
        if not self.last_used:
            return True  # Assume current if never used

        # Skills are considered current if used within last 6 months
        return datetime.now() - self.last_used < timedelta(days=180)

    @property
    def experience_weight(self) -> float:
        """Calculate experience-based weight."""
        if not self.experience_years:
            return 1.0

        # Experience weight increases logarithmically
        import math

        return min(2.0, 1.0 + math.log(self.experience_years + 1) / 10)

    def update_usage(self, success: bool = True) -> None:
        """Update skill usage statistics."""
        self.usage_frequency += 1
        self.last_used = datetime.now()

        # Update success rate with exponential moving average
        if self.usage_frequency == 1:
            self.success_rate = 1.0 if success else 0.0
        else:
            alpha = 0.1  # Learning rate
            new_success = 1.0 if success else 0.0
            self.success_rate = alpha * new_success + (1 - alpha) * self.success_rate

    def calculate_match_score(
        self, required_level: SkillLevel, importance_weight: float = 1.0
    ) -> float:
        """Calculate match score for a required skill level."""
        required_scores = {
            SkillLevel.NOVICE: 0.2,
            SkillLevel.BEGINNER: 0.4,
            SkillLevel.INTERMEDIATE: 0.6,
            SkillLevel.ADVANCED: 0.8,
            SkillLevel.EXPERT: 1.0,
        }

        required_score = required_scores.get(required_level, 0.6)

        # Calculate match based on proficiency
        if self.proficiency_score >= required_score:
            # Over-qualified bonus
            bonus = min(0.2, (self.proficiency_score - required_score) * 0.5)
            match_score = 1.0 + bonus
        else:
            # Under-qualified penalty
            match_score = self.proficiency_score / required_score

        # Apply experience weight and importance
        final_score = match_score * self.experience_weight * importance_weight

        # Penalty for stale skills
        if not self.is_current:
            final_score *= 0.8

        return min(2.0, max(0.0, final_score))


class ModelWorkRequirement(BaseModel):
    """Model for work requirements and skill needs."""

    requirement_id: str = Field(description="Unique identifier for the requirement")
    required_skills: Dict[str, SkillLevel] = Field(
        description="Required skills and their minimum levels"
    )
    optional_skills: Dict[str, SkillLevel] = Field(
        default_factory=dict, description="Optional skills that would be beneficial"
    )
    skill_weights: Dict[str, float] = Field(
        default_factory=dict, description="Importance weights for each skill (0.0-1.0)"
    )
    complexity_level: SkillLevel = Field(
        description="Overall complexity level of the work"
    )
    estimated_duration: Optional[float] = Field(
        default=None, description="Estimated duration in hours"
    )
    domain_context: List[str] = Field(
        default_factory=list, description="Domain contexts relevant to the work"
    )
    tools_required: List[str] = Field(
        default_factory=list, description="Specific tools required for the work"
    )
    platforms_supported: List[str] = Field(
        default_factory=list, description="Platforms this work should support"
    )
    quality_requirements: Dict[str, float] = Field(
        default_factory=dict,
        description="Quality requirements (testing, documentation, etc.)",
    )
    collaboration_needs: bool = Field(
        default=False, description="Whether the work requires collaboration"
    )
    learning_opportunity: bool = Field(
        default=False, description="Whether this work offers learning opportunities"
    )
    urgency_level: int = Field(
        default=1, description="Urgency level (1-5, higher is more urgent)"
    )
    metadata: Optional[Dict[str, str]] = Field(
        default=None, description="Additional requirement metadata"
    )

    @property
    def total_skill_count(self) -> int:
        """Get total number of required and optional skills."""
        return len(self.required_skills) + len(self.optional_skills)

    @property
    def has_high_complexity(self) -> bool:
        """Check if work has high complexity requirements."""
        return self.complexity_level in [SkillLevel.ADVANCED, SkillLevel.EXPERT]

    def get_skill_weight(self, skill_name: str) -> float:
        """Get importance weight for a skill."""
        return self.skill_weights.get(skill_name, 1.0)

    def is_skill_required(self, skill_name: str) -> bool:
        """Check if a skill is required (vs optional)."""
        return skill_name in self.required_skills


class ModelAgentCapabilities(BaseModel):
    """Model for comprehensive agent capabilities."""

    agent_id: str = Field(description="Unique identifier for the agent")
    agent_name: str = Field(description="Human-readable name for the agent")
    skills: Dict[str, ModelSkillProficiency] = Field(
        default_factory=dict, description="Dictionary of skills by skill name"
    )
    specializations: List[str] = Field(
        default_factory=list, description="Areas of specialization"
    )
    preferred_work_types: List[str] = Field(
        default_factory=list, description="Types of work this agent prefers"
    )
    avoided_work_types: List[str] = Field(
        default_factory=list, description="Types of work this agent should avoid"
    )
    learning_preferences: List[str] = Field(
        default_factory=list, description="Skills the agent is interested in learning"
    )
    availability_hours: Optional[Dict[str, str]] = Field(
        default=None, description="Availability schedule"
    )
    timezone: Optional[str] = Field(default=None, description="Agent's timezone")
    workload_capacity: float = Field(
        default=1.0,
        description="Relative workload capacity (0.5 = half capacity, 2.0 = double)",
    )
    performance_history: Dict[str, float] = Field(
        default_factory=dict, description="Historical performance metrics"
    )
    collaboration_score: float = Field(
        default=1.0,
        description="How well the agent works in collaborative environments",
    )
    adaptability_score: float = Field(
        default=1.0, description="How well the agent adapts to new technologies"
    )
    reliability_score: float = Field(
        default=1.0, description="Reliability score based on past performance"
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When the capability profile was created",
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="When the profile was last updated"
    )
    last_assessment: Optional[datetime] = Field(
        default=None, description="When capabilities were last assessed"
    )

    @property
    def skill_count(self) -> int:
        """Get total number of skills."""
        return len(self.skills)

    @property
    def expert_skills(self) -> List[str]:
        """Get list of expert-level skills."""
        return [
            name
            for name, skill in self.skills.items()
            if skill.level == SkillLevel.EXPERT
        ]

    @property
    def primary_capabilities(self) -> List[str]:
        """Get primary capabilities (advanced+ skills)."""
        return [
            name
            for name, skill in self.skills.items()
            if skill.level in [SkillLevel.ADVANCED, SkillLevel.EXPERT]
        ]

    @property
    def overall_skill_level(self) -> float:
        """Calculate overall skill level score."""
        if not self.skills:
            return 0.0

        total_score = sum(skill.proficiency_score for skill in self.skills.values())
        return total_score / len(self.skills)

    @property
    def is_assessment_current(self) -> bool:
        """Check if capability assessment is current."""
        if not self.last_assessment:
            return False
        return datetime.now() - self.last_assessment < timedelta(days=90)

    def has_skill(
        self, skill_name: str, min_level: SkillLevel = SkillLevel.BEGINNER
    ) -> bool:
        """Check if agent has a skill at minimum level."""
        if skill_name not in self.skills:
            return False

        skill = self.skills[skill_name]
        level_order = [
            SkillLevel.NOVICE,
            SkillLevel.BEGINNER,
            SkillLevel.INTERMEDIATE,
            SkillLevel.ADVANCED,
            SkillLevel.EXPERT,
        ]

        return level_order.index(skill.level) >= level_order.index(min_level)

    def get_skill_score(self, skill_name: str) -> float:
        """Get proficiency score for a specific skill."""
        if skill_name in self.skills:
            return self.skills[skill_name].proficiency_score
        return 0.0

    def add_skill(self, skill: ModelSkillProficiency) -> None:
        """Add or update a skill."""
        self.skills[skill.skill_name] = skill
        self.last_updated = datetime.now()

    def remove_skill(self, skill_name: str) -> bool:
        """Remove a skill from the agent's capabilities."""
        if skill_name in self.skills:
            del self.skills[skill_name]
            self.last_updated = datetime.now()
            return True
        return False

    def update_skill_usage(self, skill_name: str, success: bool = True) -> None:
        """Update usage statistics for a skill."""
        if skill_name in self.skills:
            self.skills[skill_name].update_usage(success)
            self.last_updated = datetime.now()

    def calculate_match_score(self, requirements: ModelWorkRequirement) -> float:
        """Calculate how well this agent matches work requirements."""
        if not requirements.required_skills and not requirements.optional_skills:
            return 1.0

        total_score = 0.0
        total_weight = 0.0
        missing_required = 0

        # Check required skills
        for skill_name, required_level in requirements.required_skills.items():
            weight = requirements.get_skill_weight(skill_name)
            total_weight += weight

            if skill_name in self.skills:
                skill_score = self.skills[skill_name].calculate_match_score(
                    required_level, weight
                )
                total_score += skill_score
            else:
                missing_required += 1
                # Penalty for missing required skills
                total_score += 0.0

        # Check optional skills (bonus points)
        optional_bonus = 0.0
        for skill_name, preferred_level in requirements.optional_skills.items():
            if skill_name in self.skills:
                weight = (
                    requirements.get_skill_weight(skill_name) * 0.5
                )  # Less weight for optional
                skill_score = self.skills[skill_name].calculate_match_score(
                    preferred_level, weight
                )
                optional_bonus += skill_score * 0.2  # 20% bonus for optional skills

        # Calculate base match score
        if total_weight > 0:
            base_score = total_score / total_weight
        else:
            base_score = 1.0

        # Apply penalties and bonuses
        final_score = base_score + optional_bonus

        # Heavy penalty for missing required skills
        if missing_required > 0:
            penalty = missing_required * 0.3
            final_score = max(0.0, final_score - penalty)

        # Complexity bonus/penalty
        complexity_factor = 1.0
        if requirements.has_high_complexity:
            if self.overall_skill_level > 0.8:
                complexity_factor = 1.2  # Bonus for high-skill agents on complex work
            else:
                complexity_factor = 0.8  # Penalty for low-skill agents on complex work

        final_score *= complexity_factor

        # Performance factors
        final_score *= self.reliability_score

        if requirements.collaboration_needs:
            final_score *= self.collaboration_score

        return min(2.0, max(0.0, final_score))

    def get_learning_opportunities(
        self, requirements: ModelWorkRequirement
    ) -> List[str]:
        """Identify learning opportunities from work requirements."""
        opportunities = []

        # Skills not currently possessed
        for skill_name in requirements.required_skills:
            if skill_name not in self.skills:
                if skill_name in self.learning_preferences:
                    opportunities.append(f"Learn new skill: {skill_name}")

        # Skills that could be improved
        for skill_name, required_level in requirements.required_skills.items():
            if skill_name in self.skills:
                current_skill = self.skills[skill_name]
                level_order = [
                    SkillLevel.NOVICE,
                    SkillLevel.BEGINNER,
                    SkillLevel.INTERMEDIATE,
                    SkillLevel.ADVANCED,
                    SkillLevel.EXPERT,
                ]

                current_index = level_order.index(current_skill.level)
                required_index = level_order.index(required_level)

                if required_index > current_index:
                    opportunities.append(
                        f"Improve {skill_name} from {current_skill.level.value} to {required_level.value}"
                    )

        return opportunities

    def suggest_skill_development(self) -> List[str]:
        """Suggest skills for development based on current profile."""
        suggestions = []

        # Skills with low proficiency that are used frequently
        for skill_name, skill in self.skills.items():
            if skill.proficiency_score < 0.6 and skill.usage_frequency > 5:
                suggestions.append(f"Improve frequently used skill: {skill_name}")

        # Related skills to existing expertise
        expert_skills = self.expert_skills
        for expert_skill in expert_skills:
            if expert_skill in self.skills:
                related = self.skills[expert_skill].related_skills
                for related_skill in related:
                    if related_skill not in self.skills:
                        suggestions.append(
                            f"Learn related skill: {related_skill} (complements {expert_skill})"
                        )

        return suggestions[:5]  # Limit to top 5 suggestions


class ModelCapabilityMatch(BaseModel):
    """Model for capability matching results."""

    match_id: str = Field(description="Unique identifier for the match")
    agent_id: str = Field(description="ID of the matched agent")
    requirement_id: str = Field(description="ID of the work requirement")
    overall_score: float = Field(description="Overall match score (0.0-2.0)")
    confidence: float = Field(description="Confidence in the match (0.0-1.0)")
    skill_matches: Dict[str, float] = Field(
        default_factory=dict, description="Individual skill match scores"
    )
    missing_skills: List[str] = Field(
        default_factory=list, description="Required skills the agent doesn't have"
    )
    bonus_skills: List[str] = Field(
        default_factory=list, description="Optional skills the agent possesses"
    )
    learning_opportunities: List[str] = Field(
        default_factory=list, description="Learning opportunities for the agent"
    )
    risk_factors: List[str] = Field(
        default_factory=list, description="Potential risk factors for the match"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for the match"
    )
    estimated_success_probability: float = Field(
        default=0.5, description="Estimated probability of successful completion"
    )
    estimated_completion_time: Optional[float] = Field(
        default=None, description="Estimated completion time in hours"
    )
    match_timestamp: datetime = Field(
        default_factory=datetime.now, description="When the match was calculated"
    )
    algorithm_used: MatchingAlgorithm = Field(
        default=MatchingAlgorithm.WEIGHTED_SCORE,
        description="Algorithm used for matching",
    )

    @property
    def is_good_match(self) -> bool:
        """Check if this is considered a good match."""
        return self.overall_score >= 0.8 and len(self.missing_skills) == 0

    @property
    def is_acceptable_match(self) -> bool:
        """Check if this is an acceptable match."""
        return self.overall_score >= 0.6

    @property
    def has_risks(self) -> bool:
        """Check if the match has risk factors."""
        return len(self.risk_factors) > 0 or len(self.missing_skills) > 0

    @property
    def match_quality(self) -> str:
        """Get qualitative match quality assessment."""
        if self.overall_score >= 1.5:
            return "excellent"
        elif self.overall_score >= 1.2:
            return "very_good"
        elif self.overall_score >= 0.8:
            return "good"
        elif self.overall_score >= 0.6:
            return "acceptable"
        else:
            return "poor"


class ModelCapabilityAssessment(BaseModel):
    """Model for capability assessment results."""

    assessment_id: str = Field(description="Unique identifier for the assessment")
    agent_id: str = Field(description="ID of the assessed agent")
    assessment_type: str = Field(
        description="Type of assessment (initial, periodic, performance-based)"
    )
    skills_assessed: List[str] = Field(description="List of skills that were assessed")
    assessment_results: Dict[str, Dict[str, float]] = Field(
        default_factory=dict, description="Assessment results by skill"
    )
    overall_competency: float = Field(description="Overall competency score (0.0-1.0)")
    strength_areas: List[str] = Field(
        default_factory=list, description="Identified strength areas"
    )
    improvement_areas: List[str] = Field(
        default_factory=list, description="Areas needing improvement"
    )
    learning_recommendations: List[str] = Field(
        default_factory=list, description="Recommended learning paths"
    )
    assessment_confidence: float = Field(
        description="Confidence in the assessment results"
    )
    assessor: str = Field(description="Who or what performed the assessment")
    assessment_date: datetime = Field(
        default_factory=datetime.now, description="When the assessment was performed"
    )
    next_assessment_due: Optional[datetime] = Field(
        default=None, description="When the next assessment is due"
    )
    assessment_methodology: str = Field(description="Methodology used for assessment")
    evidence_sources: List[str] = Field(
        default_factory=list, description="Sources of evidence used in assessment"
    )

    @property
    def is_current(self) -> bool:
        """Check if assessment is still current."""
        return datetime.now() - self.assessment_date < timedelta(days=90)

    @property
    def needs_update(self) -> bool:
        """Check if assessment needs updating."""
        if self.next_assessment_due:
            return datetime.now() > self.next_assessment_due
        return not self.is_current
