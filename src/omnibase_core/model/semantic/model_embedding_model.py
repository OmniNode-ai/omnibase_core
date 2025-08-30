"""
Embedding model enumeration for semantic search.

Defines available embedding models with their characteristics
and recommended use cases for semantic search applications.
"""

from enum import Enum


class ModelEmbeddingModel(str, Enum):
    """
    Available embedding models for semantic search.

    Models are ordered by quality/performance tradeoff, with higher-quality
    models generally being slower but more accurate.
    """

    # Fast models (good for development/testing)
    MINILM_L6_V2 = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dim, fast
    MINILM_L12_V2 = "sentence-transformers/all-MiniLM-L12-v2"  # 384 dim, medium

    # Balanced models (recommended for most use cases)
    BGE_BASE_EN = "BAAI/bge-base-en-v1.5"  # 768 dim, excellent quality
    BGE_SMALL_EN = "BAAI/bge-small-en-v1.5"  # 384 dim, good quality

    # High-quality models (best accuracy, slower)
    BGE_LARGE_EN = "BAAI/bge-large-en-v1.5"  # 1024 dim, highest quality
    GTE_LARGE = "thenlper/gte-large"  # 1024 dim, excellent performance
    GTE_BASE = "thenlper/gte-base"  # 768 dim, good performance

    # Multilingual models
    BGE_M3 = "BAAI/bge-m3"  # 1024 dim, multilingual
    E5_BASE_V2 = "intfloat/e5-base-v2"  # 768 dim, multilingual
    E5_LARGE_V2 = "intfloat/e5-large-v2"  # 1024 dim, multilingual

    # Specialized models
    INSTRUCTOR_LARGE = "hkunlp/instructor-large"  # 768 dim, instruction-following
    COHERE_EMBED_V3 = "cohere-embed-english-v3.0"  # API-based, high quality

    @classmethod
    def get_model_info(cls, model: "ModelEmbeddingModel") -> dict:
        """Get detailed information about an embedding model."""
        model_info = {
            cls.MINILM_L6_V2: {
                "dimensions": 384,
                "max_seq_length": 256,
                "speed": "very_fast",
                "quality": "good",
                "size_mb": 90,
                "use_case": "development, testing, fast inference",
            },
            cls.MINILM_L12_V2: {
                "dimensions": 384,
                "max_seq_length": 256,
                "speed": "fast",
                "quality": "good",
                "size_mb": 120,
                "use_case": "balanced speed/quality",
            },
            cls.BGE_BASE_EN: {
                "dimensions": 768,
                "max_seq_length": 512,
                "speed": "medium",
                "quality": "excellent",
                "size_mb": 430,
                "use_case": "recommended for most English applications",
            },
            cls.BGE_SMALL_EN: {
                "dimensions": 384,
                "max_seq_length": 512,
                "speed": "fast",
                "quality": "very_good",
                "size_mb": 130,
                "use_case": "lightweight applications with good quality",
            },
            cls.BGE_LARGE_EN: {
                "dimensions": 1024,
                "max_seq_length": 512,
                "speed": "slow",
                "quality": "exceptional",
                "size_mb": 1340,
                "use_case": "highest quality English embeddings",
            },
            cls.GTE_LARGE: {
                "dimensions": 1024,
                "max_seq_length": 512,
                "speed": "slow",
                "quality": "exceptional",
                "size_mb": 1340,
                "use_case": "high-quality general purpose embeddings",
            },
            cls.GTE_BASE: {
                "dimensions": 768,
                "max_seq_length": 512,
                "speed": "medium",
                "quality": "excellent",
                "size_mb": 430,
                "use_case": "balanced performance and quality",
            },
            cls.BGE_M3: {
                "dimensions": 1024,
                "max_seq_length": 8192,
                "speed": "slow",
                "quality": "excellent",
                "size_mb": 2240,
                "use_case": "multilingual, long documents",
            },
            cls.E5_BASE_V2: {
                "dimensions": 768,
                "max_seq_length": 512,
                "speed": "medium",
                "quality": "very_good",
                "size_mb": 430,
                "use_case": "multilingual applications",
            },
            cls.E5_LARGE_V2: {
                "dimensions": 1024,
                "max_seq_length": 512,
                "speed": "slow",
                "quality": "excellent",
                "size_mb": 1340,
                "use_case": "high-quality multilingual embeddings",
            },
            cls.INSTRUCTOR_LARGE: {
                "dimensions": 768,
                "max_seq_length": 512,
                "speed": "medium",
                "quality": "excellent",
                "size_mb": 1340,
                "use_case": "instruction-following, task-specific embeddings",
            },
            cls.COHERE_EMBED_V3: {
                "dimensions": 1024,
                "max_seq_length": 512,
                "speed": "api_dependent",
                "quality": "exceptional",
                "size_mb": 0,  # API-based
                "use_case": "API-based, highest quality commercial embeddings",
            },
        }

        return model_info.get(
            model,
            {
                "dimensions": "unknown",
                "max_seq_length": 512,
                "speed": "unknown",
                "quality": "unknown",
                "size_mb": "unknown",
                "use_case": "custom model",
            },
        )

    @classmethod
    def get_recommended_model(cls, use_case: str = "balanced") -> "ModelEmbeddingModel":
        """Get recommended model for specific use case."""
        recommendations = {
            "fast": cls.BGE_SMALL_EN,
            "balanced": cls.BGE_BASE_EN,
            "quality": cls.BGE_LARGE_EN,
            "multilingual": cls.BGE_M3,
            "development": cls.MINILM_L6_V2,
            "production": cls.BGE_BASE_EN,
        }

        return recommendations.get(use_case, cls.BGE_BASE_EN)
