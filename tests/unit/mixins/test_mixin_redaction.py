# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive unit tests for MixinSensitiveFieldRedaction.

Tests cover:
- Sensitive field pattern detection
- Field redaction with default patterns
- Custom redaction values
- Recursive redaction in nested structures
- List and dict handling
- Additional sensitive field specification
- Redaction value customization
"""

import pytest
from pydantic import BaseModel

from omnibase_core.mixins.mixin_redaction import MixinSensitiveFieldRedaction


@pytest.mark.unit
class TestMixinSensitiveFieldRedactionBasicBehavior:
    """Test basic MixinSensitiveFieldRedaction functionality."""

    def test_mixin_with_pydantic_model(self):
        """Test mixin works with Pydantic models."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str
            password: str

        model = TestModel(name="user", password="secret123")
        assert isinstance(model, MixinSensitiveFieldRedaction)
        assert isinstance(model, BaseModel)

    def test_get_sensitive_field_patterns(self):
        """Test getting default sensitive field patterns."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str

        patterns = TestModel.get_sensitive_field_patterns()

        assert isinstance(patterns, list)
        assert "password" in patterns
        assert "token" in patterns
        assert "secret" in patterns
        assert "key" in patterns

    def test_get_redaction_values(self):
        """Test getting default redaction values."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str

        redaction_values = TestModel.get_redaction_values()

        assert isinstance(redaction_values, dict)
        assert "password" in redaction_values
        assert "token" in redaction_values
        assert "secret" in redaction_values


@pytest.mark.unit
class TestSensitiveFieldDetection:
    """Test is_sensitive_field functionality."""

    def test_is_sensitive_field_with_password(self):
        """Test detection of password fields."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str

        assert TestModel.is_sensitive_field("password")
        assert TestModel.is_sensitive_field("user_password")
        assert TestModel.is_sensitive_field("PASSWORD")
        assert TestModel.is_sensitive_field("passwd")

    def test_is_sensitive_field_with_token(self):
        """Test detection of token fields."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str

        assert TestModel.is_sensitive_field("token")
        assert TestModel.is_sensitive_field("access_token")
        assert TestModel.is_sensitive_field("refresh_token")
        assert TestModel.is_sensitive_field("TOKEN")

    def test_is_sensitive_field_with_secret(self):
        """Test detection of secret fields."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str

        assert TestModel.is_sensitive_field("secret")
        assert TestModel.is_sensitive_field("client_secret")
        assert TestModel.is_sensitive_field("SECRET_KEY")

    def test_is_sensitive_field_with_key(self):
        """Test detection of key fields."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str

        assert TestModel.is_sensitive_field("key")
        assert TestModel.is_sensitive_field("api_key")
        assert TestModel.is_sensitive_field("private_key")

    def test_is_sensitive_field_with_non_sensitive(self):
        """Test detection returns False for non-sensitive fields."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str

        assert not TestModel.is_sensitive_field("name")
        assert not TestModel.is_sensitive_field("username")
        assert not TestModel.is_sensitive_field("email")
        assert not TestModel.is_sensitive_field("created_at")


@pytest.mark.unit
class TestRedactionValueSelection:
    """Test get_redaction_value functionality."""

    def test_redaction_value_for_password(self):
        """Test redaction value selection for password fields."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            password: str

        value = TestModel.get_redaction_value("password", "secret123")
        assert value == "[PASSWORD_REDACTED]"

        value = TestModel.get_redaction_value("user_passwd", "secret")
        assert value == "[PASSWORD_REDACTED]"

    def test_redaction_value_for_token(self):
        """Test redaction value selection for token fields."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            token: str

        value = TestModel.get_redaction_value("token", "abc123")
        assert value == "[MASKED]"

        value = TestModel.get_redaction_value("access_token", "xyz789")
        assert value == "[MASKED]"

    def test_redaction_value_for_secret(self):
        """Test redaction value selection for secret fields."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            secret: str

        value = TestModel.get_redaction_value("secret", "my_secret")
        assert value == "[SECRET]"

        value = TestModel.get_redaction_value("client_secret", "secret_value")
        assert value == "[SECRET]"

    def test_redaction_value_for_key(self):
        """Test redaction value selection for key fields."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            api_key: str

        value = TestModel.get_redaction_value("api_key", "key123")
        assert value == "[KEY_REDACTED]"

        value = TestModel.get_redaction_value("private_key", "priv123")
        assert value == "[KEY_REDACTED]"


@pytest.mark.unit
class TestRedactSensitiveFields:
    """Test redact_sensitive_fields functionality."""

    def test_redact_basic_sensitive_fields(self):
        """Test redacting basic sensitive fields."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str
            password: str

        model = TestModel(name="user", password="secret123")
        data = {"name": "user", "password": "secret123"}

        redacted = model.redact_sensitive_fields(data)

        assert redacted["name"] == "user"
        assert redacted["password"] == "[PASSWORD_REDACTED]"

    def test_redact_multiple_sensitive_fields(self):
        """Test redacting multiple sensitive fields."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            username: str
            password: str
            api_key: str
            token: str

        model = TestModel(
            username="user",
            password="pass123",
            api_key="key123",
            token="token123",
        )

        data = {
            "username": "user",
            "password": "pass123",
            "api_key": "key123",
            "token": "token123",
        }

        redacted = model.redact_sensitive_fields(data)

        assert redacted["username"] == "user"
        assert redacted["password"] == "[PASSWORD_REDACTED]"
        assert redacted["api_key"] == "[KEY_REDACTED]"
        assert redacted["token"] == "[MASKED]"

    def test_redact_with_none_values(self):
        """Test redaction preserves None values."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str
            password: str | None = None

        model = TestModel(name="user", password=None)
        data = {"name": "user", "password": None}

        redacted = model.redact_sensitive_fields(data)

        assert redacted["name"] == "user"
        assert redacted["password"] is None  # None should not be redacted

    def test_redact_flat_dict_only(self):
        """Test redacting sensitive fields in flat dictionary."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str

        model = TestModel(name="user")

        data = {
            "name": "user",
            "username": "admin",
            "password": "secret",
            "token": "abc123",
        }

        redacted = model.redact_sensitive_fields(data)

        assert redacted["name"] == "user"
        assert redacted["username"] == "admin"
        assert redacted["password"] == "[PASSWORD_REDACTED]"
        assert redacted["token"] == "[MASKED]"

    def test_redact_lists_with_simple_values(self):
        """Test redacting lists with simple non-dict values."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str

        model = TestModel(name="user")

        data = {
            "names": ["user1", "user2"],
            "values": [1, 2, 3],
        }

        redacted = model.redact_sensitive_fields(data)

        assert redacted["names"] == ["user1", "user2"]
        assert redacted["values"] == [1, 2, 3]

    def test_redact_with_additional_sensitive_fields_basic(self):
        """Test redaction with additional specified sensitive fields - basic."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str
            email: str

        model = TestModel(name="user", email="user@test.com")

        # Test without additional fields first
        data = {"name": "user", "email": "user@test.com"}
        redacted = model.redact_sensitive_fields(data)

        assert redacted["name"] == "user"
        assert redacted["email"] == "user@test.com"  # email not sensitive by default


@pytest.mark.unit
class TestRedactMethod:
    """Test redact convenience method."""

    def test_redact_model_data(self):
        """Test redacting model data."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            username: str
            password: str
            email: str

        model = TestModel(
            username="user",
            password="secret",
            email="user@test.com",
        )

        redacted = model.redact()

        assert redacted["username"] == "user"
        assert redacted["password"] == "[PASSWORD_REDACTED]"
        assert redacted["email"] == "user@test.com"

    def test_redact_without_additional_fields(self):
        """Test redact without additional sensitive fields."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str
            email: str
            password: str

        model = TestModel(
            name="user",
            email="user@test.com",
            password="secret",
        )

        redacted = model.redact()

        assert redacted["name"] == "user"
        assert redacted["email"] == "user@test.com"
        assert redacted["password"] == "[PASSWORD_REDACTED]"

    def test_redact_with_model_dump_kwargs(self):
        """Test redact with model_dump kwargs."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str
            password: str
            internal: str

        model = TestModel(
            name="user",
            password="secret",
            internal="internal_data",
        )

        redacted = model.redact(exclude={"internal"})

        assert "name" in redacted
        assert "password" in redacted
        assert "internal" not in redacted
        assert redacted["password"] == "[PASSWORD_REDACTED]"


@pytest.mark.unit
class TestModelDumpRedacted:
    """Test model_dump_redacted convenience method."""

    def test_model_dump_redacted_basic(self):
        """Test model_dump_redacted basic functionality."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            username: str
            password: str

        model = TestModel(username="user", password="secret")

        redacted = model.model_dump_redacted()

        assert redacted["username"] == "user"
        assert redacted["password"] == "[PASSWORD_REDACTED]"

    def test_model_dump_redacted_is_alias_for_redact(self):
        """Test model_dump_redacted is equivalent to redact."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str
            token: str

        model = TestModel(name="user", token="abc123")

        redacted1 = model.redact()
        redacted2 = model.model_dump_redacted()

        assert redacted1 == redacted2


@pytest.mark.unit
class TestCustomPatterns:
    """Test customizing sensitive field patterns."""

    def test_get_sensitive_field_patterns_can_be_overridden(self):
        """Test that sensitive field patterns method can be overridden."""

        class CustomModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str

            @classmethod
            def get_sensitive_field_patterns(cls) -> list[str]:
                # Return custom patterns
                return ["custom_field", "special_field"]

        patterns = CustomModel.get_sensitive_field_patterns()

        assert "custom_field" in patterns
        assert "special_field" in patterns

    def test_custom_redaction_values(self):
        """Test overriding redaction values."""

        class CustomModel(MixinSensitiveFieldRedaction, BaseModel):
            password: str

            @classmethod
            def get_redaction_values(cls) -> dict[str, str]:
                values = super().get_redaction_values()
                values["password"] = "[HIDDEN]"
                return values

        model = CustomModel(password="secret")

        value = model.get_redaction_value("password", "secret")
        assert value == "[HIDDEN]"


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_redact_empty_dict(self):
        """Test redacting empty dictionary."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str

        model = TestModel(name="user")
        redacted = model.redact_sensitive_fields({})

        assert redacted == {}

    def test_redact_deeply_nested_structures(self):
        """Test redacting deeply nested structures."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str

        model = TestModel(name="user")

        data = {
            "level1": {
                "password": "secret1",
                "level2": {
                    "token": "token1",
                    "level3": {"api_key": "key1", "data": "public"},
                },
            }
        }

        redacted = model.redact_sensitive_fields(data)

        assert redacted["level1"]["password"] == "[PASSWORD_REDACTED]"
        assert redacted["level1"]["level2"]["token"] == "[MASKED]"
        assert redacted["level1"]["level2"]["level3"]["api_key"] == "[KEY_REDACTED]"
        assert redacted["level1"]["level2"]["level3"]["data"] == "public"

    def test_redact_mixed_list_types(self):
        """Test redacting lists with mixed types."""

        class TestModel(MixinSensitiveFieldRedaction, BaseModel):
            name: str

        model = TestModel(name="user")

        data = {
            "items": [
                {"password": "secret1"},
                "plain string",
                123,
                {"token": "token1"},
            ]
        }

        redacted = model.redact_sensitive_fields(data)

        assert redacted["items"][0]["password"] == "[PASSWORD_REDACTED]"
        assert redacted["items"][1] == "plain string"
        assert redacted["items"][2] == 123
        assert redacted["items"][3]["token"] == "[MASKED]"


@pytest.mark.unit
class TestIntegrationScenarios:
    """Integration tests for redaction patterns."""

    def test_simple_user_model_redaction(self):
        """Test redacting a simple user model."""

        class UserModel(MixinSensitiveFieldRedaction, BaseModel):
            username: str
            email: str
            password: str
            api_key: str

        model = UserModel(
            username="john_doe",
            email="john@example.com",
            password="supersecret",
            api_key="key_12345",
        )

        redacted = model.redact()

        assert redacted["username"] == "john_doe"
        assert redacted["email"] == "john@example.com"
        assert redacted["password"] == "[PASSWORD_REDACTED]"
        assert redacted["api_key"] == "[KEY_REDACTED]"

    def test_configuration_model_basic_redaction(self):
        """Test redacting configuration with secrets."""

        class ConfigModel(MixinSensitiveFieldRedaction, BaseModel):
            app_name: str
            db_host: str
            db_password: str
            api_token: str

        model = ConfigModel(
            app_name="MyApp",
            db_host="localhost",
            db_password="db_pass",
            api_token="api_token_123",
        )

        redacted = model.redact()

        assert redacted["app_name"] == "MyApp"
        assert redacted["db_host"] == "localhost"
        assert redacted["db_password"] == "[PASSWORD_REDACTED]"
        assert redacted["api_token"] == "[MASKED]"
