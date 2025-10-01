"""
Test suite for UUID utilities.

Provides comprehensive tests for deterministic UUID generation.
"""

import hashlib
from uuid import UUID

import pytest

from omnibase_core.utils.uuid_utilities import uuid_from_string


class TestUUIDFromString:
    """Test uuid_from_string function."""

    def test_deterministic_uuid_generation(self):
        """Test that same input produces same UUID."""
        input_str = "test_entity_123"
        uuid1 = uuid_from_string(input_str)
        uuid2 = uuid_from_string(input_str)

        assert uuid1 == uuid2
        assert isinstance(uuid1, UUID)
        assert isinstance(uuid2, UUID)

    def test_different_inputs_produce_different_uuids(self):
        """Test that different inputs produce different UUIDs."""
        uuid1 = uuid_from_string("entity_1")
        uuid2 = uuid_from_string("entity_2")

        assert uuid1 != uuid2

    def test_namespace_differentiation(self):
        """Test that different namespaces produce different UUIDs for same input."""
        input_str = "test_entity"
        uuid_default = uuid_from_string(input_str)
        uuid_custom = uuid_from_string(input_str, namespace="custom")

        assert uuid_default != uuid_custom

    def test_default_namespace(self):
        """Test that default namespace is 'omnibase'."""
        input_str = "test_entity"
        uuid_default = uuid_from_string(input_str)
        uuid_explicit = uuid_from_string(input_str, namespace="omnibase")

        assert uuid_default == uuid_explicit

    def test_empty_string_input(self):
        """Test UUID generation with empty string."""
        uuid_empty = uuid_from_string("")

        assert isinstance(uuid_empty, UUID)
        # Should still be deterministic
        assert uuid_empty == uuid_from_string("")

    def test_special_characters_in_input(self):
        """Test UUID generation with special characters."""
        special_inputs = [
            "entity@test.com",
            "entity#123",
            "entity with spaces",
            "entity/with/slashes",
            "entity\\with\\backslashes",
            "entity\twith\ttabs",
            "entity\nwith\nnewlines",
            "🎉emoji🎉",
        ]

        for input_str in special_inputs:
            uuid = uuid_from_string(input_str)
            assert isinstance(uuid, UUID)
            # Verify determinism
            assert uuid == uuid_from_string(input_str)

    def test_very_long_input_string(self):
        """Test UUID generation with very long input."""
        long_input = "x" * 10000
        uuid = uuid_from_string(long_input)

        assert isinstance(uuid, UUID)
        assert uuid == uuid_from_string(long_input)

    def test_unicode_characters(self):
        """Test UUID generation with unicode characters."""
        unicode_inputs = [
            "测试实体",
            "テストエンティティ",
            "тестовая сущность",
            "الكيان الاختبار",
        ]

        for input_str in unicode_inputs:
            uuid = uuid_from_string(input_str)
            assert isinstance(uuid, UUID)
            assert uuid == uuid_from_string(input_str)

    def test_uuid_format_validation(self):
        """Test that generated UUID follows proper format."""
        uuid = uuid_from_string("test")
        uuid_str = str(uuid)

        # UUID format: 8-4-4-4-12
        parts = uuid_str.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_uuid_consistency_across_namespaces(self):
        """Test that UUIDs remain consistent for namespace-input pairs."""
        test_cases = [
            ("entity1", "ns1"),
            ("entity1", "ns2"),
            ("entity2", "ns1"),
            ("entity2", "ns2"),
        ]

        # Generate UUIDs twice for each case
        first_run = [uuid_from_string(inp, ns) for inp, ns in test_cases]
        second_run = [uuid_from_string(inp, ns) for inp, ns in test_cases]

        assert first_run == second_run

    def test_sha256_based_generation(self):
        """Test that UUID is correctly derived from SHA-256 hash."""
        input_str = "test_entity"
        namespace = "omnibase"

        # Generate UUID using function
        generated_uuid = uuid_from_string(input_str, namespace)

        # Manually compute what the UUID should be
        combined = f"{namespace}:{input_str}"
        hash_obj = hashlib.sha256(combined.encode("utf-8"))
        hex_digest = hash_obj.hexdigest()
        uuid_hex = hex_digest[:32]
        expected_uuid_str = f"{uuid_hex[:8]}-{uuid_hex[8:12]}-{uuid_hex[12:16]}-{uuid_hex[16:20]}-{uuid_hex[20:32]}"
        expected_uuid = UUID(expected_uuid_str)

        assert generated_uuid == expected_uuid

    def test_collision_resistance(self):
        """Test that similar inputs produce different UUIDs."""
        similar_inputs = [
            "entity_123",
            "entity_124",
            "entity_223",
            "entity_1234",
            "entity_12",
        ]

        uuids = [uuid_from_string(inp) for inp in similar_inputs]

        # All UUIDs should be unique
        assert len(uuids) == len(set(uuids))

    def test_namespace_collision_resistance(self):
        """Test that namespace provides proper separation."""
        input_str = "entity"
        namespaces = ["ns1", "ns2", "ns3", "ns4", "ns5"]

        uuids = [uuid_from_string(input_str, ns) for ns in namespaces]

        # All UUIDs should be unique
        assert len(uuids) == len(set(uuids))

    def test_null_byte_handling(self):
        """Test UUID generation with null bytes."""
        input_with_null = "entity\x00with\x00null"
        uuid = uuid_from_string(input_with_null)

        assert isinstance(uuid, UUID)
        assert uuid == uuid_from_string(input_with_null)

    def test_numeric_string_input(self):
        """Test UUID generation with numeric strings."""
        numeric_inputs = ["123", "0", "-456", "3.14159", "1e10"]

        for input_str in numeric_inputs:
            uuid = uuid_from_string(input_str)
            assert isinstance(uuid, UUID)
            assert uuid == uuid_from_string(input_str)

    def test_namespace_with_special_characters(self):
        """Test namespace parameter with special characters."""
        input_str = "entity"
        special_namespaces = [
            "namespace@test",
            "namespace with spaces",
            "namespace/slash",
            "namespace:colon",
        ]

        for namespace in special_namespaces:
            uuid = uuid_from_string(input_str, namespace)
            assert isinstance(uuid, UUID)
            # Verify different from default namespace
            assert uuid != uuid_from_string(input_str)
