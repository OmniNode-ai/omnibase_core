"""
Tests for TypedDict structured definitions.

These TypedDicts define structured data formats used throughout the codebase.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from omnibase_core.types.typed_dict_structured_definitions import (
    TypedDictAuditInfo,
    TypedDictBatchProcessingInfo,
    TypedDictCacheInfo,
    TypedDictConfigurationSettings,
    TypedDictConnectionInfo,
    TypedDictDependencyInfo,
    TypedDictErrorDetails,
    TypedDictEventInfo,
    TypedDictExecutionStats,
    TypedDictFeatureFlags,
    TypedDictHealthStatus,
    TypedDictLegacyError,
    TypedDictLegacyHealth,
    TypedDictLegacyStats,
    TypedDictMetrics,
    TypedDictOperationResult,
    TypedDictResourceUsage,
    TypedDictSecurityContext,
    TypedDictSemVer,
    TypedDictServiceInfo,
    TypedDictStatsCollection,
    TypedDictSystemState,
    TypedDictValidationResult,
    TypedDictWorkflowState,
    _parse_datetime,
)


class TestTypedDictStructuredDefinitions:
    """Test TypedDict structured definitions can be instantiated."""

    def test_parse_datetime_with_datetime_object(self) -> None:
        """Test _parse_datetime with datetime object."""
        now = datetime.now()
        result = _parse_datetime(now)
        assert result == now

    def test_parse_datetime_with_iso_string(self) -> None:
        """Test _parse_datetime with ISO format string."""
        iso_string = "2025-01-01T12:00:00"
        result = _parse_datetime(iso_string)
        assert isinstance(result, datetime)
        assert result.year == 2025

    def test_parse_datetime_with_z_suffix(self) -> None:
        """Test _parse_datetime with Z suffix."""
        iso_string = "2025-01-01T12:00:00Z"
        result = _parse_datetime(iso_string)
        assert isinstance(result, datetime)

    def test_parse_datetime_with_invalid_string(self) -> None:
        """Test _parse_datetime with invalid string."""
        result = _parse_datetime("invalid")
        assert isinstance(result, datetime)

    def test_parse_datetime_with_none(self) -> None:
        """Test _parse_datetime with None."""
        result = _parse_datetime(None)
        assert isinstance(result, datetime)

    def test_semver_dict(self) -> None:
        """Test TypedDictSemVer instantiation."""
        version: TypedDictSemVer = {
            "major": 1,
            "minor": 2,
            "patch": 3,
        }
        assert version["major"] == 1
        assert version["minor"] == 2
        assert version["patch"] == 3

    def test_execution_stats_dict(self) -> None:
        """Test TypedDictExecutionStats instantiation."""
        stats: TypedDictExecutionStats = {
            "execution_count": 100,
            "success_count": 95,
            "failure_count": 5,
            "average_duration_ms": 150.5,
            "last_execution": datetime.now(),
            "total_duration_ms": 15050,
        }
        assert stats["execution_count"] == 100
        assert stats["success_count"] == 95

    def test_health_status_dict(self) -> None:
        """Test TypedDictHealthStatus instantiation."""
        health: TypedDictHealthStatus = {
            "is_healthy": True,
            "status": "operational",
            "timestamp": datetime.now(),
            "checks": [],
        }
        assert health["is_healthy"] is True
        assert health["status"] == "operational"

    def test_resource_usage_dict(self) -> None:
        """Test TypedDictResourceUsage instantiation."""
        usage: TypedDictResourceUsage = {
            "cpu_percent": 45.5,
            "memory_mb": 512,
            "disk_mb": 1024,
            "network_kb": 256,
        }
        assert usage["cpu_percent"] == 45.5
        assert usage["memory_mb"] == 512

    def test_configuration_settings_dict(self) -> None:
        """Test TypedDictConfigurationSettings instantiation."""
        config: TypedDictConfigurationSettings = {
            "environment": "production",
            "debug_mode": False,
            "log_level": "INFO",
            "timeout_seconds": 30,
        }
        assert config["environment"] == "production"
        assert config["debug_mode"] is False

    def test_validation_result_dict(self) -> None:
        """Test TypedDictValidationResult instantiation."""
        result: TypedDictValidationResult = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
        }
        assert result["is_valid"] is True
        assert result["errors"] == []

    def test_metrics_dict(self) -> None:
        """Test TypedDictMetrics instantiation."""
        metrics: TypedDictMetrics = {
            "name": "response_time",
            "value": 150.0,
            "unit": "ms",
            "timestamp": datetime.now(),
        }
        assert metrics["name"] == "response_time"
        assert metrics["value"] == 150.0

    def test_error_details_dict(self) -> None:
        """Test TypedDictErrorDetails instantiation."""
        error: TypedDictErrorDetails = {
            "code": "ERR001",
            "message": "Test error",
            "severity": "high",
            "timestamp": datetime.now(),
        }
        assert error["code"] == "ERR001"
        assert error["message"] == "Test error"

    def test_operation_result_dict(self) -> None:
        """Test TypedDictOperationResult instantiation."""
        result: TypedDictOperationResult = {
            "success": True,
            "result": "completed",
            "duration_ms": 100,
        }
        assert result["success"] is True
        assert result["result"] == "completed"

    def test_workflow_state_dict(self) -> None:
        """Test TypedDictWorkflowState instantiation."""
        state: TypedDictWorkflowState = {
            "workflow_id": "wf_123",
            "current_state": "running",
            "started_at": datetime.now(),
        }
        assert state["workflow_id"] == "wf_123"
        assert state["current_state"] == "running"

    def test_event_info_dict(self) -> None:
        """Test TypedDictEventInfo instantiation."""
        event: TypedDictEventInfo = {
            "event_type": "user_action",
            "timestamp": datetime.now(),
            "data": {},
        }
        assert event["event_type"] == "user_action"

    def test_connection_info_dict(self) -> None:
        """Test TypedDictConnectionInfo instantiation."""
        connection: TypedDictConnectionInfo = {
            "host": "localhost",
            "port": 5432,
            "database": "testdb",
        }
        assert connection["host"] == "localhost"
        assert connection["port"] == 5432

    def test_service_info_dict(self) -> None:
        """Test TypedDictServiceInfo instantiation."""
        service: TypedDictServiceInfo = {
            "name": "api_service",
            "version": "1.0.0",
            "status": "running",
        }
        assert service["name"] == "api_service"
        assert service["version"] == "1.0.0"

    def test_dependency_info_dict(self) -> None:
        """Test TypedDictDependencyInfo instantiation."""
        dependency: TypedDictDependencyInfo = {
            "name": "postgres",
            "version": "14.0",
            "required": True,
        }
        assert dependency["name"] == "postgres"
        assert dependency["required"] is True

    def test_cache_info_dict(self) -> None:
        """Test TypedDictCacheInfo instantiation."""
        cache: TypedDictCacheInfo = {
            "hits": 100,
            "misses": 10,
            "size_mb": 256,
        }
        assert cache["hits"] == 100
        assert cache["misses"] == 10

    def test_batch_processing_info_dict(self) -> None:
        """Test TypedDictBatchProcessingInfo instantiation."""
        batch: TypedDictBatchProcessingInfo = {
            "batch_id": "batch_123",
            "items_processed": 1000,
            "items_failed": 5,
        }
        assert batch["batch_id"] == "batch_123"
        assert batch["items_processed"] == 1000

    def test_security_context_dict(self) -> None:
        """Test TypedDictSecurityContext instantiation."""
        context: TypedDictSecurityContext = {
            "user_id": "user_123",
            "roles": ["admin"],
            "permissions": ["read", "write"],
        }
        assert context["user_id"] == "user_123"
        assert "admin" in context["roles"]

    def test_audit_info_dict(self) -> None:
        """Test TypedDictAuditInfo instantiation."""
        audit: TypedDictAuditInfo = {
            "action": "update",
            "user_id": "user_123",
            "timestamp": datetime.now(),
            "resource": "document_456",
        }
        assert audit["action"] == "update"
        assert audit["user_id"] == "user_123"

    def test_feature_flags_dict(self) -> None:
        """Test TypedDictFeatureFlags instantiation."""
        flags: TypedDictFeatureFlags = {
            "feature_a": True,
            "feature_b": False,
        }
        assert flags["feature_a"] is True
        assert flags["feature_b"] is False

    def test_stats_collection_dict(self) -> None:
        """Test TypedDictStatsCollection instantiation."""
        stats: TypedDictStatsCollection = {
            "total_requests": 1000,
            "successful_requests": 950,
            "failed_requests": 50,
        }
        assert stats["total_requests"] == 1000
        assert stats["successful_requests"] == 950

    def test_system_state_dict(self) -> None:
        """Test TypedDictSystemState instantiation."""
        state: TypedDictSystemState = {
            "status": "operational",
            "uptime_seconds": 3600,
            "version": "1.0.0",
        }
        assert state["status"] == "operational"
        assert state["uptime_seconds"] == 3600

    def test_legacy_stats_dict(self) -> None:
        """Test TypedDictLegacyStats instantiation."""
        stats: TypedDictLegacyStats = {
            "count": 100,
        }
        assert stats["count"] == 100

    def test_legacy_health_dict(self) -> None:
        """Test TypedDictLegacyHealth instantiation."""
        health: TypedDictLegacyHealth = {
            "healthy": True,
        }
        assert health["healthy"] is True

    def test_legacy_error_dict(self) -> None:
        """Test TypedDictLegacyError instantiation."""
        error: TypedDictLegacyError = {
            "error_code": "ERR001",
        }
        assert error["error_code"] == "ERR001"
