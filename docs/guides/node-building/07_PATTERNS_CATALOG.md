# Patterns Catalog - Common ONEX Node Patterns

**Status**: ✅ Complete

## Overview

This catalog provides a comprehensive collection of common patterns for building ONEX nodes. These patterns have been proven in production and can be used as building blocks for your own implementations.

## Table of Contents

1. [COMPUTE Node Patterns](#compute-node-patterns)
2. [EFFECT Node Patterns](#effect-node-patterns)
3. [REDUCER Node Patterns](#reducer-node-patterns)
4. [ORCHESTRATOR Node Patterns](#orchestrator-node-patterns)
5. [Cross-Cutting Patterns](#cross-cutting-patterns)
6. [Error Handling Patterns](#error-handling-patterns)
7. [Performance Patterns](#performance-patterns)
8. [Testing Patterns](#testing-patterns)

## COMPUTE Node Patterns

### 1. Data Transformation Pattern

**Use Case**: Transform data from one format to another.

```python
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from typing import Dict, Any, List

class DataTransformationCompute(NodeCompute):
    """Transform data between different formats."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.transformation_rules = {
            "csv_to_json": self._csv_to_json,
            "json_to_xml": self._json_to_xml,
            "normalize_data": self._normalize_data
        }

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform data based on transformation type."""
        transformation_type = input_data.get("transformation_type")
        data = input_data.get("data")

        if transformation_type not in self.transformation_rules:
            raise ValueError(f"Unknown transformation type: {transformation_type}")

        transformer = self.transformation_rules[transformation_type]
        result = await transformer(data)

        return {
            "transformed_data": result,
            "transformation_type": transformation_type,
            "original_size": len(str(data)),
            "transformed_size": len(str(result))
        }

    async def _csv_to_json(self, csv_data: str) -> List[Dict[str, Any]]:
        """Convert CSV to JSON."""
        lines = csv_data.strip().split('\n')
        headers = lines[0].split(',')

        result = []
        for line in lines[1:]:
            values = line.split(',')
            row = dict(zip(headers, values))
            result.append(row)

        return result

    async def _json_to_xml(self, json_data: Dict[str, Any]) -> str:
        """Convert JSON to XML."""
        # Implementation would use xml.etree.ElementTree
        return f"<root>{json_data}</root>"

    async def _normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data structure."""
        normalized = {}
        for key, value in data.items():
            normalized_key = key.lower().replace(' ', '_')
            if isinstance(value, str):
                normalized[normalized_key] = value.strip()
            else:
                normalized[normalized_key] = value

        return normalized
```

### 2. Calculation Engine Pattern

**Use Case**: Perform complex calculations with multiple operations.

```python
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from typing import Dict, Any, List
import math

class CalculationEngineCompute(NodeCompute):
    """Perform complex calculations with multiple operations."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.operations = {
            "add": self._add,
            "subtract": self._subtract,
            "multiply": self._multiply,
            "divide": self._divide,
            "power": self._power,
            "sqrt": self._sqrt,
            "log": self._log
        }

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute calculation operations."""
        operations = input_data.get("operations", [])
        initial_value = input_data.get("initial_value", 0)

        result = initial_value
        execution_log = []

        for operation in operations:
            op_type = operation.get("type")
            op_value = operation.get("value", 0)

            if op_type not in self.operations:
                raise ValueError(f"Unknown operation: {op_type}")

            previous_result = result
            result = await self.operations[op_type](result, op_value)

            execution_log.append({
                "operation": op_type,
                "value": op_value,
                "previous_result": previous_result,
                "new_result": result
            })

        return {
            "final_result": result,
            "execution_log": execution_log,
            "operations_count": len(operations)
        }

    async def _add(self, a: float, b: float) -> float:
        return a + b

    async def _subtract(self, a: float, b: float) -> float:
        return a - b

    async def _multiply(self, a: float, b: float) -> float:
        return a * b

    async def _divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Division by zero")
        return a / b

    async def _power(self, a: float, b: float) -> float:
        return a ** b

    async def _sqrt(self, a: float, b: float) -> float:
        return math.sqrt(a)

    async def _log(self, a: float, b: float) -> float:
        return math.log(a)
```

### 3. Validation Engine Pattern

**Use Case**: Validate data against multiple rules and schemas.

```python
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from typing import Dict, Any, List
import re

class ValidationEngineCompute(NodeCompute):
    """Validate data against multiple rules and schemas."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.validation_rules = {
            "email": self._validate_email,
            "phone": self._validate_phone,
            "url": self._validate_url,
            "credit_card": self._validate_credit_card,
            "required": self._validate_required,
            "range": self._validate_range,
            "pattern": self._validate_pattern
        }

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against rules."""
        data = input_data.get("data", {})
        rules = input_data.get("rules", [])

        validation_results = []
        is_valid = True

        for rule in rules:
            field = rule.get("field")
            rule_type = rule.get("type")
            rule_params = rule.get("params", {})

            if rule_type not in self.validation_rules:
                validation_results.append({
                    "field": field,
                    "rule": rule_type,
                    "valid": False,
                    "error": f"Unknown validation rule: {rule_type}"
                })
                is_valid = False
                continue

            try:
                validator = self.validation_rules[rule_type]
                field_value = data.get(field)
                valid = await validator(field_value, rule_params)

                validation_results.append({
                    "field": field,
                    "rule": rule_type,
                    "valid": valid,
                    "error": None if valid else f"Validation failed for {field}"
                })

                if not valid:
                    is_valid = False

            except Exception as e:
                validation_results.append({
                    "field": field,
                    "rule": rule_type,
                    "valid": False,
                    "error": str(e)
                })
                is_valid = False

        return {
            "is_valid": is_valid,
            "validation_results": validation_results,
            "validated_fields": len(validation_results)
        }

    async def _validate_email(self, value: str, params: Dict[str, Any]) -> bool:
        """Validate email format."""
        if not value:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, value))

    async def _validate_phone(self, value: str, params: Dict[str, Any]) -> bool:
        """Validate phone number format."""
        if not value:
            return False
        pattern = r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$'
        return bool(re.match(pattern, value))

    async def _validate_url(self, value: str, params: Dict[str, Any]) -> bool:
        """Validate URL format."""
        if not value:
            return False
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, value))

    async def _validate_credit_card(self, value: str, params: Dict[str, Any]) -> bool:
        """Validate credit card number using Luhn algorithm."""
        if not value:
            return False

        # Remove spaces and dashes
        number = re.sub(r'[\s-]', '', value)

        # Check if all characters are digits
        if not number.isdigit():
            return False

        # Luhn algorithm
        def luhn_checksum(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d*2))
            return checksum % 10

        return luhn_checksum(number) == 0

    async def _validate_required(self, value: Any, params: Dict[str, Any]) -> bool:
        """Validate required field."""
        return value is not None and value != ""

    async def _validate_range(self, value: float, params: Dict[str, Any]) -> bool:
        """Validate numeric range."""
        min_val = params.get("min")
        max_val = params.get("max")

        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False

        return True

    async def _validate_pattern(self, value: str, params: Dict[str, Any]) -> bool:
        """Validate against regex pattern."""
        pattern = params.get("pattern")
        if not pattern:
            return False
        return bool(re.match(pattern, value))
```

## EFFECT Node Patterns

### 1. Database Operations Pattern

**Use Case**: Perform database operations with transaction management.

```python
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from typing import Dict, Any, List
import asyncio
import time

class DatabaseOperationsEffect(NodeEffect):
    """Perform database operations with transaction management."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.db_service = None

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database operations."""
        operation_type = input_data.get("operation_type")
        operations = input_data.get("operations", [])
        use_transaction = input_data.get("use_transaction", True)

        if not operations:
            raise ValueError("No operations provided")

        if use_transaction:
            return await self._execute_with_transaction(operation_type, operations)
        else:
            return await self._execute_without_transaction(operation_type, operations)

    async def _execute_with_transaction(self, operation_type: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute operations within a transaction."""
        transaction_id = f"txn_{int(time.time())}"

        try:
            # Begin transaction
            await self._begin_transaction(transaction_id)

            results = []
            for operation in operations:
                result = await self._execute_operation(operation)
                results.append(result)

            # Commit transaction
            await self._commit_transaction(transaction_id)

            return {
                "success": True,
                "transaction_id": transaction_id,
                "operations_count": len(operations),
                "results": results
            }

        except Exception as e:
            # Rollback transaction
            await self._rollback_transaction(transaction_id)
            raise e

    async def _execute_without_transaction(self, operation_type: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute operations without transaction."""
        results = []

        for operation in operations:
            try:
                result = await self._execute_operation(operation)
                results.append(result)
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "operation": operation
                })

        return {
            "success": True,
            "operations_count": len(operations),
            "results": results
        }

    async def _execute_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single database operation."""
        op_type = operation.get("type")
        table = operation.get("table")
        data = operation.get("data", {})
        conditions = operation.get("conditions", {})

        if op_type == "insert":
            return await self._insert_record(table, data)
        elif op_type == "update":
            return await self._update_records(table, data, conditions)
        elif op_type == "delete":
            return await self._delete_records(table, conditions)
        elif op_type == "select":
            return await self._select_records(table, conditions)
        else:
            raise ValueError(f"Unknown operation type: {op_type}")

    async def _insert_record(self, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a record into the database."""
        # Implementation would use actual database service
        return {"success": True, "inserted_id": "12345"}

    async def _update_records(self, table: str, data: Dict[str, Any], conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Update records in the database."""
        # Implementation would use actual database service
        return {"success": True, "updated_count": 1}

    async def _delete_records(self, table: str, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Delete records from the database."""
        # Implementation would use actual database service
        return {"success": True, "deleted_count": 1}

    async def _select_records(self, table: str, conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Select records from the database."""
        # Implementation would use actual database service
        return {"success": True, "records": [{"id": 1, "name": "test"}]}

    async def _begin_transaction(self, transaction_id: str) -> None:
        """Begin a database transaction."""
        # Implementation would use actual database service
        pass

    async def _commit_transaction(self, transaction_id: str) -> None:
        """Commit a database transaction."""
        # Implementation would use actual database service
        pass

    async def _rollback_transaction(self, transaction_id: str) -> None:
        """Rollback a database transaction."""
        # Implementation would use actual database service
        pass
```

### 2. API Integration Pattern

**Use Case**: Integrate with external APIs with retry and circuit breaker.

```python
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from typing import Dict, Any, List
import aiohttp
import asyncio

class APIIntegrationEffect(NodeEffect):
    """Integrate with external APIs with retry and circuit breaker."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.session = None
        self.circuit_breakers = {}

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API operations."""
        api_config = input_data.get("api_config", {})
        operations = input_data.get("operations", [])

        if not operations:
            raise ValueError("No operations provided")

        # Initialize session if needed
        if not self.session:
            self.session = aiohttp.ClientSession()

        results = []
        for operation in operations:
            result = await self._execute_api_operation(api_config, operation)
            results.append(result)

        return {
            "success": True,
            "operations_count": len(operations),
            "results": results
        }

    async def _execute_api_operation(self, api_config: Dict[str, Any], operation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single API operation."""
        url = operation.get("url")
        method = operation.get("method", "GET")
        headers = operation.get("headers", {})
        data = operation.get("data", {})
        params = operation.get("params", {})

        # Get circuit breaker for this API
        circuit_breaker = self._get_circuit_breaker(url)

        if not circuit_breaker.can_execute():
            return {
                "success": False,
                "error": "Circuit breaker is open",
                "url": url
            }

        try:
            # Execute API call
            async with self.session.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params
            ) as response:
                result = await response.json()

                if response.status >= 400:
                    circuit_breaker.record_failure()
                    return {
                        "success": False,
                        "error": f"HTTP {response.status}",
                        "url": url,
                        "response": result
                    }

                circuit_breaker.record_success()
                return {
                    "success": True,
                    "status_code": response.status,
                    "url": url,
                    "response": result
                }

        except Exception as e:
            circuit_breaker.record_failure()
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    def _get_circuit_breaker(self, url: str):
        """Get or create circuit breaker for URL."""
        if url not in self.circuit_breakers:
            self.circuit_breakers[url] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60
            )
        return self.circuit_breakers[url]

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
```

## REDUCER Node Patterns

### 1. State Machine Pattern

**Use Case**: Implement state machines with pure state transitions.

```python
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from typing import Dict, Any, List
from enum import Enum

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class OrderStateMachineReducer(NodeReducer):
    """Implement order state machine with pure state transitions."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.state = {
            "order_id": None,
            "status": OrderStatus.PENDING,
            "history": [],
            "metadata": {}
        }

        # Define valid transitions
        self.transitions = {
            OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
            OrderStatus.DELIVERED: [],  # Terminal state
            OrderStatus.CANCELLED: []   # Terminal state
        }

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process state transition."""
        action = input_data.get("action")
        order_id = input_data.get("order_id")
        metadata = input_data.get("metadata", {})

        if not action:
            raise ValueError("Action is required")

        if order_id and self.state["order_id"] is None:
            self.state["order_id"] = order_id

        # Validate transition
        if not self._is_valid_transition(action):
            raise ValueError(f"Invalid transition from {self.state['status']} to {action}")

        # Execute transition
        new_state = await self._execute_transition(action, metadata)

        return {
            "order_id": self.state["order_id"],
            "previous_status": self.state["status"],
            "new_status": new_state["status"],
            "transition_valid": True,
            "state": new_state
        }

    def _is_valid_transition(self, new_status: str) -> bool:
        """Check if transition is valid."""
        try:
            new_status_enum = OrderStatus(new_status)
            current_status = self.state["status"]
            return new_status_enum in self.transitions.get(current_status, [])
        except ValueError:
            return False

    async def _execute_transition(self, new_status: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Execute state transition."""
        previous_status = self.state["status"]
        new_status_enum = OrderStatus(new_status)

        # Update state
        self.state["status"] = new_status_enum
        self.state["metadata"].update(metadata)

        # Add to history
        self.state["history"].append({
            "timestamp": time.time(),
            "from_status": previous_status.value,
            "to_status": new_status_enum.value,
            "metadata": metadata
        })

        return self.state.copy()

    def get_current_state(self) -> Dict[str, Any]:
        """Get current state."""
        return self.state.copy()

    def get_state_history(self) -> List[Dict[str, Any]]:
        """Get state transition history."""
        return self.state["history"].copy()
```

### 2. Data Aggregation Pattern

**Use Case**: Aggregate data from multiple sources with time windows.

```python
from omnibase_core.nodes.node_reducer import NodeReducer
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from typing import Dict, Any, List
from collections import defaultdict
import time

class DataAggregationReducer(NodeReducer):
    """Aggregate data from multiple sources with time windows."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.aggregated_data = defaultdict(list)
        self.time_windows = {
            "1m": 60,      # 1 minute
            "5m": 300,     # 5 minutes
            "1h": 3600,    # 1 hour
            "1d": 86400    # 1 day
        }

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data aggregation."""
        data_points = input_data.get("data_points", [])
        aggregation_type = input_data.get("aggregation_type", "sum")
        time_window = input_data.get("time_window", "1m")
        group_by = input_data.get("group_by", "source")

        if not data_points:
            raise ValueError("No data points provided")

        # Add data points to aggregation
        for point in data_points:
            await self._add_data_point(point, group_by)

        # Calculate aggregation
        result = await self._calculate_aggregation(aggregation_type, time_window, group_by)

        return {
            "aggregation_type": aggregation_type,
            "time_window": time_window,
            "group_by": group_by,
            "data_points_count": len(data_points),
            "result": result
        }

    async def _add_data_point(self, point: Dict[str, Any], group_by: str) -> None:
        """Add a data point to aggregation."""
        timestamp = point.get("timestamp", time.time())
        value = point.get("value", 0)
        group_key = point.get(group_by, "default")

        self.aggregated_data[group_key].append({
            "timestamp": timestamp,
            "value": value,
            "metadata": point.get("metadata", {})
        })

    async def _calculate_aggregation(self, aggregation_type: str, time_window: str, group_by: str) -> Dict[str, Any]:
        """Calculate aggregation for the specified time window."""
        window_seconds = self.time_windows.get(time_window, 60)
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        result = {}

        for group_key, data_points in self.aggregated_data.items():
            # Filter data points within time window
            recent_points = [
                point for point in data_points
                if point["timestamp"] >= cutoff_time
            ]

            if not recent_points:
                result[group_key] = 0
                continue

            # Calculate aggregation
            values = [point["value"] for point in recent_points]

            if aggregation_type == "sum":
                result[group_key] = sum(values)
            elif aggregation_type == "avg":
                result[group_key] = sum(values) / len(values)
            elif aggregation_type == "min":
                result[group_key] = min(values)
            elif aggregation_type == "max":
                result[group_key] = max(values)
            elif aggregation_type == "count":
                result[group_key] = len(values)
            else:
                raise ValueError(f"Unknown aggregation type: {aggregation_type}")

        return result

    def get_aggregated_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all aggregated data."""
        return dict(self.aggregated_data)

    def clear_old_data(self, time_window: str) -> None:
        """Clear old data outside the time window."""
        window_seconds = self.time_windows.get(time_window, 60)
        cutoff_time = time.time() - window_seconds

        for group_key in self.aggregated_data:
            self.aggregated_data[group_key] = [
                point for point in self.aggregated_data[group_key]
                if point["timestamp"] >= cutoff_time
            ]
```

## ORCHESTRATOR Node Patterns

### 1. Workflow Orchestration Pattern

**Use Case**: Coordinate complex workflows with error handling and recovery.

```python
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from typing import Dict, Any, List
import asyncio

class WorkflowOrchestrator(NodeOrchestrator):
    """Coordinate complex workflows with error handling and recovery."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.active_workflows = {}
        self.workflow_templates = {
            "order_processing": self._order_processing_workflow,
            "user_registration": self._user_registration_workflow,
            "data_pipeline": self._data_pipeline_workflow
        }

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow orchestration."""
        workflow_type = input_data.get("workflow_type")
        workflow_data = input_data.get("workflow_data", {})
        workflow_id = input_data.get("workflow_id", f"wf_{int(time.time())}")

        if workflow_type not in self.workflow_templates:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

        # Initialize workflow
        workflow = {
            "id": workflow_id,
            "type": workflow_type,
            "status": "running",
            "start_time": time.time(),
            "steps": [],
            "data": workflow_data
        }

        self.active_workflows[workflow_id] = workflow

        try:
            # Execute workflow
            workflow_template = self.workflow_templates[workflow_type]
            result = await workflow_template(workflow)

            # Mark workflow as completed
            workflow["status"] = "completed"
            workflow["end_time"] = time.time()
            workflow["result"] = result

            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "result": result,
                "execution_time": workflow["end_time"] - workflow["start_time"]
            }

        except Exception as e:
            # Mark workflow as failed
            workflow["status"] = "failed"
            workflow["end_time"] = time.time()
            workflow["error"] = str(e)

            # Attempt recovery
            recovery_result = await self._attempt_recovery(workflow)

            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e),
                "recovery_attempted": recovery_result is not None,
                "recovery_result": recovery_result
            }

    async def _order_processing_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Execute order processing workflow."""
        steps = [
            {"name": "validate_order", "type": "compute"},
            {"name": "check_inventory", "type": "effect"},
            {"name": "process_payment", "type": "effect"},
            {"name": "update_inventory", "type": "effect"},
            {"name": "send_confirmation", "type": "effect"}
        ]

        return await self._execute_workflow_steps(workflow, steps)

    async def _user_registration_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Execute user registration workflow."""
        steps = [
            {"name": "validate_user_data", "type": "compute"},
            {"name": "check_email_availability", "type": "effect"},
            {"name": "create_user_account", "type": "effect"},
            {"name": "send_welcome_email", "type": "effect"},
            {"name": "log_registration", "type": "effect"}
        ]

        return await self._execute_workflow_steps(workflow, steps)

    async def _data_pipeline_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data pipeline workflow."""
        steps = [
            {"name": "extract_data", "type": "effect"},
            {"name": "transform_data", "type": "compute"},
            {"name": "validate_data", "type": "compute"},
            {"name": "load_data", "type": "effect"},
            {"name": "send_notification", "type": "effect"}
        ]

        return await self._execute_workflow_steps(workflow, steps)

    async def _execute_workflow_steps(self, workflow: Dict[str, Any], steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute workflow steps."""
        results = []

        for step in steps:
            step_result = await self._execute_step(workflow, step)
            results.append(step_result)

            # Check if step failed
            if not step_result.get("success", False):
                raise Exception(f"Step {step['name']} failed: {step_result.get('error')}")

        return {
            "steps_executed": len(steps),
            "results": results
        }

    async def _execute_step(self, workflow: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single workflow step."""
        step_name = step["name"]
        step_type = step["type"]

        try:
            # Simulate step execution
            await asyncio.sleep(0.1)  # Simulate processing time

            # Add step to workflow
            workflow["steps"].append({
                "name": step_name,
                "type": step_type,
                "status": "completed",
                "timestamp": time.time()
            })

            return {
                "step": step_name,
                "success": True,
                "result": f"Step {step_name} completed successfully"
            }

        except Exception as e:
            # Add failed step to workflow
            workflow["steps"].append({
                "name": step_name,
                "type": step_type,
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            })

            return {
                "step": step_name,
                "success": False,
                "error": str(e)
            }

    async def _attempt_recovery(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to recover from workflow failure."""
        # Simple recovery strategy: retry failed steps
        failed_steps = [step for step in workflow["steps"] if step["status"] == "failed"]

        if not failed_steps:
            return None

        recovery_results = []
        for step in failed_steps:
            try:
                # Retry step
                await asyncio.sleep(0.1)  # Simulate retry
                recovery_results.append({
                    "step": step["name"],
                    "recovery_success": True
                })
            except Exception as e:
                recovery_results.append({
                    "step": step["name"],
                    "recovery_success": False,
                    "error": str(e)
                })

        return {
            "recovery_attempted": True,
            "failed_steps_count": len(failed_steps),
            "recovery_results": recovery_results
        }

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow status."""
        return self.active_workflows.get(workflow_id, {})

    def get_active_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get all active workflows."""
        return self.active_workflows.copy()
```

## Cross-Cutting Patterns

### 1. Caching Pattern

**Use Case**: Add caching to any node type for performance optimization.

```python
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from typing import Dict, Any, Optional
import hashlib
import json

class CachingMixin:
    """Mixin for adding caching functionality to nodes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes default TTL
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }

    def _generate_cache_key(self, input_data: Dict[str, Any]) -> str:
        """Generate cache key from input data."""
        # Sort keys for consistent hashing
        sorted_data = json.dumps(input_data, sort_keys=True)
        return hashlib.md5(sorted_data.encode()).hexdigest()

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid."""
        if "timestamp" not in cache_entry:
            return False

        current_time = time.time()
        return (current_time - cache_entry["timestamp"]) < self.cache_ttl

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get value from cache."""
        if cache_key not in self.cache:
            self.cache_stats["misses"] += 1
            return None

        cache_entry = self.cache[cache_key]
        if not self._is_cache_valid(cache_entry):
            del self.cache[cache_key]
            self.cache_stats["evictions"] += 1
            self.cache_stats["misses"] += 1
            return None

        self.cache_stats["hits"] += 1
        return cache_entry["value"]

    def _put_to_cache(self, cache_key: str, value: Any) -> None:
        """Put value to cache."""
        self.cache[cache_key] = {
            "value": value,
            "timestamp": time.time()
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self.cache_stats,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_size": len(self.cache)
        }

class CachedComputeNode(NodeCompute, CachingMixin):
    """COMPUTE node with caching functionality."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        CachingMixin.__init__(self)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process with caching."""
        cache_key = self._generate_cache_key(input_data)

        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return {
                **cached_result,
                "from_cache": True
            }

        # Process normally
        result = await self._actual_process(input_data)

        # Cache result
        self._put_to_cache(cache_key, result)

        return {
            **result,
            "from_cache": False
        }

    async def _actual_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Actual processing logic."""
        # Your business logic here
        return {"result": "processed"}
```

### 2. Metrics Collection Pattern

**Use Case**: Collect performance metrics from any node type.

```python
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from typing import Dict, Any
import time
from collections import defaultdict

class MetricsMixin:
    """Mixin for adding metrics collection to nodes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = defaultdict(list)
        self.operation_count = 0
        self.error_count = 0

    def _record_metric(self, metric_name: str, value: float, metadata: Dict[str, Any] = None) -> None:
        """Record a metric value."""
        self.metrics[metric_name].append({
            "value": value,
            "timestamp": time.time(),
            "metadata": metadata or {}
        })

    def _record_operation(self, operation_name: str, duration: float, success: bool) -> None:
        """Record operation metrics."""
        self.operation_count += 1
        if not success:
            self.error_count += 1

        self._record_metric("operation_duration", duration, {
            "operation": operation_name,
            "success": success
        })

        self._record_metric("operation_count", 1, {
            "operation": operation_name,
            "success": success
        })

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        total_operations = self.operation_count
        success_rate = ((total_operations - self.error_count) / total_operations * 100) if total_operations > 0 else 0

        # Calculate average durations
        duration_metrics = self.metrics.get("operation_duration", [])
        avg_duration = sum(m["value"] for m in duration_metrics) / len(duration_metrics) if duration_metrics else 0

        return {
            "total_operations": total_operations,
            "error_count": self.error_count,
            "success_rate_percent": round(success_rate, 2),
            "average_duration_ms": round(avg_duration * 1000, 2),
            "metrics_count": len(self.metrics)
        }

    def get_detailed_metrics(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get detailed metrics."""
        return dict(self.metrics)

class MetricsComputeNode(NodeCompute, MetricsMixin):
    """COMPUTE node with metrics collection."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        MetricsMixin.__init__(self)

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process with metrics collection."""
        start_time = time.time()
        operation_name = "process"

        try:
            # Your business logic here
            result = await self._actual_process(input_data)

            # Record successful operation
            duration = time.time() - start_time
            self._record_operation(operation_name, duration, True)

            return result

        except Exception as e:
            # Record failed operation
            duration = time.time() - start_time
            self._record_operation(operation_name, duration, False)

            # Record error metric
            self._record_metric("error_count", 1, {
                "error_type": type(e).__name__,
                "operation": operation_name
            })

            raise

    async def _actual_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Actual processing logic."""
        # Your business logic here
        return {"result": "processed"}
```

## Error Handling Patterns

### 1. Retry with Exponential Backoff

```python
from omnibase_core.utils.retry import retry_with_backoff, RetryConfig
from omnibase_core.errors.error_codes import EnumCoreErrorCode

class RetryableNode(NodeCompute):
    """Node with retry functionality."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.retry_config = RetryConfig(
            max_attempts=3,
            initial_delay=1.0,
            max_delay=60.0,
            backoff_multiplier=2.0,
            jitter=True,
            retryable_exceptions=[ConnectionError, TimeoutError]
        )

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process with retry logic."""
        return await retry_with_backoff(
            func=self._actual_process,
            config=self.retry_config,
            correlation_id=input_data.get("correlation_id"),
            input_data
        )

    async def _actual_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Actual processing logic that may fail."""
        # Your business logic here
        return {"result": "processed"}
```

### 2. Circuit Breaker Pattern

```python
from omnibase_core.utils.circuit_breaker import CircuitBreaker

class CircuitBreakerNode(NodeEffect):
    """Node with circuit breaker protection."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=Exception
        )

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process with circuit breaker protection."""
        try:
            result = await self.circuit_breaker.call(self._risky_operation, input_data)
            return result
        except CircuitBreakerOpenException:
            # Fallback behavior
            return await self._fallback_operation(input_data)

    async def _risky_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Operation that may fail."""
        # Your business logic here
        return {"result": "processed"}

    async def _fallback_operation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback operation when circuit breaker is open."""
        return {"result": "fallback", "circuit_breaker_open": True}
```

## Performance Patterns

### 1. Batch Processing Pattern

```python
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from typing import Dict, Any, List
import asyncio

class BatchProcessingNode(NodeCompute):
    """Node that processes data in batches for better performance."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.batch_size = 100
        self.max_concurrent_batches = 5

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data in batches."""
        data_items = input_data.get("data_items", [])
        batch_size = input_data.get("batch_size", self.batch_size)

        if not data_items:
            raise ValueError("No data items provided")

        # Split data into batches
        batches = [data_items[i:i + batch_size] for i in range(0, len(data_items), batch_size)]

        # Process batches concurrently
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)

        async def process_batch(batch):
            async with semaphore:
                return await self._process_batch(batch)

        batch_tasks = [process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks)

        # Combine results
        all_results = []
        for batch_result in batch_results:
            all_results.extend(batch_result)

        return {
            "total_items": len(data_items),
            "batches_processed": len(batches),
            "results": all_results
        }

    async def _process_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a single batch."""
        results = []
        for item in batch:
            result = await self._process_item(item)
            results.append(result)
        return results

    async def _process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single item."""
        # Your business logic here
        return {"processed": True, "item": item}
```

### 2. Streaming Processing Pattern

```python
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from typing import Dict, Any, AsyncGenerator
import asyncio

class StreamingProcessingNode(NodeCompute):
    """Node that processes data in a streaming fashion."""

    def __init__(self, container: ModelONEXContainer):
        super().__init__(container)
        self.buffer_size = 1000
        self.flush_interval = 5.0  # seconds

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data in streaming fashion."""
        data_stream = input_data.get("data_stream")
        if not data_stream:
            raise ValueError("No data stream provided")

        # Process stream
        processed_count = 0
        async for result in self._process_stream(data_stream):
            processed_count += 1
            # Yield result or store in buffer
            yield result

        return {
            "processed_count": processed_count,
            "stream_completed": True
        }

    async def _process_stream(self, data_stream: AsyncGenerator[Dict[str, Any], None]) -> AsyncGenerator[Dict[str, Any], None]:
        """Process data stream."""
        buffer = []
        last_flush = time.time()

        async for item in data_stream:
            # Process item
            processed_item = await self._process_item(item)
            buffer.append(processed_item)

            # Check if buffer should be flushed
            current_time = time.time()
            if (len(buffer) >= self.buffer_size or
                current_time - last_flush >= self.flush_interval):

                # Flush buffer
                for buffered_item in buffer:
                    yield buffered_item

                buffer.clear()
                last_flush = current_time

        # Flush remaining items
        for buffered_item in buffer:
            yield buffered_item

    async def _process_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single item."""
        # Your business logic here
        return {"processed": True, "item": item}
```

## Testing Patterns

### 1. Mock Service Pattern

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

class MockServiceProvider:
    """Provider of mock services for testing."""

    @staticmethod
    def create_mock_database_service():
        """Create mock database service."""
        mock_service = AsyncMock()
        mock_service.query.return_value = [{"id": 1, "name": "test"}]
        mock_service.insert.return_value = {"inserted_id": "12345"}
        mock_service.update.return_value = {"updated_count": 1}
        mock_service.delete.return_value = {"deleted_count": 1}
        return mock_service

    @staticmethod
    def create_mock_api_service():
        """Create mock API service."""
        mock_service = AsyncMock()
        mock_service.get.return_value = {"status": 200, "data": {"result": "success"}}
        mock_service.post.return_value = {"status": 201, "data": {"created": True}}
        mock_service.put.return_value = {"status": 200, "data": {"updated": True}}
        mock_service.delete.return_value = {"status": 204, "data": {"deleted": True}}
        return mock_service

    @staticmethod
    def create_mock_cache_service():
        """Create mock cache service."""
        mock_service = AsyncMock()
        mock_service.get.return_value = None
        mock_service.set.return_value = True
        mock_service.delete.return_value = True
        return mock_service

@pytest.fixture
def mock_container():
    """Create container with mock services."""
    container = ModelONEXContainer()

    # Register mock services
    container.register_service("DatabaseService", MockServiceProvider.create_mock_database_service())
    container.register_service("APIService", MockServiceProvider.create_mock_api_service())
    container.register_service("CacheService", MockServiceProvider.create_mock_cache_service())

    return container

@pytest.mark.asyncio
async def test_with_mock_services(mock_container):
    """Test node with mock services."""
    # Your test logic here
    pass
```

### 2. Test Data Factory Pattern

```python
import pytest
from typing import Dict, Any, List
import random
import string

class TestDataFactory:
    """Factory for creating test data."""

    @staticmethod
    def create_user_data(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create user test data."""
        data = {
            "id": random.randint(1, 10000),
            "name": f"User{random.randint(1, 1000)}",
            "email": f"user{random.randint(1, 1000)}@example.com",
            "age": random.randint(18, 80),
            "active": True
        }

        if overrides:
            data.update(overrides)

        return data

    @staticmethod
    def create_order_data(overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create order test data."""
        data = {
            "id": random.randint(1, 10000),
            "user_id": random.randint(1, 1000),
            "items": [
                {"product_id": random.randint(1, 100), "quantity": random.randint(1, 5)}
                for _ in range(random.randint(1, 5))
            ],
            "total": round(random.uniform(10.0, 1000.0), 2),
            "status": random.choice(["pending", "confirmed", "shipped", "delivered"])
        }

        if overrides:
            data.update(overrides)

        return data

    @staticmethod
    def create_batch_data(count: int, data_type: str = "user") -> List[Dict[str, Any]]:
        """Create batch of test data."""
        if data_type == "user":
            return [TestDataFactory.create_user_data() for _ in range(count)]
        elif data_type == "order":
            return [TestDataFactory.create_order_data() for _ in range(count)]
        else:
            raise ValueError(f"Unknown data type: {data_type}")

@pytest.fixture
def test_data():
    """Provide test data factory."""
    return TestDataFactory

@pytest.mark.asyncio
async def test_with_factory_data(test_data):
    """Test with factory-generated data."""
    user_data = test_data.create_user_data({"name": "TestUser"})
    order_data = test_data.create_order_data({"user_id": user_data["id"]})

    # Your test logic here
    assert user_data["name"] == "TestUser"
    assert order_data["user_id"] == user_data["id"]
```

## Related Documentation

- [Node Building Guide](README.md) - Complete implementation tutorials
- [Testing Intent Publisher](09_TESTING_INTENT_PUBLISHER.md) - Comprehensive testing strategies
- [Error Handling](../../conventions/ERROR_HANDLING_BEST_PRACTICES.md) - Error handling patterns
- [API Reference](../../reference/api/) - Complete API documentation
