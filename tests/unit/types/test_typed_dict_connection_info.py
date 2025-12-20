"""
Test suite for TypedDictConnectionInfo.
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from omnibase_core.types.typed_dict_connection_info import TypedDictConnectionInfo


@pytest.mark.unit
class TestTypedDictConnectionInfo:
    """Test TypedDictConnectionInfo functionality."""

    def test_typed_dict_connection_info_creation(self):
        """Test creating TypedDictConnectionInfo with all fields."""
        connection_id = uuid4()
        now = datetime.now()

        connection: TypedDictConnectionInfo = {
            "connection_id": connection_id,
            "connection_type": "websocket",
            "status": "connected",
            "established_at": now,
            "last_activity": now,
            "bytes_sent": 1024,
            "bytes_received": 2048,
        }

        assert connection["connection_id"] == connection_id
        assert connection["connection_type"] == "websocket"
        assert connection["status"] == "connected"
        assert connection["established_at"] == now
        assert connection["last_activity"] == now
        assert connection["bytes_sent"] == 1024
        assert connection["bytes_received"] == 2048

    def test_typed_dict_connection_info_different_connection_types(self):
        """Test TypedDictConnectionInfo with different connection types."""
        connection_types = ["websocket", "http", "tcp", "udp", "grpc", "rest"]

        for conn_type in connection_types:
            connection: TypedDictConnectionInfo = {
                "connection_id": uuid4(),
                "connection_type": conn_type,
                "status": "connected",
                "established_at": datetime.now(),
                "last_activity": datetime.now(),
                "bytes_sent": 0,
                "bytes_received": 0,
            }
            assert connection["connection_type"] == conn_type

    def test_typed_dict_connection_info_different_statuses(self):
        """Test TypedDictConnectionInfo with different statuses."""
        statuses = ["connected", "disconnected", "error", "connecting", "reconnecting"]

        for status in statuses:
            connection: TypedDictConnectionInfo = {
                "connection_id": uuid4(),
                "connection_type": "websocket",
                "status": status,
                "established_at": datetime.now(),
                "last_activity": datetime.now(),
                "bytes_sent": 0,
                "bytes_received": 0,
            }
            assert connection["status"] == status

    def test_typed_dict_connection_info_timestamp_formats(self):
        """Test TypedDictConnectionInfo with different timestamp formats."""
        now = datetime.now()
        specific_time = datetime(2024, 1, 15, 10, 30, 45)
        iso_time = datetime.fromisoformat("2024-01-01T12:00:00")

        # Test with current time
        connection1: TypedDictConnectionInfo = {
            "connection_id": uuid4(),
            "connection_type": "websocket",
            "status": "connected",
            "established_at": now,
            "last_activity": now,
            "bytes_sent": 100,
            "bytes_received": 200,
        }
        assert connection1["established_at"] == now
        assert connection1["last_activity"] == now

        # Test with specific time
        connection2: TypedDictConnectionInfo = {
            "connection_id": uuid4(),
            "connection_type": "http",
            "status": "connected",
            "established_at": specific_time,
            "last_activity": specific_time,
            "bytes_sent": 300,
            "bytes_received": 400,
        }
        assert connection2["established_at"] == specific_time
        assert connection2["last_activity"] == specific_time

        # Test with ISO time
        connection3: TypedDictConnectionInfo = {
            "connection_id": uuid4(),
            "connection_type": "tcp",
            "status": "connected",
            "established_at": iso_time,
            "last_activity": iso_time,
            "bytes_sent": 500,
            "bytes_received": 600,
        }
        assert connection3["established_at"] == iso_time
        assert connection3["last_activity"] == iso_time

    def test_typed_dict_connection_info_bytes_data(self):
        """Test TypedDictConnectionInfo with different byte values."""
        # Test with zero bytes
        connection: TypedDictConnectionInfo = {
            "connection_id": uuid4(),
            "connection_type": "websocket",
            "status": "connected",
            "established_at": datetime.now(),
            "last_activity": datetime.now(),
            "bytes_sent": 0,
            "bytes_received": 0,
        }
        assert connection["bytes_sent"] == 0
        assert connection["bytes_received"] == 0

        # Test with large byte values
        connection = {
            "connection_id": uuid4(),
            "connection_type": "websocket",
            "status": "connected",
            "established_at": datetime.now(),
            "last_activity": datetime.now(),
            "bytes_sent": 999999999,
            "bytes_received": 888888888,
        }
        assert connection["bytes_sent"] == 999999999
        assert connection["bytes_received"] == 888888888

    def test_typed_dict_connection_info_negative_bytes(self):
        """Test TypedDictConnectionInfo with negative byte values."""
        connection: TypedDictConnectionInfo = {
            "connection_id": uuid4(),
            "connection_type": "websocket",
            "status": "error",
            "established_at": datetime.now(),
            "last_activity": datetime.now(),
            "bytes_sent": -100,
            "bytes_received": -200,
        }
        assert connection["bytes_sent"] == -100
        assert connection["bytes_received"] == -200

    def test_typed_dict_connection_info_uuid_types(self):
        """Test TypedDictConnectionInfo with different UUID types."""
        # Test with generated UUID
        connection_id1 = uuid4()
        connection: TypedDictConnectionInfo = {
            "connection_id": connection_id1,
            "connection_type": "websocket",
            "status": "connected",
            "established_at": datetime.now(),
            "last_activity": datetime.now(),
            "bytes_sent": 0,
            "bytes_received": 0,
        }
        assert connection["connection_id"] == connection_id1
        assert isinstance(connection["connection_id"], UUID)

        # Test with specific UUID
        specific_uuid = UUID("12345678-1234-5678-9abc-123456789012")
        connection = {
            "connection_id": specific_uuid,
            "connection_type": "http",
            "status": "connected",
            "established_at": datetime.now(),
            "last_activity": datetime.now(),
            "bytes_sent": 0,
            "bytes_received": 0,
        }
        assert connection["connection_id"] == specific_uuid

    def test_typed_dict_connection_info_type_annotations(self):
        """Test that all fields have correct type annotations."""
        connection: TypedDictConnectionInfo = {
            "connection_id": uuid4(),
            "connection_type": "websocket",
            "status": "connected",
            "established_at": datetime.now(),
            "last_activity": datetime.now(),
            "bytes_sent": 1000,
            "bytes_received": 2000,
        }

        assert isinstance(connection["connection_id"], UUID)
        assert isinstance(connection["connection_type"], str)
        assert isinstance(connection["status"], str)
        assert isinstance(connection["established_at"], datetime)
        assert isinstance(connection["last_activity"], datetime)
        assert isinstance(connection["bytes_sent"], int)
        assert isinstance(connection["bytes_received"], int)

    def test_typed_dict_connection_info_mutability(self):
        """Test that TypedDictConnectionInfo behaves like a regular dict."""
        connection: TypedDictConnectionInfo = {
            "connection_id": uuid4(),
            "connection_type": "websocket",
            "status": "connected",
            "established_at": datetime.now(),
            "last_activity": datetime.now(),
            "bytes_sent": 100,
            "bytes_received": 200,
        }

        # Should be able to modify like a regular dict
        new_uuid = uuid4()
        new_time = datetime.now()
        connection["connection_id"] = new_uuid
        connection["status"] = "disconnected"
        connection["bytes_sent"] = 500
        connection["bytes_received"] = 600

        assert connection["connection_id"] == new_uuid
        assert connection["status"] == "disconnected"
        assert connection["bytes_sent"] == 500
        assert connection["bytes_received"] == 600

    def test_typed_dict_connection_info_equality(self):
        """Test equality comparison between instances."""
        base_uuid = uuid4()
        base_time = datetime(2024, 1, 1, 12, 0, 0)

        connection1: TypedDictConnectionInfo = {
            "connection_id": base_uuid,
            "connection_type": "websocket",
            "status": "connected",
            "established_at": base_time,
            "last_activity": base_time,
            "bytes_sent": 1000,
            "bytes_received": 2000,
        }

        connection2: TypedDictConnectionInfo = {
            "connection_id": base_uuid,
            "connection_type": "websocket",
            "status": "connected",
            "established_at": base_time,
            "last_activity": base_time,
            "bytes_sent": 1000,
            "bytes_received": 2000,
        }

        assert connection1 == connection2

        # Modify one field
        connection2["status"] = "disconnected"
        assert connection1 != connection2

    def test_typed_dict_connection_info_edge_cases(self):
        """Test edge cases for connection info."""
        # Test with minimum datetime
        connection: TypedDictConnectionInfo = {
            "connection_id": uuid4(),
            "connection_type": "websocket",
            "status": "connected",
            "established_at": datetime.min,
            "last_activity": datetime.min,
            "bytes_sent": 0,
            "bytes_received": 0,
        }

        assert connection["established_at"] == datetime.min
        assert connection["last_activity"] == datetime.min

    def test_typed_dict_connection_info_long_strings(self):
        """Test TypedDictConnectionInfo with long string values."""
        long_type = "very_long_connection_type_" + "x" * 100
        long_status = "very_long_status_name_" + "y" * 50

        connection: TypedDictConnectionInfo = {
            "connection_id": uuid4(),
            "connection_type": long_type,
            "status": long_status,
            "established_at": datetime.now(),
            "last_activity": datetime.now(),
            "bytes_sent": 0,
            "bytes_received": 0,
        }

        assert connection["connection_type"] == long_type
        assert connection["status"] == long_status

    def test_typed_dict_connection_info_special_characters(self):
        """Test TypedDictConnectionInfo with special characters."""
        connection: TypedDictConnectionInfo = {
            "connection_id": uuid4(),
            "connection_type": "connection-type_with.special@chars",
            "status": "status$with%special&chars",
            "established_at": datetime.now(),
            "last_activity": datetime.now(),
            "bytes_sent": 0,
            "bytes_received": 0,
        }

        assert connection["connection_type"] == "connection-type_with.special@chars"
        assert connection["status"] == "status$with%special&chars"

    def test_typed_dict_connection_info_unicode(self):
        """Test TypedDictConnectionInfo with unicode characters."""
        connection: TypedDictConnectionInfo = {
            "connection_id": uuid4(),
            "connection_type": "连接类型_测试",
            "status": "连接状态_测试",
            "established_at": datetime.now(),
            "last_activity": datetime.now(),
            "bytes_sent": 0,
            "bytes_received": 0,
        }

        assert connection["connection_type"] == "连接类型_测试"
        assert connection["status"] == "连接状态_测试"

    def test_typed_dict_connection_info_nested_access(self):
        """Test accessing nested properties."""
        connection: TypedDictConnectionInfo = {
            "connection_id": uuid4(),
            "connection_type": "websocket",
            "status": "connected",
            "established_at": datetime.now(),
            "last_activity": datetime.now(),
            "bytes_sent": 1000,
            "bytes_received": 2000,
        }

        # Test accessing all fields
        fields = [
            "connection_id",
            "connection_type",
            "status",
            "established_at",
            "last_activity",
            "bytes_sent",
            "bytes_received",
        ]
        for field in fields:
            assert field in connection
            if field in ["connection_id"]:
                assert isinstance(connection[field], UUID)
            elif field in ["established_at", "last_activity"]:
                assert isinstance(connection[field], datetime)
            elif field in ["bytes_sent", "bytes_received"]:
                assert isinstance(connection[field], int)
            else:
                assert isinstance(connection[field], str)
