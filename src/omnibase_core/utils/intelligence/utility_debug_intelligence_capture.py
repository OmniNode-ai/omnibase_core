"""Debug Intelligence Capture Utility for Agents.

This utility enables agents to automatically capture their problem-solving process
and query historical solutions from other agents.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.exceptions import OnexError
from omnibase_core.model.intelligence.model_agent_debug_intelligence import (
    EnumAgentType, EnumProblemType, EnumSolutionEffectiveness,
    ModelAgentDebugIntelligence, ModelDebugIntelligenceQuery,
    ModelDebugIntelligenceResult, ModelProblemContext, ModelSolutionApproach,
    ModelSolutionOutcome)

logger = logging.getLogger(__name__)


class UtilityDebugIntelligenceCapture:
    """Utility for capturing and querying agent debug intelligence."""

    def __init__(
        self, agent_name: str, agent_type: EnumAgentType, agent_version: str = "1.0.0"
    ):
        """Initialize debug intelligence capture for an agent.

        Args:
            agent_name: Name of the agent
            agent_type: Type/category of the agent
            agent_version: Version of the agent
        """
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.agent_version = agent_version
        self.current_session_id = uuid4()

        # In future, this will connect to actual database/RAG service
        # For now, we'll use in-memory storage as foundation
        self._debug_entries: List[ModelAgentDebugIntelligence] = []

        logger.info(
            "Debug intelligence capture initialized",
            extra={
                "agent_name": agent_name,
                "agent_type": agent_type.value,
                "session_id": str(self.current_session_id),
            },
        )

    def start_problem_solving(
        self,
        problem_description: str,
        problem_type: EnumProblemType,
        context: Optional[Dict[str, Union[str, int, float, bool, List[str]]]] = None,
    ) -> UUID:
        """Start tracking a problem-solving session.

        Args:
            problem_description: Clear description of the problem
            problem_type: Classification of the problem type
            context: Additional context information

        Returns:
            UUID: Problem tracking ID
        """
        problem_id = uuid4()

        logger.info(
            "Problem solving session started",
            extra={
                "agent_name": self.agent_name,
                "problem_id": str(problem_id),
                "problem_type": problem_type.value,
                "problem_description": (
                    problem_description[:100] + "..."
                    if len(problem_description) > 100
                    else problem_description
                ),
            },
        )

        return problem_id

    def query_similar_problems(
        self,
        problem_description: str,
        problem_type: Optional[EnumProblemType] = None,
        subsystem: Optional[str] = None,
        limit: int = 5,
        offset: int = 0,
        min_similarity_score: float = 0.5,
    ) -> List[ModelDebugIntelligenceResult]:
        """Query for similar problems solved by other agents.

        Args:
            problem_description: Description of current problem
            problem_type: Optional problem type filter
            subsystem: Optional subsystem filter
            limit: Maximum number of results per page
            offset: Number of results to skip (for pagination)
            min_similarity_score: Minimum similarity score threshold

        Returns:
            List of similar debug intelligence entries
        """
        query = ModelDebugIntelligenceQuery(
            problem_description=problem_description,
            problem_type=problem_type,
            agent_type=None,  # Don't filter by agent type - learn from all agents
            subsystem=subsystem,
            min_effectiveness=EnumSolutionEffectiveness.EFFECTIVE,
            min_reusability_score=0.6,
            limit=limit,
        )

        # TODO: Replace with actual RAG/database query
        # For now, return empty results as foundation
        similar_solutions = self._simulate_similarity_search(
            query, offset, min_similarity_score
        )

        logger.debug(
            "Queried similar problems",
            extra={
                "agent_name": self.agent_name,
                "query_problem": (
                    problem_description[:50] + "..."
                    if len(problem_description) > 50
                    else problem_description
                ),
                "results_count": len(similar_solutions),
                "problem_type": problem_type.value if problem_type else "any",
            },
        )

        return similar_solutions

    def capture_solution(
        self,
        problem_id: UUID,
        problem_description: str,
        problem_type: EnumProblemType,
        solution_strategy: str,
        solution_steps: List[str],
        effectiveness: EnumSolutionEffectiveness,
        success_indicators: List[str],
        context: Optional[Dict[str, Union[str, int, float, bool, List[str]]]] = None,
        tools_used: Optional[List[str]] = None,
        time_to_solution_minutes: Optional[int] = None,
        lessons_learned: Optional[List[str]] = None,
        confidence_level: float = 0.8,
        reusability_score: float = 0.7,
    ) -> ModelAgentDebugIntelligence:
        """Capture a complete problem-solution pair for future learning.

        Args:
            problem_id: UUID from start_problem_solving
            problem_description: Description of the problem that was solved
            problem_type: Type of problem that was solved
            solution_strategy: High-level strategy used to solve
            solution_steps: Specific steps taken
            effectiveness: How effective the solution was
            success_indicators: How success was measured
            context: Additional context about the problem
            tools_used: Tools or utilities used in the solution
            time_to_solution_minutes: How long it took to solve
            lessons_learned: Key insights from solving this problem
            confidence_level: Agent's confidence in this solution (0.0-1.0)
            reusability_score: How reusable this solution is (0.0-1.0)

        Returns:
            The created debug intelligence entry
        """
        try:
            # Build problem context
            problem_context = ModelProblemContext(
                subsystem=context.get("subsystem") if context else None,
                component=context.get("component") if context else None,
                operation=context.get("operation") if context else None,
                input_data=(
                    self._sanitize_data(context.get("input_data")) if context else None
                ),
                error_messages=context.get("error_messages") if context else None,
                stack_trace=context.get("stack_trace") if context else None,
                environment=context.get("environment") if context else None,
                dependencies=context.get("dependencies") if context else None,
                user_context=context.get("user_context") if context else None,
            )

            # Build solution approach
            solution_approach = ModelSolutionApproach(
                strategy=solution_strategy,
                steps=solution_steps,
                tools_used=tools_used or [],
                time_to_solution=time_to_solution_minutes,
            )

            # Build solution outcome
            solution_outcome = ModelSolutionOutcome(
                effectiveness=effectiveness,
                success_indicators=success_indicators,
                lessons_learned=lessons_learned or [],
            )

            # Create debug intelligence entry
            now = datetime.utcnow()
            debug_entry = ModelAgentDebugIntelligence(
                entry_id=uuid4(),
                agent_name=self.agent_name,
                agent_type=self.agent_type,
                agent_version=self.agent_version,
                problem_type=problem_type,
                problem_description=problem_description,
                problem_context=problem_context,
                solution_approach=solution_approach,
                solution_outcome=solution_outcome,
                confidence_level=confidence_level,
                reusability_score=reusability_score,
                problem_occurred_at=now
                - timedelta(minutes=time_to_solution_minutes or 5),
                solution_completed_at=now,
                correlation_id=self.current_session_id,
                tags=self._generate_tags(problem_description, problem_type, context),
            )

            # Store the entry (TODO: Replace with actual database storage)
            self._debug_entries.append(debug_entry)

            logger.info(
                "Debug intelligence captured",
                extra={
                    "agent_name": self.agent_name,
                    "problem_id": str(problem_id),
                    "entry_id": str(debug_entry.entry_id),
                    "problem_type": problem_type.value,
                    "effectiveness": effectiveness.value,
                    "confidence_level": confidence_level,
                    "reusability_score": reusability_score,
                },
            )

            # TODO: Store in actual database and update RAG index
            self._store_in_database(debug_entry)

            return debug_entry

        except Exception as e:
            logger.error(
                "Failed to capture debug intelligence",
                extra={
                    "agent_name": self.agent_name,
                    "problem_id": str(problem_id),
                    "error_message": str(e),
                },
                exc_info=True,
            )

            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to capture debug intelligence: {str(e)}",
                context={"agent_name": self.agent_name, "problem_id": str(problem_id)},
            ) from e

    def get_agent_statistics(
        self,
    ) -> Dict[str, Union[int, float, str, List[str], Dict[str, int]]]:
        """Get statistics about this agent's debug intelligence contributions.

        Returns:
            Dictionary with agent debug statistics
        """
        agent_entries = [
            entry
            for entry in self._debug_entries
            if entry.agent_name == self.agent_name
        ]

        if not agent_entries:
            return {
                "total_entries": 0,
                "average_solution_time": 0,
                "effectiveness_distribution": {},
                "most_common_problem_types": [],
                "highly_effective_solutions": 0,
            }

        # Calculate statistics
        total_entries = len(agent_entries)
        solution_times = [
            entry.calculate_solution_time_minutes() for entry in agent_entries
        ]
        avg_solution_time = sum(solution_times) / len(solution_times)

        effectiveness_dist = {}
        for entry in agent_entries:
            eff = entry.solution_outcome.effectiveness.value
            effectiveness_dist[eff] = effectiveness_dist.get(eff, 0) + 1

        problem_type_dist = {}
        for entry in agent_entries:
            pt = entry.problem_type.value
            problem_type_dist[pt] = problem_type_dist.get(pt, 0) + 1

        highly_effective = len(
            [
                entry
                for entry in agent_entries
                if entry.solution_outcome.effectiveness
                == EnumSolutionEffectiveness.HIGHLY_EFFECTIVE
            ]
        )

        return {
            "total_entries": total_entries,
            "average_solution_time_minutes": round(avg_solution_time, 1),
            "effectiveness_distribution": effectiveness_dist,
            "most_common_problem_types": sorted(
                problem_type_dist.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "highly_effective_solutions": highly_effective,
            "reusable_solutions": len(
                [entry for entry in agent_entries if entry.is_highly_reusable()]
            ),
        }

    def _sanitize_data(
        self,
        data: Optional[
            Union[
                Dict[str, Union[str, int, float, bool, List[str]]],
                List[Union[str, int, float, bool]],
                str,
                int,
                float,
                bool,
            ]
        ],
    ) -> Optional[
        Union[
            Dict[str, Union[str, int, float, bool, List[str]]],
            List[Union[str, int, float, bool]],
            str,
            int,
            float,
            bool,
        ]
    ]:
        """Sanitize data before storing to remove sensitive information."""
        if data is None:
            return None

        # TODO: Implement proper data sanitization
        # Remove passwords, tokens, keys, etc.
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(
                    sensitive in key.lower()
                    for sensitive in ["password", "token", "key", "secret"]
                ):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self._sanitize_data(value)
            return sanitized
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        else:
            return data

    def _generate_tags(
        self,
        problem_description: str,
        problem_type: EnumProblemType,
        context: Optional[Dict[str, Union[str, int, float, bool, List[str]]]],
    ) -> List[str]:
        """Generate searchable tags for the debug entry."""
        tags = [problem_type.value]

        # Add subsystem and component tags
        if context:
            if context.get("subsystem"):
                tags.append(f"subsystem:{context['subsystem']}")
            if context.get("component"):
                tags.append(f"component:{context['component']}")

        # Add agent type tag
        tags.append(f"agent_type:{self.agent_type.value}")

        # Extract key terms from problem description
        key_terms = self._extract_key_terms(problem_description)
        tags.extend(key_terms)

        return list(set(tags))  # Remove duplicates

    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key searchable terms from text."""
        # Simple keyword extraction - could be enhanced with NLP
        common_tech_terms = [
            "validation",
            "configuration",
            "dependency",
            "performance",
            "integration",
            "authentication",
            "network",
            "database",
            "api",
            "service",
            "contract",
            "model",
            "schema",
            "error",
            "timeout",
            "connection",
            "permission",
        ]

        text_lower = text.lower()
        found_terms = []

        for term in common_tech_terms:
            if term in text_lower:
                found_terms.append(term)

        return found_terms[:10]  # Limit to top 10 terms

    def _simulate_similarity_search(
        self,
        query: ModelDebugIntelligenceQuery,
        offset: int = 0,
        min_similarity_score: float = 0.5,
    ) -> List[ModelDebugIntelligenceResult]:
        """Simulate similarity search - to be replaced with actual RAG query.

        Args:
            query: Intelligence query parameters
            offset: Results offset for pagination
            min_similarity_score: Minimum similarity score threshold

        Returns:
            List of matching debug intelligence results with pagination
        """
        # TODO: Replace with actual RAG/database similarity search
        # This will implement:
        # 1. Vector similarity search using embeddings
        # 2. Pagination support with offset/limit
        # 3. Filtering by similarity score threshold
        # 4. Sorting by relevance and recency

        # For now, return empty results but with proper pagination structure
        return []

    def _store_in_database(self, entry: ModelAgentDebugIntelligence):
        """Store debug intelligence entry in database and update RAG index."""
        # TODO: Implement actual database storage
        # TODO: Update RAG index with searchable content

        # For now, just log that we would store this
        logger.debug(
            "Would store debug intelligence in database",
            extra={
                "entry_id": str(entry.entry_id),
                "agent_name": entry.agent_name,
                "problem_type": entry.problem_type.value,
                "searchable_text_length": len(entry.get_searchable_text()),
            },
        )


# Decorator for automatic problem-solving capture
def capture_problem_solving(
    problem_type: EnumProblemType,
    confidence_level: float = 0.8,
    reusability_score: float = 0.7,
):
    """Decorator to automatically capture problem-solving sessions.

    Usage:
        @capture_problem_solving(EnumProblemType.VALIDATION_FAILURE)
        def validate_contract(self, contract_data):
            # Agent logic here
            return result
    """

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # Check if agent has debug capture capability
            if not hasattr(self, "debug_capture"):
                return func(self, *args, **kwargs)

            problem_description = f"Executing {func.__name__} with {len(args)} args"
            problem_id = self.debug_capture.start_problem_solving(
                problem_description, problem_type
            )

            start_time = datetime.utcnow()

            try:
                # Execute the function
                result = func(self, *args, **kwargs)

                # Capture successful solution
                end_time = datetime.utcnow()
                solution_time = int((end_time - start_time).total_seconds() / 60)

                self.debug_capture.capture_solution(
                    problem_id=problem_id,
                    problem_description=problem_description,
                    problem_type=problem_type,
                    solution_strategy=f"Successfully executed {func.__name__}",
                    solution_steps=[
                        f"Executed function {func.__name__} with provided parameters"
                    ],
                    effectiveness=EnumSolutionEffectiveness.EFFECTIVE,
                    success_indicators=[
                        "Function completed without exceptions",
                        "Result generated",
                    ],
                    time_to_solution_minutes=solution_time,
                    confidence_level=confidence_level,
                    reusability_score=reusability_score,
                )

                return result

            except Exception as e:
                # Capture failed attempt
                end_time = datetime.utcnow()
                solution_time = int((end_time - start_time).total_seconds() / 60)

                self.debug_capture.capture_solution(
                    problem_id=problem_id,
                    problem_description=f"Failed execution of {func.__name__}: {str(e)}",
                    problem_type=problem_type,
                    solution_strategy="Function execution failed",
                    solution_steps=[
                        f"Attempted to execute {func.__name__}",
                        f"Encountered error: {str(e)}",
                    ],
                    effectiveness=EnumSolutionEffectiveness.INEFFECTIVE,
                    success_indicators=[],
                    context={"error_message": str(e), "function": func.__name__},
                    time_to_solution_minutes=solution_time,
                    lessons_learned=[
                        f"Execution of {func.__name__} failed with: {str(e)}"
                    ],
                    confidence_level=0.1,
                    reusability_score=0.1,
                )

                raise

        return wrapper

    return decorator
