"""Database engine type enum for repository contracts.

Defines supported database engines for contract-driven data access.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumDatabaseEngine(StrValueHelper, str, Enum):
    """Supported database engine types for repository contracts.

    Used by ModelDbRepositoryContract to specify the target database.
    Validators may apply engine-specific SQL syntax rules.
    """

    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLITE = "sqlite"

    @classmethod
    def supports_schemas(cls, engine: EnumDatabaseEngine) -> bool:
        """Check if the engine supports schema-qualified table names."""
        return engine in {cls.POSTGRES, cls.MYSQL}

    @classmethod
    def supports_returning(cls, engine: EnumDatabaseEngine) -> bool:
        """Check if the engine supports RETURNING clause on INSERT/UPDATE/DELETE."""
        return engine in {cls.POSTGRES, cls.SQLITE}

    @classmethod
    def get_param_style(cls, engine: EnumDatabaseEngine) -> str:
        """Get the native parameter placeholder style for each engine.

        Returns:
            The parameter style: 'named' (:param), 'qmark' (?), or 'format' (%s).
        """
        style_map = {
            cls.POSTGRES: "named",  # :param or $N (we use :param)
            cls.MYSQL: "format",  # %s (but we normalize to :param)
            cls.SQLITE: "qmark",  # ? (but we normalize to :param)
        }
        return style_map.get(engine, "named")


__all__ = ["EnumDatabaseEngine"]
