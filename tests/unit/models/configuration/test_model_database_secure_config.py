"""Comprehensive tests for ModelDatabaseSecureConfig.

Test Coverage:
- Initialization and validation
- Connection string generation (6 database types)
- Connection string parsing
- Security assessment and SSL/TLS
- Performance and pool recommendations
- Health checks and troubleshooting
- Environment integration
- Factory methods
"""

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.examplesuration.model_database_secure_config import (
    ModelDatabaseSecureConfig,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestModelDatabaseSecureConfigInstantiation:
    """Tests for ModelDatabaseSecureConfig instantiation and validation."""

    def test_create_basic_postgresql_config(self):
        """Test creating basic PostgreSQL configuration."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
        )
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.database == "test_db"
        assert config.username == "test_user"
        assert config.password.get_secret_value() == "test_password"
        assert config.driver == "postgresql"

    def test_create_with_ssl_enabled(self):
        """Test creating configuration with SSL enabled."""
        config = ModelDatabaseSecureConfig(
            host="db.example.com",
            port=5432,
            database="prod_db",
            username="app_user",
            password=SecretStr("secure_password_123"),
            driver="postgresql",
            ssl_enabled=True,
            ssl_mode="verify-full",
            ssl_cert_path="/path/to/cert.pem",
            ssl_key_path="/path/to/key.pem",
            ssl_ca_path="/path/to/ca.pem",
        )
        assert config.ssl_enabled is True
        assert config.ssl_mode == "verify-full"
        assert config.ssl_cert_path == "/path/to/cert.pem"
        assert config.ssl_key_path == "/path/to/key.pem"
        assert config.ssl_ca_path == "/path/to/ca.pem"

    def test_create_with_connection_pool_settings(self):
        """Test creating configuration with connection pool settings."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
            pool_size=20,
            max_overflow=30,
            pool_timeout=60,
        )
        assert config.pool_size == 20
        assert config.max_overflow == 30
        assert config.pool_timeout == 60

    def test_create_with_timeouts(self):
        """Test creating configuration with custom timeouts."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
            connection_timeout=60,
            query_timeout=120,
        )
        assert config.connection_timeout == 60
        assert config.query_timeout == 120

    def test_create_with_schema(self):
        """Test creating configuration with database schema."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
            db_schema="public",
        )
        assert config.db_schema == "public"

    def test_create_with_application_name(self):
        """Test creating configuration with application name."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
            application_name="MyApp",
        )
        assert config.application_name == "MyApp"


class TestModelDatabaseSecureConfigValidation:
    """Tests for field validation."""

    def test_validate_host_localhost(self):
        """Test validation of localhost."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
        )
        assert config.host == "localhost"

    def test_validate_host_ip_address(self):
        """Test validation of IP address."""
        config = ModelDatabaseSecureConfig(
            host="127.0.0.1",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
        )
        assert config.host == "127.0.0.1"

    def test_validate_host_domain(self):
        """Test validation of domain name."""
        config = ModelDatabaseSecureConfig(
            host="db.example.com",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
        )
        assert config.host == "db.example.com"

    def test_validate_host_empty_raises_error(self):
        """Test that empty host raises validation error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDatabaseSecureConfig(
                host="",
                port=5432,
                database="test_db",
                username="test_user",
                password=SecretStr("test_password"),
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "cannot be empty" in str(exc_info.value)

    def test_validate_host_invalid_format_raises_error(self):
        """Test that invalid hostname raises validation error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDatabaseSecureConfig(
                host="-invalid-host",
                port=5432,
                database="test_db",
                username="test_user",
                password=SecretStr("test_password"),
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_validate_port_valid_range(self):
        """Test validation of valid port numbers."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=8080,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
        )
        assert config.port == 8080

    def test_validate_port_below_range_raises_error(self):
        """Test that port below valid range raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDatabaseSecureConfig(
                host="localhost",
                port=0,
                database="test_db",
                username="test_user",
                password=SecretStr("test_password"),
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_validate_port_above_range_raises_error(self):
        """Test that port above valid range raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDatabaseSecureConfig(
                host="localhost",
                port=65536,
                database="test_db",
                username="test_user",
                password=SecretStr("test_password"),
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_validate_database_name_valid(self):
        """Test validation of valid database name."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="my_test_db_2024",
            username="test_user",
            password=SecretStr("test_password"),
        )
        assert config.database == "my_test_db_2024"

    def test_validate_database_name_empty_raises_error(self):
        """Test that empty database name raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDatabaseSecureConfig(
                host="localhost",
                port=5432,
                database="",
                username="test_user",
                password=SecretStr("test_password"),
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "cannot be empty" in str(exc_info.value)

    def test_validate_database_name_sql_injection_patterns(self):
        """Test that SQL injection patterns are rejected."""
        dangerous_patterns = ["test_db;DROP TABLE", "test_db--", "test/**/db"]
        for pattern in dangerous_patterns:
            with pytest.raises(ModelOnexError) as exc_info:
                ModelDatabaseSecureConfig(
                    host="localhost",
                    port=5432,
                    database=pattern,
                    username="test_user",
                    password=SecretStr("test_password"),
                )
            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert "dangerous pattern" in str(exc_info.value)

    def test_validate_driver_postgresql(self):
        """Test driver normalization for PostgreSQL."""
        for driver_alias in ["postgresql", "postgres", "pg", "psql"]:
            config = ModelDatabaseSecureConfig(
                host="localhost",
                port=5432,
                database="test_db",
                username="test_user",
                password=SecretStr("test_password"),
                driver=driver_alias,
            )
            assert config.driver == "postgresql"

    def test_validate_driver_mysql(self):
        """Test driver normalization for MySQL."""
        for driver_alias in ["mysql", "mariadb"]:
            config = ModelDatabaseSecureConfig(
                host="localhost",
                port=3306,
                database="test_db",
                username="test_user",
                password=SecretStr("test_password"),
                driver=driver_alias,
            )
            assert config.driver == "mysql"

    def test_validate_driver_sqlite(self):
        """Test driver normalization for SQLite."""
        for driver_alias in ["sqlite", "sqlite3"]:
            config = ModelDatabaseSecureConfig(
                host="localhost",
                port=0,
                database="/path/to/db.sqlite",
                username="sqlite",
                password=SecretStr(""),
                driver=driver_alias,
            )
            assert config.driver == "sqlite"

    def test_validate_driver_oracle(self):
        """Test driver normalization for Oracle."""
        for driver_alias in ["oracle", "ora"]:
            config = ModelDatabaseSecureConfig(
                host="localhost",
                port=1521,
                database="test_db",
                username="test_user",
                password=SecretStr("test_password"),
                driver=driver_alias,
            )
            assert config.driver == "oracle"

    def test_validate_driver_mssql(self):
        """Test driver normalization for SQL Server."""
        for driver_alias in ["mssql", "sqlserver"]:
            config = ModelDatabaseSecureConfig(
                host="localhost",
                port=1433,
                database="test_db",
                username="test_user",
                password=SecretStr("test_password"),
                driver=driver_alias,
            )
            assert config.driver == "mssql"

    def test_validate_driver_mongodb(self):
        """Test driver normalization for MongoDB."""
        for driver_alias in ["mongodb", "mongo"]:
            config = ModelDatabaseSecureConfig(
                host="localhost",
                port=27017,
                database="test_db",
                username="test_user",
                password=SecretStr("test_password"),
                driver=driver_alias,
            )
            assert config.driver == "mongodb"

    def test_validate_driver_invalid_raises_error(self):
        """Test that invalid driver raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDatabaseSecureConfig(
                host="localhost",
                port=5432,
                database="test_db",
                username="test_user",
                password=SecretStr("test_password"),
                driver="invalid_db",
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Unsupported driver" in str(exc_info.value)


class TestConnectionStringGeneration:
    """Tests for connection string generation."""

    def test_postgresql_connection_string_basic(self):
        """Test basic PostgreSQL connection string generation."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
        )
        conn_str = config.get_connection_string()
        assert "postgresql://" in conn_str
        assert "host=localhost" in conn_str
        assert "port=5432" in conn_str
        assert "dbname=test_db" in conn_str
        assert "user=test_user" in conn_str
        assert "password=test_password" in conn_str

    def test_postgresql_connection_string_with_ssl(self):
        """Test PostgreSQL connection string with SSL."""
        config = ModelDatabaseSecureConfig(
            host="db.example.com",
            port=5432,
            database="prod_db",
            username="app_user",
            password=SecretStr("secure_pass"),
            driver="postgresql",
            ssl_enabled=True,
            ssl_mode="verify-full",
            ssl_cert_path="/certs/client.crt",
            ssl_key_path="/certs/client.key",
            ssl_ca_path="/certs/ca.crt",
        )
        conn_str = config.get_connection_string()
        assert "sslmode=verify-full" in conn_str
        assert "sslcert=/certs/client.crt" in conn_str
        assert "sslkey=/certs/client.key" in conn_str
        assert "sslrootcert=/certs/ca.crt" in conn_str

    def test_postgresql_connection_string_with_schema(self):
        """Test PostgreSQL connection string with schema."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
            db_schema="custom_schema",
        )
        conn_str = config.get_connection_string()
        assert "options=-c search_path=custom_schema" in conn_str

    def test_postgresql_connection_string_masked_password(self):
        """Test PostgreSQL connection string with masked password."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("secret_password"),
            driver="postgresql",
        )
        conn_str = config.get_connection_string(mask_password=True)
        assert "password=***MASKED***" in conn_str
        assert "secret_password" not in conn_str

    def test_mysql_connection_string_basic(self):
        """Test basic MySQL connection string generation."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=3306,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="mysql",
        )
        conn_str = config.get_connection_string()
        assert "mysql://" in conn_str
        assert "test_user:test_password@localhost:3306/test_db" in conn_str

    def test_mysql_connection_string_with_ssl(self):
        """Test MySQL connection string with SSL."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=3306,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="mysql",
            ssl_enabled=True,
            ssl_mode="require",
        )
        conn_str = config.get_connection_string()
        assert "ssl_mode=REQUIRE" in conn_str

    def test_sqlite_connection_string(self):
        """Test SQLite connection string generation."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=0,
            database="/path/to/database.db",
            username="sqlite",
            password=SecretStr(""),
            driver="sqlite",
        )
        conn_str = config.get_connection_string()
        assert conn_str == "sqlite:////path/to/database.db"

    def test_oracle_connection_string(self):
        """Test Oracle connection string generation."""
        config = ModelDatabaseSecureConfig(
            host="oracle.example.com",
            port=1521,
            database="ORCL",
            username="system",
            password=SecretStr("oracle_pass"),
            driver="oracle",
        )
        conn_str = config.get_connection_string()
        assert conn_str == "oracle://system:oracle_pass@oracle.example.com:1521/ORCL"

    def test_mssql_connection_string(self):
        """Test SQL Server connection string generation."""
        config = ModelDatabaseSecureConfig(
            host="mssql.example.com",
            port=1433,
            database="test_db",
            username="sa",
            password=SecretStr("mssql_pass"),
            driver="mssql",
        )
        conn_str = config.get_connection_string()
        assert "mssql://?" in conn_str
        assert "SERVER=mssql.example.com,1433" in conn_str
        assert "DATABASE=test_db" in conn_str
        assert "UID=sa" in conn_str
        assert "PWD=mssql_pass" in conn_str

    def test_mssql_connection_string_with_ssl(self):
        """Test SQL Server connection string with SSL."""
        config = ModelDatabaseSecureConfig(
            host="mssql.example.com",
            port=1433,
            database="test_db",
            username="sa",
            password=SecretStr("mssql_pass"),
            driver="mssql",
            ssl_enabled=True,
        )
        conn_str = config.get_connection_string()
        assert "Encrypt=yes" in conn_str
        assert "TrustServerCertificate=no" in conn_str

    def test_mongodb_connection_string(self):
        """Test MongoDB connection string generation."""
        config = ModelDatabaseSecureConfig(
            host="mongo.example.com",
            port=27017,
            database="test_db",
            username="mongo_user",
            password=SecretStr("mongo_pass"),
            driver="mongodb",
            application_name="TestApp",
        )
        conn_str = config.get_connection_string()
        assert (
            "mongodb://mongo_user:mongo_pass@mongo.example.com:27017/test_db"
            in conn_str
        )
        assert "appName=TestApp" in conn_str

    def test_mongodb_connection_string_with_ssl(self):
        """Test MongoDB connection string with SSL."""
        config = ModelDatabaseSecureConfig(
            host="mongo.example.com",
            port=27017,
            database="test_db",
            username="mongo_user",
            password=SecretStr("mongo_pass"),
            driver="mongodb",
            ssl_enabled=True,
        )
        conn_str = config.get_connection_string()
        assert "ssl=true" in conn_str


class TestConnectionStringParsing:
    """Tests for connection string parsing."""

    def test_parse_postgresql_connection_string(self):
        """Test parsing PostgreSQL connection string."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
        )
        conn_str = "postgresql://test_user:test_pass@localhost:5432/test_db"
        parsed = config.parse_connection_string(conn_str)
        assert parsed.scheme == "postgresql"
        assert parsed.host == "localhost"
        assert parsed.port == 5432
        assert parsed.username == "test_user"
        assert parsed.database == "test_db"

    def test_parse_mysql_connection_string(self):
        """Test parsing MySQL connection string."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=3306,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="mysql",
        )
        conn_str = "mysql://root:password@localhost:3306/mydb"
        parsed = config.parse_connection_string(conn_str)
        assert parsed.scheme == "mysql"
        assert parsed.host == "localhost"
        assert parsed.port == 3306
        assert parsed.database == "mydb"


class TestSecurityAssessment:
    """Tests for security assessment functionality."""

    def test_security_assessment_no_ssl(self):
        """Test security assessment without SSL."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
            ssl_enabled=False,
        )
        assessment = config.get_security_assessment()
        assert assessment["security_level"] == "basic"
        assert assessment["encryption_in_transit"] is False
        assert "No encryption" in " ".join(assessment["vulnerabilities"])
        assert "Enable SSL/TLS" in " ".join(assessment["recommendations"])

    def test_security_assessment_with_ssl_weak_mode(self):
        """Test security assessment with weak SSL mode."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
            ssl_enabled=True,
            ssl_mode="allow",
        )
        assessment = config.get_security_assessment()
        assert assessment["security_level"] == "medium"
        assert "Weak SSL mode" in " ".join(assessment["vulnerabilities"])

    def test_security_assessment_with_ssl_verify_full(self):
        """Test security assessment with verify-full SSL mode."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("strong_password_123456"),
            driver="postgresql",
            ssl_enabled=True,
            ssl_mode="verify-full",
        )
        assessment = config.get_security_assessment()
        assert assessment["security_level"] == "high"
        assert assessment["encryption_in_transit"] is True

    def test_security_assessment_weak_password(self):
        """Test security assessment with weak password."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("short"),
            driver="postgresql",
        )
        assessment = config.get_security_assessment()
        assert "Weak password" in " ".join(assessment["vulnerabilities"])

    def test_security_assessment_common_password(self):
        """Test security assessment with common password."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("password"),
            driver="postgresql",
        )
        assessment = config.get_security_assessment()
        assert "common/default password" in " ".join(assessment["vulnerabilities"])

    def test_security_assessment_postgres_superuser(self):
        """Test security assessment warns about postgres superuser."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="postgres",
            password=SecretStr("secure_password_123"),
            driver="postgresql",
        )
        assessment = config.get_security_assessment()
        assert any("postgres" in rec for rec in assessment["recommendations"])

    def test_security_assessment_mysql_root_user(self):
        """Test security assessment warns about MySQL root user."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=3306,
            database="test_db",
            username="root",
            password=SecretStr("secure_password_123"),
            driver="mysql",
        )
        assessment = config.get_security_assessment()
        assert any("root" in rec for rec in assessment["recommendations"])

    def test_security_assessment_compliance_status(self):
        """Test security assessment compliance status."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("very_secure_password_123"),
            driver="postgresql",
            ssl_enabled=True,
            ssl_mode="verify-full",
        )
        assessment = config.get_security_assessment()
        assert "pci_dss" in assessment["compliance_status"]
        assert "hipaa" in assessment["compliance_status"]
        assert "gdpr" in assessment["compliance_status"]

    def test_is_production_ready_without_ssl(self):
        """Test production readiness without SSL."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("secure_password_123"),
            driver="postgresql",
            ssl_enabled=False,
        )
        assert config.is_production_ready() is False

    def test_is_production_ready_with_weak_password(self):
        """Test production readiness with weak password."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("password"),
            driver="postgresql",
            ssl_enabled=True,
        )
        assert config.is_production_ready() is False

    def test_is_production_ready_secure_config(self):
        """Test production readiness with secure configuration."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("very_secure_password_123"),
            driver="postgresql",
            ssl_enabled=True,
            ssl_mode="verify-full",
        )
        assert config.is_production_ready() is True


class TestPoolRecommendations:
    """Tests for connection pool recommendations."""

    def test_pool_recommendations_basic(self):
        """Test basic pool recommendations."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
        )
        recommendations = config.get_pool_recommendations()
        assert recommendations.recommended_pool_size == 10
        assert recommendations.recommended_max_overflow == 20
        assert recommendations.recommended_pool_timeout == 30

    def test_pool_recommendations_small_pool(self):
        """Test recommendations for small pool size."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
            pool_size=3,
        )
        recommendations = config.get_pool_recommendations()
        assert any(
            "increasing pool_size" in rec for rec in recommendations.recommendations
        )

    def test_pool_recommendations_large_pool(self):
        """Test recommendations for large pool size."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
            pool_size=60,
        )
        recommendations = config.get_pool_recommendations()
        assert any(
            "resource contention" in rec for rec in recommendations.recommendations
        )

    def test_pool_recommendations_no_overflow(self):
        """Test recommendations when max_overflow is zero."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
            max_overflow=0,
        )
        recommendations = config.get_pool_recommendations()
        assert any("max_overflow" in rec for rec in recommendations.recommendations)

    def test_pool_recommendations_postgresql_profile(self):
        """Test PostgreSQL-specific pool recommendations."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
        )
        recommendations = config.get_pool_recommendations()
        assert "performance_profile" in recommendations.model_dump()

    def test_pool_recommendations_mysql_profile(self):
        """Test MySQL-specific pool recommendations."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=3306,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="mysql",
        )
        recommendations = config.get_pool_recommendations()
        assert "performance_profile" in recommendations.model_dump()


class TestPerformanceProfile:
    """Tests for performance profiling."""

    def test_performance_profile_basic(self):
        """Test basic performance profile."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
        )
        profile = config.get_performance_profile()
        assert "latency_characteristics" in profile
        assert "throughput_optimization" in profile
        assert "resource_usage" in profile
        assert "monitoring_recommendations" in profile

    def test_latency_profile_with_ssl(self):
        """Test latency profile with SSL enabled."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
            ssl_enabled=True,
        )
        profile = config.get_performance_profile()
        latency = profile["latency_characteristics"]
        assert latency.connection_latency == "medium"
        assert "SSL handshake" in " ".join(latency.factors)

    def test_throughput_recommendations_postgresql(self):
        """Test throughput recommendations for PostgreSQL."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
        )
        profile = config.get_performance_profile()
        recommendations = profile["throughput_optimization"]
        assert any("PgBouncer" in rec for rec in recommendations)

    def test_resource_usage_large_pool(self):
        """Test resource usage profile with large pool."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
            pool_size=25,
        )
        profile = config.get_performance_profile()
        resource_usage = profile["resource_usage"]
        assert resource_usage["memory_usage"] == "high"

    def test_resource_usage_sqlite(self):
        """Test resource usage profile for SQLite."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=0,
            database="/path/to/db.sqlite",
            username="sqlite",
            password=SecretStr(""),
            driver="sqlite",
        )
        profile = config.get_performance_profile()
        resource_usage = profile["resource_usage"]
        assert resource_usage["network_usage"] == "none"

    def test_monitoring_recommendations(self):
        """Test monitoring recommendations."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
            ssl_enabled=True,
        )
        profile = config.get_performance_profile()
        recommendations = profile["monitoring_recommendations"]
        assert any("SSL certificate expiration" in rec for rec in recommendations)


class TestHealthAndTroubleshooting:
    """Tests for health checks and troubleshooting."""

    def test_can_connect_valid_credentials(self):
        """Test can_connect with valid credentials."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("secure_password_123"),
            driver="postgresql",
        )
        # Note: This tests credential validation, not actual DB connection
        assert config.can_connect() is True

    def test_can_connect_with_ssl_missing_files(self):
        """Test can_connect with SSL but missing certificate files."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("secure_password_123"),
            driver="postgresql",
            ssl_enabled=True,
            ssl_cert_path="/nonexistent/cert.pem",
        )
        assert config.can_connect() is False

    def test_troubleshooting_guide_structure(self):
        """Test troubleshooting guide structure."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
        )
        guide = config.get_troubleshooting_guide()
        assert "connection_failures" in guide
        assert "ssl_issues" in guide
        assert "authentication_failures" in guide
        assert "performance_issues" in guide
        assert "driver_specific" in guide

    def test_troubleshooting_guide_postgresql(self):
        """Test PostgreSQL-specific troubleshooting."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="postgresql",
        )
        guide = config.get_troubleshooting_guide()
        assert any("pg_hba.conf" in tip for tip in guide["driver_specific"])

    def test_troubleshooting_guide_mysql(self):
        """Test MySQL-specific troubleshooting."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=3306,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            driver="mysql",
        )
        guide = config.get_troubleshooting_guide()
        assert any("bind-address" in tip for tip in guide["driver_specific"])


class TestEnvironmentIntegration:
    """Tests for environment variable integration."""

    @patch.dict(
        os.environ,
        {
            "ONEX_DB_HOST": "env.example.com",
            "ONEX_DB_PORT": "5432",
            "ONEX_DB_DATABASE": "env_db",
            "ONEX_DB_USERNAME": "env_user",
            "ONEX_DB_PASSWORD": "env_password",
        },
    )
    def test_load_from_env_basic(self):
        """Test loading configuration from environment variables."""
        config = ModelDatabaseSecureConfig.load_from_env(env_prefix="ONEX_DB_")
        assert config.host == "env.example.com"
        assert config.port == 5432
        assert config.database == "env_db"
        assert config.username == "env_user"
        assert config.password.get_secret_value() == "env_password"

    @patch.dict(
        os.environ,
        {
            "CUSTOM_HOST": "custom.example.com",
            "CUSTOM_PORT": "3306",
            "CUSTOM_DATABASE": "custom_db",
            "CUSTOM_USERNAME": "custom_user",
            "CUSTOM_PASSWORD": "custom_pass",
            "CUSTOM_DRIVER": "mysql",
        },
    )
    def test_load_from_env_custom_prefix(self):
        """Test loading with custom prefix."""
        config = ModelDatabaseSecureConfig.load_from_env(env_prefix="CUSTOM_")
        assert config.host == "custom.example.com"
        assert config.driver == "mysql"

    def test_load_from_env_missing_password(self):
        """Test loading fails when password is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ModelOnexError) as exc_info:
                ModelDatabaseSecureConfig.load_from_env(env_prefix="MISSING_")
            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert "password required" in str(exc_info.value).lower()

    @patch.dict(
        os.environ,
        {
            "SSL_HOST": "ssl.example.com",
            "SSL_PASSWORD": "ssl_pass",
            "SSL_SSL_ENABLED": "true",
            "SSL_SSL_MODE": "verify-full",
            "SSL_SSL_CERT_PATH": "/certs/client.crt",
        },
    )
    def test_load_from_env_with_ssl(self):
        """Test loading SSL configuration from environment."""
        config = ModelDatabaseSecureConfig.load_from_env(env_prefix="SSL_")
        assert config.ssl_enabled is True
        assert config.ssl_mode == "verify-full"
        assert config.ssl_cert_path == "/certs/client.crt"


class TestFactoryMethods:
    """Tests for factory methods."""

    def test_create_postgresql(self):
        """Test PostgreSQL factory method."""
        config = ModelDatabaseSecureConfig.create_postgresql(
            host="pg.example.com",
            port=5433,
            database="mydb",
            username="pguser",
            password="pgpass",  # noqa: S106 - Test data, not actual password
        )
        assert config.driver == "postgresql"
        assert config.host == "pg.example.com"
        assert config.port == 5433
        assert config.database == "mydb"

    def test_create_postgresql_without_password_raises_error(self):
        """Test PostgreSQL factory without password raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDatabaseSecureConfig.create_postgresql(
                host="localhost",
                database="test_db",
                username="test_user",
                password=None,
            )
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_create_mysql(self):
        """Test MySQL factory method."""
        config = ModelDatabaseSecureConfig.create_mysql(
            host="mysql.example.com",
            port=3307,
            database="mydb",
            username="mysqluser",
            password="mysqlpass",  # noqa: S106 - Test data, not actual password
        )
        assert config.driver == "mysql"
        assert config.host == "mysql.example.com"
        assert config.port == 3307

    def test_create_sqlite(self):
        """Test SQLite factory method."""
        config = ModelDatabaseSecureConfig.create_sqlite(database_path="/data/app.db")
        assert config.driver == "sqlite"
        assert config.database == "/data/app.db"

    def test_create_production_postgresql(self):
        """Test production PostgreSQL factory method."""
        config = ModelDatabaseSecureConfig.create_production_postgresql(
            host="prod.example.com",
            database="prod_db",
            username="prod_user",
            password="very_secure_password",  # noqa: S106 - Test data, not actual password
            ssl_cert_path="/certs/client.crt",
            ssl_key_path="/certs/client.key",
            ssl_ca_path="/certs/ca.crt",
        )
        assert config.driver == "postgresql"
        assert config.ssl_enabled is True
        assert config.ssl_mode == "verify-full"
        assert config.pool_size == 20
        assert config.max_overflow == 30


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_minimum_pool_size(self):
        """Test minimum pool size boundary."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            pool_size=1,
        )
        assert config.pool_size == 1

    def test_maximum_pool_size(self):
        """Test maximum pool size boundary."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            pool_size=100,
        )
        assert config.pool_size == 100

    def test_minimum_port(self):
        """Test minimum port boundary."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=1,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
        )
        assert config.port == 1

    def test_maximum_port(self):
        """Test maximum port boundary."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=65535,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
        )
        assert config.port == 65535

    def test_empty_password_validation(self):
        """Test empty password is allowed but flagged."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr(""),
            driver="postgresql",
        )
        assessment = config.get_credential_strength_assessment()
        assert assessment.strength_score == 0

    def test_very_long_password(self):
        """Test very long password."""
        long_password = "a" * 256
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr(long_password),
            driver="postgresql",
        )
        assert config.password.get_secret_value() == long_password

    def test_special_characters_in_database_name(self):
        """Test valid special characters in database name."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db_2024",
            username="test_user",
            password=SecretStr("test_password"),
        )
        assert config.database == "test_db_2024"

    def test_unicode_in_application_name(self):
        """Test Unicode characters in application name."""
        config = ModelDatabaseSecureConfig(
            host="localhost",
            port=5432,
            database="test_db",
            username="test_user",
            password=SecretStr("test_password"),
            application_name="MyApp™",
        )
        assert config.application_name == "MyApp™"
