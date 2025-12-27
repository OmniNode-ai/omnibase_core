"""Tests for ModelGraphConnectionConfig."""

import pytest
from pydantic import SecretStr, ValidationError

from omnibase_core.models.graph.model_graph_connection_config import (
    ModelGraphConnectionConfig,
)


@pytest.mark.unit
class TestModelGraphConnectionConfigBasics:
    """Test basic ModelGraphConnectionConfig functionality."""

    def test_basic_initialization(self):
        """Test basic initialization with required fields only."""
        config = ModelGraphConnectionConfig(
            uri="bolt://localhost:7687",
        )

        assert config.uri == "bolt://localhost:7687"
        assert config.username is None
        assert config.password is None
        assert config.database is None
        assert config.pool_size == 50

    def test_full_initialization(self):
        """Test initialization with all fields."""
        config = ModelGraphConnectionConfig(
            uri="neo4j://db.example.com:7687",
            username="neo4j",
            password=SecretStr("secretpassword"),
            database="mydb",
            pool_size=100,
        )

        assert config.uri == "neo4j://db.example.com:7687"
        assert config.username == "neo4j"
        assert config.password is not None
        assert config.password.get_secret_value() == "secretpassword"
        assert config.database == "mydb"
        assert config.pool_size == 100

    def test_bolt_uri(self):
        """Test with bolt:// URI."""
        config = ModelGraphConnectionConfig(
            uri="bolt://localhost:7687",
            username="admin",
            password=SecretStr("pass"),
        )

        assert config.uri.startswith("bolt://")

    def test_neo4j_uri(self):
        """Test with neo4j:// URI."""
        config = ModelGraphConnectionConfig(
            uri="neo4j://cluster.example.com:7687",
        )

        assert config.uri.startswith("neo4j://")


@pytest.mark.unit
class TestModelGraphConnectionConfigValidation:
    """Test ModelGraphConnectionConfig validation."""

    def test_missing_required_uri(self):
        """Test that uri is required."""
        with pytest.raises(ValidationError):
            ModelGraphConnectionConfig()

    def test_pool_size_minimum(self):
        """Test pool_size minimum value."""
        config = ModelGraphConnectionConfig(
            uri="bolt://localhost:7687",
            pool_size=1,
        )
        assert config.pool_size == 1

        with pytest.raises(ValidationError):
            ModelGraphConnectionConfig(
                uri="bolt://localhost:7687",
                pool_size=0,
            )

    def test_pool_size_maximum(self):
        """Test pool_size maximum value."""
        config = ModelGraphConnectionConfig(
            uri="bolt://localhost:7687",
            pool_size=1000,
        )
        assert config.pool_size == 1000

        with pytest.raises(ValidationError):
            ModelGraphConnectionConfig(
                uri="bolt://localhost:7687",
                pool_size=1001,
            )

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            ModelGraphConnectionConfig(
                uri="bolt://localhost:7687",
                unknown_field="value",
            )


@pytest.mark.unit
class TestModelGraphConnectionConfigImmutability:
    """Test ModelGraphConnectionConfig immutability."""

    def test_frozen_model(self):
        """Test that model is frozen and cannot be modified."""
        config = ModelGraphConnectionConfig(
            uri="bolt://localhost:7687",
        )

        with pytest.raises(ValidationError):
            config.uri = "bolt://other:7687"


@pytest.mark.unit
class TestModelGraphConnectionConfigMethods:
    """Test ModelGraphConnectionConfig methods."""

    def test_get_masked_uri_no_embedded_credentials(self):
        """Test get_masked_uri when URI has no embedded credentials."""
        config = ModelGraphConnectionConfig(
            uri="bolt://localhost:7687",
        )

        masked = config.get_masked_uri()
        assert masked == "bolt://localhost:7687"

    def test_get_masked_uri_with_embedded_credentials(self):
        """Test get_masked_uri masks embedded credentials in URI."""
        config = ModelGraphConnectionConfig(
            uri="bolt://admin:secretpass@localhost:7687",
        )

        masked = config.get_masked_uri()
        # Credentials should be masked
        assert masked == "bolt://***:***@localhost:7687"
        # Original credentials should not appear
        assert "admin" not in masked
        assert "secretpass" not in masked

    def test_get_masked_uri_with_embedded_credentials_neo4j(self):
        """Test get_masked_uri with neo4j:// scheme."""
        config = ModelGraphConnectionConfig(
            uri="neo4j://user:password123@cluster.example.com:7687",
        )

        masked = config.get_masked_uri()
        assert masked == "neo4j://***:***@cluster.example.com:7687"
        assert "user" not in masked
        assert "password123" not in masked

    def test_get_masked_uri_separate_password_field(self):
        """Test that password in SecretStr field doesn't affect URI masking.

        The get_masked_uri method only masks credentials embedded in the URI,
        not the separate password field which is stored securely via SecretStr.
        """
        config = ModelGraphConnectionConfig(
            uri="bolt://localhost:7687",
            password=SecretStr("mypassword"),
        )

        masked = config.get_masked_uri()
        # URI has no embedded credentials, so it should be unchanged
        assert masked == "bolt://localhost:7687"


@pytest.mark.unit
class TestModelGraphConnectionConfigSerialization:
    """Test ModelGraphConnectionConfig serialization."""

    def test_model_dump(self):
        """Test model serialization to dict."""
        config = ModelGraphConnectionConfig(
            uri="bolt://localhost:7687",
            username="neo4j",
            database="mydb",
            pool_size=75,
        )

        data = config.model_dump()

        assert data["uri"] == "bolt://localhost:7687"
        assert data["username"] == "neo4j"
        assert data["database"] == "mydb"
        assert data["pool_size"] == 75

    def test_password_not_exposed_in_repr(self):
        """Test that password is not exposed in string representation."""
        config = ModelGraphConnectionConfig(
            uri="bolt://localhost:7687",
            password=SecretStr("secretpassword"),
        )

        repr_str = repr(config)
        assert "secretpassword" not in repr_str

    def test_model_dump_with_password(self):
        """Test model dump handles SecretStr properly."""
        config = ModelGraphConnectionConfig(
            uri="bolt://localhost:7687",
            password=SecretStr("secretpassword"),
        )

        data = config.model_dump()

        # SecretStr is preserved in the model_dump output
        assert data["password"] is not None
        # Verify we can access the secret value if needed
        assert isinstance(data["password"], SecretStr)
        assert data["password"].get_secret_value() == "secretpassword"
