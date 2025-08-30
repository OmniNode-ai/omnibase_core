"""
File processing protocols for SYSINT-001 integration.

Defines protocols for unified file processing, tree analysis, and caching operations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# === MODELS ===


class ModelFileProcessingResult(BaseModel):
    """Result of file processing operation"""

    file_path: Path
    success: bool
    processing_time_ms: float
    cached: bool
    metadata: Dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ModelProjectAnalysis(BaseModel):
    """Complete project analysis result"""

    project_root: Path
    total_files: int
    processed_files: int
    ignored_files: int
    failed_files: int
    processing_time_ms: float
    file_results: List[ModelFileProcessingResult]
    tree_structure: Dict[str, object]  # OnexTree structure
    ignore_patterns: List[str]  # OnexIgnore patterns applied


class ModelASTNode(BaseModel):
    """AST node representation"""

    node_type: str
    name: Optional[str] = None
    start_line: int
    end_line: int
    start_column: int
    end_column: int
    children: List["ModelASTNode"] = Field(default_factory=list)
    metadata: Dict[str, object] = Field(default_factory=dict)


class ModelASTResult(BaseModel):
    """Result of AST parsing"""

    file_path: Path
    language: str
    root_node: ModelASTNode
    parsing_time_ms: float
    node_count: int
    error_count: int
    warnings: List[str] = Field(default_factory=list)


# === PROTOCOLS ===


class ProtocolFileProcessor(ABC):
    """Protocol for file processing operations"""

    @abstractmethod
    async def process_file(self, file_path: Path) -> ModelFileProcessingResult:
        """
        Process a single file.

        Args:
            file_path: Path to file to process

        Returns:
            Processing result with metadata
        """
        pass

    @abstractmethod
    async def process_directory(
        self, directory: Path
    ) -> List[ModelFileProcessingResult]:
        """
        Process all files in a directory.

        Args:
            directory: Directory path to process

        Returns:
            List of processing results
        """
        pass

    @abstractmethod
    async def process_project(self, project_root: Path) -> ModelProjectAnalysis:
        """
        Process entire project with OnexTree/OnexIgnore integration.

        Args:
            project_root: Root directory of project

        Returns:
            Complete project analysis
        """
        pass


class ProtocolTreeAnalyzer(ABC):
    """Protocol for AST tree analysis"""

    @abstractmethod
    async def parse_file(
        self, file_path: Path, language: Optional[str] = None
    ) -> ModelASTResult:
        """
        Parse file and return AST.

        Args:
            file_path: Path to file to parse
            language: Optional language hint (auto-detected if not provided)

        Returns:
            Parsed AST result
        """
        pass

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """
        Return list of supported languages.

        Returns:
            List of language identifiers (e.g., ["python", "typescript"])
        """
        pass

    @abstractmethod
    async def extract_symbols(self, ast_result: ModelASTResult) -> Dict[str, List[str]]:
        """
        Extract symbols from AST (functions, classes, etc).

        Args:
            ast_result: Parsed AST result

        Returns:
            Dictionary of symbol types to symbol names
        """
        pass


class ProtocolCacheManager(ABC):
    """Protocol for caching operations"""

    @abstractmethod
    async def get(self, key: str) -> Optional[object]:
        """
        Get cached value.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: object, ttl_seconds: int) -> None:
        """
        Set cached value with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
        """
        pass

    @abstractmethod
    async def invalidate(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern.

        Args:
            pattern: Pattern to match (supports wildcards)

        Returns:
            Number of entries invalidated
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries"""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with stats (hits, misses, size, etc)
        """
        pass


class ProtocolRateLimiter(ABC):
    """Protocol for rate limiting operations"""

    @abstractmethod
    async def acquire(self, resource: str) -> None:
        """
        Acquire rate limit permit for resource.

        Args:
            resource: Resource identifier

        Raises:
            RateLimitExceeded: If rate limit exceeded
        """
        pass

    @abstractmethod
    async def release(self, resource: str) -> None:
        """
        Release rate limit permit for resource.

        Args:
            resource: Resource identifier
        """
        pass

    @abstractmethod
    def get_limit(self, resource: str) -> int:
        """
        Get rate limit for resource.

        Args:
            resource: Resource identifier

        Returns:
            Maximum requests per time window
        """
        pass


class ProtocolMetricsCollector(ABC):
    """Protocol for metrics collection"""

    @abstractmethod
    def increment(
        self, metric: str, value: int = 1, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Increment counter metric.

        Args:
            metric: Metric name
            value: Increment value
            tags: Optional metric tags
        """
        pass

    @abstractmethod
    def gauge(
        self, metric: str, value: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Set gauge metric.

        Args:
            metric: Metric name
            value: Gauge value
            tags: Optional metric tags
        """
        pass

    @abstractmethod
    def histogram(
        self, metric: str, value: float, tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record histogram metric.

        Args:
            metric: Metric name
            value: Value to record
            tags: Optional metric tags
        """
        pass

    @abstractmethod
    async def export_metrics(self) -> Dict[str, object]:
        """
        Export all metrics.

        Returns:
            Dictionary of metric data
        """
        pass


# Enable forward references
ModelASTNode.model_rebuild()
