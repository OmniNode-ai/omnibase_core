"""
Document dependency graph models for tracking relationships and impact analysis.

Defines data structures for building and managing dependency graphs between
documents, code files, and other resources in the ONEX system.
"""

from datetime import datetime
from enum import Enum

from pydantic import Field, validator

from omnibase_core.model.core.model_onex_base_state import ModelOnexInputState


class EnumDependencyType(str, Enum):
    """Types of dependencies that can be tracked."""

    CODE_FILE = "code_file"  # Python, JS, etc. source files
    CONFIG_FILE = "config_file"  # YAML, JSON, TOML config files
    DOCUMENTATION = "documentation"  # Other documentation files
    SCHEMA_FILE = "schema_file"  # JSON Schema, OpenAPI, etc.
    TEMPLATE_FILE = "template_file"  # Template files
    TEST_FILE = "test_file"  # Test files
    BUILD_FILE = "build_file"  # Dockerfile, build scripts
    EXTERNAL_API = "external_api"  # External API endpoints
    DATABASE_SCHEMA = "database_schema"  # Database schema references
    ENVIRONMENT_VAR = "environment_var"  # Environment variable references
    CLI_COMMAND = "cli_command"  # CLI command references
    UNKNOWN = "unknown"


class EnumDependencyRelationship(str, Enum):
    """Types of relationships between documents and dependencies."""

    DOCUMENTS = "documents"  # Doc describes/explains the dependency
    REFERENCES = "references"  # Doc references/mentions the dependency
    CONFIGURES = "configures"  # Doc provides configuration for dependency
    DEPENDS_ON = "depends_on"  # Doc functionality depends on dependency
    GENERATES = "generates"  # Doc describes how to generate dependency
    TESTS = "tests"  # Doc describes how to test dependency
    IMPORTS = "imports"  # Doc shows how to import/use dependency


class EnumChangeImpact(str, Enum):
    """Impact levels for dependency changes."""

    NONE = "none"  # No impact on documentation
    LOW = "low"  # Minor updates may be needed
    MEDIUM = "medium"  # Moderate updates likely needed
    HIGH = "high"  # Significant updates required
    CRITICAL = "critical"  # Documentation may be completely invalid


class ModelDependencyNode(ModelOnexInputState):
    """Represents a single node in the dependency graph."""

    node_id: str = Field(..., description="Unique identifier for this node")
    file_path: str = Field(..., description="Full path to the file or resource")
    node_type: EnumDependencyType = Field(
        ...,
        description="Type of dependency this node represents",
    )

    # File metadata
    exists: bool = Field(default=True, description="Whether the file currently exists")
    last_modified: datetime = Field(..., description="Last modification timestamp")
    file_size_bytes: int = Field(default=0, description="File size in bytes")
    file_hash: str | None = Field(
        None,
        description="File content hash for change detection",
    )

    # Analysis metadata
    is_critical: bool = Field(
        default=False,
        description="Whether this dependency is critical",
    )
    complexity_score: float = Field(
        default=0.5,
        description="Complexity score (0.0-1.0)",
    )
    change_frequency: float = Field(
        default=0.0,
        description="How frequently this file changes (changes/day)",
    )

    # Tracking
    last_analyzed: datetime | None = Field(
        None,
        description="Last time this node was analyzed",
    )
    analysis_version: str = Field(default="1.0", description="Version of analysis used")

    @validator("complexity_score")
    def validate_complexity_score(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "Complexity score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelDependencyEdge(ModelOnexInputState):
    """Represents a relationship edge in the dependency graph."""

    edge_id: str = Field(..., description="Unique identifier for this edge")
    source_node_id: str = Field(
        ...,
        description="ID of the source node (typically a document)",
    )
    target_node_id: str = Field(
        ...,
        description="ID of the target node (the dependency)",
    )

    relationship_type: EnumDependencyRelationship = Field(
        ...,
        description="Type of relationship",
    )
    impact_weight: float = Field(default=1.0, description="Weight of impact (0.0-1.0)")
    change_impact: EnumChangeImpact = Field(
        default=EnumChangeImpact.MEDIUM,
        description="Expected impact of changes",
    )

    # Context information
    line_numbers: list[int] = Field(
        default_factory=list,
        description="Line numbers where dependency is referenced",
    )
    context_snippets: list[str] = Field(
        default_factory=list,
        description="Code/text snippets showing the reference",
    )

    # Tracking
    discovered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this relationship was discovered",
    )
    last_verified: datetime | None = Field(
        None,
        description="Last time this relationship was verified to still exist",
    )
    confidence_score: float = Field(
        default=1.0,
        description="Confidence in this relationship (0.0-1.0)",
    )

    @validator("impact_weight", "confidence_score")
    def validate_scores(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "Score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelDependencyGraph(ModelOnexInputState):
    """Complete dependency graph for a document or set of documents."""

    graph_id: str = Field(
        ...,
        description="Unique identifier for this dependency graph",
    )
    root_document_path: str = Field(
        ...,
        description="Primary document this graph is built for",
    )

    # Graph structure
    nodes: dict[str, ModelDependencyNode] = Field(
        default_factory=dict,
        description="All nodes in the graph",
    )
    edges: list[ModelDependencyEdge] = Field(
        default_factory=list,
        description="All edges in the graph",
    )

    # Graph metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this graph was created",
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last time graph was updated",
    )
    analysis_depth: int = Field(
        default=1,
        description="Depth of dependency analysis performed",
    )

    # Statistics
    total_dependencies: int = Field(
        default=0,
        description="Total number of dependencies tracked",
    )
    critical_dependencies: int = Field(
        default=0,
        description="Number of critical dependencies",
    )
    stale_dependencies: int = Field(
        default=0,
        description="Number of stale dependencies",
    )
    missing_dependencies: int = Field(
        default=0,
        description="Number of missing/broken dependencies",
    )

    # Performance tracking
    build_duration_ms: int = Field(
        default=0,
        description="Time taken to build this graph in milliseconds",
    )
    memory_usage_bytes: int = Field(default=0, description="Memory used by this graph")


class ModelDependencyAnalysisResult(ModelOnexInputState):
    """Result of dependency analysis for impact assessment."""

    analysis_id: str = Field(..., description="Unique identifier for this analysis")
    document_path: str = Field(..., description="Document that was analyzed")
    trigger_change: str | None = Field(
        None,
        description="Change that triggered this analysis",
    )

    # Analysis results
    dependency_graph: ModelDependencyGraph = Field(
        ...,
        description="Generated dependency graph",
    )
    impact_assessment: dict[str, EnumChangeImpact] = Field(
        default_factory=dict,
        description="Impact assessment for each dependency",
    )

    # Recommendations
    requires_update: bool = Field(
        default=False,
        description="Whether document requires updating",
    )
    update_priority: str = Field(
        default="low",
        description="Priority level for updates (low, medium, high, critical)",
    )
    suggested_actions: list[str] = Field(
        default_factory=list,
        description="Suggested actions to take",
    )

    # Quality metrics
    coverage_score: float = Field(
        default=0.0,
        description="Percentage of dependencies successfully analyzed",
    )
    confidence_score: float = Field(
        default=0.0,
        description="Overall confidence in analysis results",
    )

    # Timing
    analysis_started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When analysis started",
    )
    analysis_completed_at: datetime | None = Field(
        None,
        description="When analysis completed",
    )
    analysis_duration_ms: int = Field(
        default=0,
        description="Analysis duration in milliseconds",
    )

    @validator("coverage_score", "confidence_score")
    def validate_scores(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "Score must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v


class ModelDependencyChangeEvent(ModelOnexInputState):
    """Event representing a change in the dependency graph."""

    event_id: str = Field(..., description="Unique identifier for this change event")
    graph_id: str = Field(..., description="ID of the affected dependency graph")
    change_type: str = Field(
        ...,
        description="Type of change (node_added, node_removed, edge_added, edge_removed, node_modified)",
    )

    # Change details
    affected_node_id: str | None = Field(None, description="ID of node that changed")
    affected_edge_id: str | None = Field(None, description="ID of edge that changed")
    old_value: dict | None = Field(None, description="Previous value before change")
    new_value: dict | None = Field(None, description="New value after change")

    # Impact
    impact_level: EnumChangeImpact = Field(
        ...,
        description="Assessed impact level of this change",
    )
    affected_documents: list[str] = Field(
        default_factory=list,
        description="Documents affected by this change",
    )

    # Metadata
    detected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this change was detected",
    )
    source: str = Field(
        default="unknown",
        description="Source of change detection (git, filesystem, manual)",
    )
    processed: bool = Field(
        default=False,
        description="Whether this change has been processed",
    )


class ModelDependencyGraphConfig(ModelOnexInputState):
    """Configuration for dependency graph building and analysis."""

    # Analysis settings
    max_depth: int = Field(
        default=3,
        description="Maximum depth for dependency traversal",
    )
    include_test_files: bool = Field(
        default=True,
        description="Whether to include test files in analysis",
    )
    include_build_files: bool = Field(
        default=True,
        description="Whether to include build files",
    )
    include_config_files: bool = Field(
        default=True,
        description="Whether to include configuration files",
    )

    # File patterns
    excluded_patterns: list[str] = Field(
        default_factory=lambda: ["*.pyc", "*.log", "__pycache__/*", ".git/*"],
        description="File patterns to exclude",
    )
    included_extensions: list[str] = Field(
        default_factory=lambda: [".py", ".md", ".yaml", ".yml", ".json", ".toml"],
        description="File extensions to include",
    )

    # Thresholds
    min_file_size_bytes: int = Field(
        default=1,
        description="Minimum file size to analyze",
    )
    max_file_size_bytes: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum file size to analyze (10MB default)",
    )

    # Performance settings
    max_analysis_time_seconds: int = Field(
        default=300,
        description="Maximum time to spend on analysis",
    )
    enable_caching: bool = Field(
        default=True,
        description="Whether to enable result caching",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        description="Cache time-to-live in seconds",
    )

    # Change detection
    enable_real_time_monitoring: bool = Field(
        default=True,
        description="Enable real-time file system monitoring",
    )
    change_debounce_seconds: int = Field(
        default=5,
        description="Debounce time for rapid file changes",
    )

    # AI analysis
    enable_ai_analysis: bool = Field(
        default=False,
        description="Enable AI-powered dependency analysis",
    )
    ai_analysis_batch_size: int = Field(
        default=10,
        description="Batch size for AI analysis",
    )
    ai_confidence_threshold: float = Field(
        default=0.7,
        description="Minimum confidence for AI-detected dependencies",
    )

    @validator("ai_confidence_threshold")
    def validate_ai_confidence_threshold(self, v):
        if not 0.0 <= v <= 1.0:
            msg = "AI confidence threshold must be between 0.0 and 1.0"
            raise ValueError(msg)
        return v
