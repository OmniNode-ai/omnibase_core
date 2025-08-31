import os
import re
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator

from omnibase_core.model.configuration.model_connection_parse_result import (
    LatencyProfile,
    ParsedConnectionInfo,
    PoolRecommendations,
)

# Moved to TYPE_CHECKING import

if TYPE_CHECKING:
    from omnibase_core.model.core import (
        ModelPerformanceProfile,
        ModelSecurityAssessment,
    )

from omnibase_core.model.security.model_secure_credentials import ModelSecureCredentials


class ModelDatabaseSecureConfig(ModelSecureCredentials):
    """
    Enterprise-grade secure database configuration with comprehensive connection
    management, security features, performance optimization, and operational monitoring.

    Features:
    - Multi-database support (PostgreSQL, MySQL, SQLite, Oracle, SQL Server)
    - Advanced connection string generation and parsing
    - SSL/TLS configuration and security assessment
    - Connection pooling recommendations and optimization
    - Performance profiling and tuning recommendations
    - Health monitoring and troubleshooting capabilities
    """

    host: str = Field(
        ...,
        description="Database host",
        pattern=r"^[a-zA-Z0-9\-\.]+$",
        max_length=255,
    )

    port: int = Field(..., description="Database port", ge=1, le=65535)

    database: str = Field(
        ...,
        description="Database name",
        pattern=r"^[a-zA-Z0-9_\-]+$",
        max_length=100,
    )

    username: str = Field(..., description="Database username", max_length=100)

    password: SecretStr = Field(..., description="Database password (secured)")

    driver: str = Field(
        default="postgresql",
        description="Database driver type",
        pattern=r"^(postgresql|mysql|sqlite|oracle|mssql|mongodb)$",
    )

    db_schema: str | None = Field(
        default=None,
        description="Default database schema",
        max_length=100,
    )

    ssl_enabled: bool = Field(
        default=False,
        description="Whether to use SSL connection",
    )

    ssl_mode: str = Field(
        default="prefer",
        description="SSL connection mode",
        pattern=r"^(disable|allow|prefer|require|verify-ca|verify-full)$",
    )

    ssl_cert_path: str | None = Field(
        default=None,
        description="Path to SSL certificate",
        max_length=500,
    )

    ssl_key_path: str | None = Field(
        default=None,
        description="Path to SSL key file",
        max_length=500,
    )

    ssl_key_password: SecretStr | None = Field(
        default=None,
        description="SSL key password (secured)",
    )

    ssl_ca_path: str | None = Field(
        default=None,
        description="Path to SSL CA certificate",
        max_length=500,
    )

    connection_timeout: int = Field(
        default=30,
        description="Connection timeout in seconds",
        ge=1,
        le=300,
    )

    query_timeout: int = Field(
        default=60,
        description="Query timeout in seconds",
        ge=1,
        le=3600,
    )

    pool_size: int = Field(default=10, description="Connection pool size", ge=1, le=100)

    max_overflow: int = Field(
        default=20,
        description="Maximum connection pool overflow",
        ge=0,
        le=100,
    )

    pool_timeout: int = Field(
        default=30,
        description="Pool checkout timeout in seconds",
        ge=1,
        le=300,
    )

    application_name: str | None = Field(
        default="ONEX",
        description="Application name for connection identification",
        max_length=100,
    )

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate database host format."""
        if not v or not v.strip():
            msg = "Database host cannot be empty"
            raise ValueError(msg)

        v = v.strip().lower()

        # Allow localhost and IP addresses
        if v in ["localhost", "127.0.0.1", "::1"]:
            return v

        # Validate hostname format
        if not re.match(r"^[a-zA-Z0-9\-\.]+$", v):
            msg = f"Invalid hostname format: {v}"
            raise ValueError(msg)

        # Check for valid domain format
        parts = v.split(".")
        for part in parts:
            if not part or len(part) > 63:
                msg = f"Invalid hostname part: {part}"
                raise ValueError(msg)
            if part.startswith("-") or part.endswith("-"):
                msg = f"Hostname part cannot start or end with dash: {part}"
                raise ValueError(msg)

        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate database port number."""
        if not isinstance(v, int):
            msg = "Port must be an integer"
            raise ValueError(msg)

        if not (1 <= v <= 65535):
            msg = f"Port must be between 1 and 65535, got: {v}"
            raise ValueError(msg)

        return v

    @field_validator("database")
    @classmethod
    def validate_database(cls, v: str) -> str:
        """Validate database name."""
        if not v or not v.strip():
            msg = "Database name cannot be empty"
            raise ValueError(msg)

        v = v.strip()

        # Check for SQL injection patterns
        dangerous_patterns = [";", "--", "/*", "*/", "xp_", "sp_"]
        for pattern in dangerous_patterns:
            if pattern in v.lower():
                msg = f"Database name contains potentially dangerous pattern: {pattern}"
                raise ValueError(
                    msg,
                )

        return v

    @field_validator("driver")
    @classmethod
    def validate_driver(cls, v: str) -> str:
        """Validate and normalize database driver."""
        if not v:
            return "postgresql"

        v = v.strip().lower()

        # Normalize common variations
        driver_aliases = {
            "postgres": "postgresql",
            "pg": "postgresql",
            "psql": "postgresql",
            "mysql": "mysql",
            "mariadb": "mysql",
            "sqlite": "sqlite",
            "sqlite3": "sqlite",
            "oracle": "oracle",
            "ora": "oracle",
            "mssql": "mssql",
            "sqlserver": "mssql",
            "mongodb": "mongodb",
            "mongo": "mongodb",
        }

        normalized = driver_aliases.get(v, v)

        valid_drivers = {"postgresql", "mysql", "sqlite", "oracle", "mssql", "mongodb"}
        if normalized not in valid_drivers:
            msg = f"Unsupported driver: {v}. Must be one of: {valid_drivers}"
            raise ValueError(
                msg,
            )

        return normalized

    # === Connection String Generation ===

    def get_connection_string(self, mask_password: bool = False) -> str:
        """Generate database connection string."""
        password_value = (
            "***MASKED***" if mask_password else self.password.get_secret_value()
        )

        if self.driver == "postgresql":
            return self._get_postgresql_connection_string(password_value)
        if self.driver == "mysql":
            return self._get_mysql_connection_string(password_value)
        if self.driver == "sqlite":
            return self._get_sqlite_connection_string()
        if self.driver == "oracle":
            return self._get_oracle_connection_string(password_value)
        if self.driver == "mssql":
            return self._get_mssql_connection_string(password_value)
        if self.driver == "mongodb":
            return self._get_mongodb_connection_string(password_value)
        msg = f"Connection string generation not implemented for driver: {self.driver}"
        raise ValueError(
            msg,
        )

    def _get_postgresql_connection_string(self, password: str) -> str:
        """Generate PostgreSQL connection string."""
        params = {
            "host": self.host,
            "port": self.port,
            "dbname": self.database,
            "user": self.username,
            "password": password,
            "connect_timeout": self.connection_timeout,
        }

        if self.application_name:
            params["application_name"] = self.application_name

        if self.ssl_enabled:
            params["sslmode"] = self.ssl_mode

            if self.ssl_cert_path:
                params["sslcert"] = self.ssl_cert_path
            if self.ssl_key_path:
                params["sslkey"] = self.ssl_key_path
            if self.ssl_ca_path:
                params["sslrootcert"] = self.ssl_ca_path

        if self.db_schema:
            params["options"] = f"-c search_path={self.db_schema}"

        param_string = " ".join([f"{k}={v}" for k, v in params.items()])
        return f"postgresql://{param_string}"

    def _get_mysql_connection_string(self, password: str) -> str:
        """Generate MySQL connection string."""
        base_url = f"mysql://{self.username}:{password}@{self.host}:{self.port}/{self.database}"

        params = []

        if self.ssl_enabled:
            params.append(f"ssl_mode={self.ssl_mode.upper()}")

            if self.ssl_cert_path:
                params.append(f"ssl_cert={self.ssl_cert_path}")
            if self.ssl_key_path:
                params.append(f"ssl_key={self.ssl_key_path}")
            if self.ssl_ca_path:
                params.append(f"ssl_ca={self.ssl_ca_path}")

        params.append(f"connect_timeout={self.connection_timeout}")

        if params:
            base_url += "?" + "&".join(params)

        return base_url

    def _get_sqlite_connection_string(self) -> str:
        """Generate SQLite connection string."""
        # For SQLite, database field contains the file path
        return f"sqlite:///{self.database}"

    def _get_oracle_connection_string(self, password: str) -> str:
        """Generate Oracle connection string."""
        return f"oracle://{self.username}:{password}@{self.host}:{self.port}/{self.database}"

    def _get_mssql_connection_string(self, password: str) -> str:
        """Generate SQL Server connection string."""
        params = [
            f"SERVER={self.host},{self.port}",
            f"DATABASE={self.database}",
            f"UID={self.username}",
            f"PWD={password}",
            f"TIMEOUT={self.connection_timeout}",
        ]

        if self.ssl_enabled:
            params.append("Encrypt=yes")
            params.append("TrustServerCertificate=no")

        return "mssql://?" + "&".join(params)

    def _get_mongodb_connection_string(self, password: str) -> str:
        """Generate MongoDB connection string."""
        base_url = f"mongodb://{self.username}:{password}@{self.host}:{self.port}/{self.database}"

        params = []

        if self.ssl_enabled:
            params.append("ssl=true")

        params.append(f"connectTimeoutMS={self.connection_timeout * 1000}")
        params.append(f"socketTimeoutMS={self.query_timeout * 1000}")

        if self.application_name:
            params.append(f"appName={self.application_name}")

        if params:
            base_url += "?" + "&".join(params)

        return base_url

    def parse_connection_string(self, connection_string: str) -> ParsedConnectionInfo:
        """Parse connection string back to configuration components."""
        parsed = urlparse(connection_string)

        config = {
            "driver": parsed.scheme,
            "host": parsed.hostname,
            "port": parsed.port,
            "username": parsed.username,
            "database": parsed.path.lstrip("/") if parsed.path else None,
        }

        # Parse query parameters
        if parsed.query:
            from urllib.parse import parse_qs

            params = parse_qs(parsed.query)

            # Map common parameters
            param_mapping = {
                "ssl": "ssl_enabled",
                "sslmode": "ssl_mode",
                "connect_timeout": "connection_timeout",
                "timeout": "connection_timeout",
            }

            for param, value in params.items():
                mapped_param = param_mapping.get(param, param)
                config[mapped_param] = (
                    value[0] if isinstance(value, list) and value else value
                )

        return config

    # === Security Assessment ===

    def get_security_assessment(self) -> "ModelSecurityAssessment":
        """Comprehensive security assessment of database configuration."""
        assessment = {
            "security_level": "basic",
            "encryption_in_transit": self.ssl_enabled,
            "authentication_strength": "basic",
            "vulnerabilities": [],
            "recommendations": [],
            "compliance_status": {},
        }

        # Assess SSL/TLS configuration
        if not self.ssl_enabled:
            assessment["vulnerabilities"].extend(
                [
                    "No encryption - database traffic sent in plaintext",
                    "Connection vulnerable to man-in-the-middle attacks",
                ],
            )
            assessment["recommendations"].extend(
                [
                    "Enable SSL/TLS encryption (ssl_enabled: true)",
                    "Use 'require' or 'verify-full' SSL mode for production",
                ],
            )
        else:
            assessment["security_level"] = "medium"

            if self.ssl_mode in ["disable", "allow"]:
                assessment["vulnerabilities"].append(f"Weak SSL mode: {self.ssl_mode}")
                assessment["recommendations"].append(
                    "Use 'require' or 'verify-full' SSL mode",
                )
            elif self.ssl_mode == "verify-full":
                assessment["security_level"] = "high"

        # Assess password strength
        password_value = self.password.get_secret_value()
        if len(password_value) < 8:
            assessment["vulnerabilities"].append(
                "Weak password (less than 8 characters)",
            )
            assessment["recommendations"].append(
                "Use password with at least 12 characters",
            )
        elif len(password_value) < 12:
            assessment["recommendations"].append(
                "Consider using longer password (12+ characters)",
            )
        else:
            assessment["authentication_strength"] = "strong"

        # Check for default credentials
        weak_passwords = ["password", "123456", "admin", "root", self.username]
        if password_value.lower() in [p.lower() for p in weak_passwords]:
            assessment["vulnerabilities"].append("Using common/default password")
            assessment["recommendations"].append("Use strong, unique password")

        # Database-specific security checks
        if self.driver == "postgresql":
            if self.username == "postgres":
                assessment["recommendations"].append(
                    "Avoid using 'postgres' superuser for applications",
                )
        elif self.driver == "mysql" and self.username == "root":
            assessment["recommendations"].append(
                "Avoid using 'root' user for applications",
            )

        # Compliance assessment
        assessment["compliance_status"] = {
            "pci_dss": assessment["encryption_in_transit"]
            and assessment["authentication_strength"] == "strong",
            "hipaa": assessment["encryption_in_transit"]
            and self.ssl_mode in ["require", "verify-full"],
            "gdpr": assessment["encryption_in_transit"],
            "sox": assessment["authentication_strength"] == "strong",
        }

        return assessment

    def is_production_ready(self) -> bool:
        """Check if configuration is suitable for production deployment."""
        assessment = self.get_security_assessment()

        # Production requires encryption
        if not assessment["encryption_in_transit"]:
            return False

        # Check for critical vulnerabilities
        critical_vulnerabilities = [
            "No encryption - database traffic sent in plaintext",
            "Using common/default password",
        ]

        for vuln in assessment["vulnerabilities"]:
            if any(critical in vuln for critical in critical_vulnerabilities):
                return False

        return True

    # === Connection Pool Optimization ===

    def get_pool_recommendations(self) -> PoolRecommendations:
        """Get connection pool optimization recommendations."""
        recommendations = PoolRecommendations(
            recommended_pool_size=self.pool_size,
            recommended_max_overflow=self.max_overflow,
            recommended_pool_timeout=self.pool_timeout,
            recommended_pool_recycle=3600,  # Default 1 hour
            recommendations=[],
        )

        # Assess current pool configuration
        if self.pool_size < 5:
            recommendations["recommendations"].append(
                "Consider increasing pool_size for better concurrency",
            )
        elif self.pool_size > 50:
            recommendations["recommendations"].append(
                "Large pool_size may cause resource contention",
            )

        if self.max_overflow == 0:
            recommendations["recommendations"].append(
                "Enable max_overflow for burst handling",
            )

        if self.pool_timeout < 10:
            recommendations["recommendations"].append(
                "Low pool_timeout may cause frequent timeouts",
            )

        # Performance profile based on driver
        if self.driver == "postgresql":
            recommendations["performance_profile"] = {
                "recommended_pool_size": min(20, max(5, self.pool_size)),
                "recommended_max_overflow": min(30, max(10, self.max_overflow)),
                "connection_overhead": "low",
                "concurrent_connections_limit": 100,
            }
        elif self.driver == "mysql":
            recommendations["performance_profile"] = {
                "recommended_pool_size": min(15, max(5, self.pool_size)),
                "recommended_max_overflow": min(25, max(10, self.max_overflow)),
                "connection_overhead": "medium",
                "concurrent_connections_limit": 151,  # MySQL default max_connections
            }

        return recommendations

    # === Performance Optimization ===

    def get_performance_profile(self) -> "ModelPerformanceProfile":
        """Get performance characteristics and optimization recommendations."""
        return {
            "latency_characteristics": self._get_latency_profile(),
            "throughput_optimization": self._get_throughput_recommendations(),
            "resource_usage": self._get_resource_usage_profile(),
            "monitoring_recommendations": self._get_monitoring_recommendations(),
        }

    def _get_latency_profile(self) -> LatencyProfile:
        """Assess configuration impact on latency."""
        profile = LatencyProfile(
            connection_latency="low",
            query_latency="low",
            overall_latency="low",
            factors=[],
        )

        # SSL impact
        if self.ssl_enabled:
            profile["factors"].append("SSL handshake adds connection latency")
            profile["connection_latency"] = "medium"

        # Timeout impact
        if self.connection_timeout > 60:
            profile["factors"].append(
                "High connection timeout may delay error detection",
            )

        if self.query_timeout > 300:
            profile["factors"].append("High query timeout may delay error detection")

        # Driver-specific characteristics
        driver_latency = {
            "postgresql": "low",
            "mysql": "low",
            "sqlite": "minimal",
            "oracle": "medium",
            "mssql": "medium",
            "mongodb": "medium",
        }

        profile["driver_latency"] = driver_latency.get(self.driver, "medium")

        return profile

    def _get_throughput_recommendations(self) -> list[str]:
        """Get throughput optimization recommendations."""
        recommendations = []

        # Pool-based recommendations
        pool_recommendations = self.get_pool_recommendations()
        recommendations.extend(pool_recommendations["recommendations"])

        # Driver-specific recommendations
        if self.driver == "postgresql":
            recommendations.extend(
                [
                    "Consider using connection pooler like PgBouncer for high concurrency",
                    "Enable prepared statements for repeated queries",
                ],
            )
        elif self.driver == "mysql":
            recommendations.extend(
                [
                    "Consider using MySQL connection pooling",
                    "Optimize query cache settings",
                ],
            )

        # SSL recommendations for performance
        if self.ssl_enabled and self.ssl_mode == "verify-full":
            recommendations.append(
                "Consider 'require' SSL mode if certificate validation overhead is high",
            )

        return recommendations

    def _get_resource_usage_profile(self) -> dict[str, str]:
        """Get resource usage characteristics."""
        profile = {
            "memory_usage": "medium",
            "cpu_usage": "low",
            "network_usage": "medium",
        }

        # Adjust based on pool size
        if self.pool_size > 20:
            profile["memory_usage"] = "high"

        # SSL increases CPU usage
        if self.ssl_enabled:
            profile["cpu_usage"] = "medium"

        # Driver-specific adjustments
        if self.driver == "oracle":
            profile["memory_usage"] = "high"
        elif self.driver == "sqlite":
            profile["memory_usage"] = "low"
            profile["network_usage"] = "none"

        return profile

    def _get_monitoring_recommendations(self) -> list[str]:
        """Get monitoring and observability recommendations."""
        recommendations = [
            "Monitor connection pool utilization",
            "Track query execution times",
            "Monitor database connection counts",
            "Set up alerts for connection failures",
        ]

        if self.ssl_enabled:
            recommendations.extend(
                ["Monitor SSL certificate expiration", "Track SSL handshake latency"],
            )

        # Driver-specific monitoring
        if self.driver == "postgresql":
            recommendations.extend(
                [
                    "Monitor PostgreSQL connection state",
                    "Track pg_stat_activity for active connections",
                ],
            )
        elif self.driver == "mysql":
            recommendations.extend(
                [
                    "Monitor MySQL processlist",
                    "Track connection thread cache efficiency",
                ],
            )

        return recommendations

    # === Health Check & Troubleshooting ===

    def can_connect(self) -> bool:
        """Test if configuration allows successful connection."""
        validation = self.validate_credentials()
        if not validation["is_valid"]:
            return False

        # Check SSL files exist if SSL is enabled
        if self.ssl_enabled:
            if self.ssl_cert_path and not os.path.exists(self.ssl_cert_path):
                return False
            if self.ssl_key_path and not os.path.exists(self.ssl_key_path):
                return False
            if self.ssl_ca_path and not os.path.exists(self.ssl_ca_path):
                return False

        # Driver-specific checks
        if self.driver == "sqlite":
            # For SQLite, check if directory exists
            db_dir = os.path.dirname(self.database)
            if db_dir and not os.path.exists(db_dir):
                return False

        return True

    def get_troubleshooting_guide(self) -> dict[str, list[str]]:
        """Get troubleshooting guide for common database connection issues."""
        return {
            "connection_failures": [
                "Verify host and port are correct and reachable",
                "Check database name exists",
                "Verify username and password are correct",
                "Ensure database server is running and accepting connections",
                "Check firewall rules allow connection to database port",
            ],
            "ssl_issues": [
                "Verify SSL is enabled on database server",
                "Check SSL certificate paths are correct and files exist",
                "Ensure SSL certificates are valid and not expired",
                "Verify SSL mode is compatible with server configuration",
                "Check SSL key file permissions and password if required",
            ],
            "authentication_failures": [
                "Verify username exists in database",
                "Check password is correct and not expired",
                "Ensure user has necessary privileges",
                "Check for account lockouts or restrictions",
                "Verify authentication method is supported",
            ],
            "performance_issues": [
                "Monitor connection pool utilization",
                "Check for connection leaks",
                "Adjust timeout values based on network latency",
                "Consider increasing pool size for high concurrency",
                "Monitor database server performance metrics",
            ],
            "driver_specific": self._get_driver_specific_troubleshooting(),
        }

    def _get_driver_specific_troubleshooting(self) -> list[str]:
        """Get driver-specific troubleshooting tips."""
        guides = {
            "postgresql": [
                "Check pg_hba.conf for authentication rules",
                "Verify PostgreSQL is listening on configured port",
                "Check postgresql.conf for ssl settings",
                "Monitor pg_stat_activity for connection states",
            ],
            "mysql": [
                "Check MySQL bind-address configuration",
                "Verify user host permissions in mysql.user table",
                "Check MySQL SSL configuration",
                "Monitor SHOW PROCESSLIST for connection states",
            ],
            "sqlite": [
                "Verify database file path and permissions",
                "Check directory write permissions for database creation",
                "Ensure SQLite library is installed",
            ],
            "oracle": [
                "Check Oracle listener configuration",
                "Verify TNS names resolution",
                "Check Oracle SSL/TLS configuration",
                "Monitor v$session for connection states",
            ],
            "mssql": [
                "Verify SQL Server is accepting connections",
                "Check SQL Server authentication mode",
                "Verify SSL certificate configuration",
                "Monitor sys.dm_exec_sessions for connections",
            ],
        }

        return guides.get(self.driver, [])

    # === Environment Integration ===

    @classmethod
    def load_from_env(cls, env_prefix: str = "ONEX_DB_") -> "ModelDatabaseSecureConfig":
        """Load database configuration from environment variables."""
        password = os.getenv(f"{env_prefix}PASSWORD")
        if not password:
            msg = f"Database password required: {env_prefix}PASSWORD"
            raise ValueError(msg)

        config_data = {
            "host": os.getenv(f"{env_prefix}HOST", "localhost"),
            "database": os.getenv(f"{env_prefix}DATABASE", "onex_dev"),
            "username": os.getenv(f"{env_prefix}USERNAME", "onex_user"),
            "password": SecretStr(password),
            "driver": os.getenv(f"{env_prefix}DRIVER", "postgresql"),
            "schema": os.getenv(f"{env_prefix}SCHEMA"),
            "ssl_enabled": os.getenv(f"{env_prefix}SSL_ENABLED", "false").lower()
            == "true",
            "ssl_mode": os.getenv(f"{env_prefix}SSL_MODE", "prefer"),
            "ssl_cert_path": os.getenv(f"{env_prefix}SSL_CERT_PATH"),
            "ssl_key_path": os.getenv(f"{env_prefix}SSL_KEY_PATH"),
            "ssl_ca_path": os.getenv(f"{env_prefix}SSL_CA_PATH"),
            "application_name": os.getenv(f"{env_prefix}APPLICATION_NAME", "ONEX"),
        }

        # Handle SecretStr fields
        ssl_key_password = os.getenv(f"{env_prefix}SSL_KEY_PASSWORD")
        if ssl_key_password:
            config_data["ssl_key_password"] = SecretStr(ssl_key_password)

        # Handle integer fields
        try:
            if port := os.getenv(f"{env_prefix}PORT"):
                config_data["port"] = int(port)
            else:
                # Set default port based on driver
                default_ports = {
                    "postgresql": 5432,
                    "mysql": 3306,
                    "oracle": 1521,
                    "mssql": 1433,
                    "mongodb": 27017,
                    "sqlite": 0,  # Not applicable for SQLite
                }
                config_data["port"] = default_ports.get(config_data["driver"], 5432)

            if timeout := os.getenv(f"{env_prefix}CONNECTION_TIMEOUT"):
                config_data["connection_timeout"] = int(timeout)
            if query_timeout := os.getenv(f"{env_prefix}QUERY_TIMEOUT"):
                config_data["query_timeout"] = int(query_timeout)
            if pool_size := os.getenv(f"{env_prefix}POOL_SIZE"):
                config_data["pool_size"] = int(pool_size)
            if max_overflow := os.getenv(f"{env_prefix}MAX_OVERFLOW"):
                config_data["max_overflow"] = int(max_overflow)
            if pool_timeout := os.getenv(f"{env_prefix}POOL_TIMEOUT"):
                config_data["pool_timeout"] = int(pool_timeout)
        except ValueError as e:
            msg = f"Invalid integer value in environment variables: {e}"
            raise ValueError(msg)

        # Remove None values
        config_data = {k: v for k, v in config_data.items() if v is not None}

        return cls(**config_data)

    # === Factory Methods ===

    @classmethod
    def create_postgresql(
        cls,
        host: str = "localhost",
        port: int = 5432,
        database: str = "onex_dev",
        username: str = "onex_user",
        password: str = "secure_password",
    ) -> "ModelDatabaseSecureConfig":
        """Create PostgreSQL configuration."""
        return cls(
            host=host,
            port=port,
            database=database,
            username=username,
            password=SecretStr(password),
            driver="postgresql",
        )

    @classmethod
    def create_mysql(
        cls,
        host: str = "localhost",
        port: int = 3306,
        database: str = "onex_dev",
        username: str = "onex_user",
        password: str = "secure_password",
    ) -> "ModelDatabaseSecureConfig":
        """Create MySQL configuration."""
        return cls(
            host=host,
            port=port,
            database=database,
            username=username,
            password=SecretStr(password),
            driver="mysql",
        )

    @classmethod
    def create_sqlite(
        cls,
        database_path: str = "onex_dev.db",
    ) -> "ModelDatabaseSecureConfig":
        """Create SQLite configuration."""
        return cls(
            host="localhost",  # Required by model but not used for SQLite
            port=0,  # Not applicable for SQLite
            database=database_path,
            username="sqlite",  # Not applicable but required by model
            password=SecretStr(""),  # Not applicable but required by model
            driver="sqlite",
        )

    @classmethod
    def create_production_postgresql(
        cls,
        host: str,
        database: str,
        username: str,
        password: str,
        ssl_cert_path: str,
        ssl_key_path: str,
        ssl_ca_path: str,
    ) -> "ModelDatabaseSecureConfig":
        """Create production-ready PostgreSQL configuration with SSL."""
        return cls(
            host=host,
            port=5432,
            database=database,
            username=username,
            password=SecretStr(password),
            driver="postgresql",
            ssl_enabled=True,
            ssl_mode="verify-full",
            ssl_cert_path=ssl_cert_path,
            ssl_key_path=ssl_key_path,
            ssl_ca_path=ssl_ca_path,
            pool_size=20,
            max_overflow=30,
        )
