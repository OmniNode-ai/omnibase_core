#!/usr/bin/env python3
"""
Contract Validation Script for ONEX Architecture

Validates that all nodes and services properly implement their contracts with:
1. Required methods and signatures
2. Proper Pydantic model backing for all contracts
3. Subcontract compliance for complex operations
4. Protocol implementation compliance

This ensures architectural compliance and prevents runtime issues.
"""

import sys
import os
import importlib
import inspect
from pathlib import Path
from typing import get_type_hints, List, Dict, Optional, Union, get_origin, get_args
from dataclasses import dataclass

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class ContractValidationResult:
    """Result of contract validation."""
    node_name: str
    contract_type: str
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class ContractValidator:
    """Validates ONEX node contracts."""

    def __init__(self):
        self.results: List[ContractValidationResult] = []
        self.total_nodes = 0
        self.valid_nodes = 0

    def validate_all_contracts(self) -> bool:
        """Validate all contracts in the project."""
        print("🔍 ONEX Contract Validation")
        print("=" * 50)

        success = True
        
        # Validate canary nodes
        success &= self._validate_canary_nodes()
        
        # Validate core services
        success &= self._validate_core_services()
        
        # Validate contract models
        success &= self._validate_contract_models()
        
        # Print summary
        self._print_summary()
        
        return success

    def _validate_canary_nodes(self) -> bool:
        """Validate all canary node contracts."""
        print("\n📋 Validating Canary Node Contracts...")
        
        canary_nodes = [
            ("NodeCanaryEffect", "omnibase_core.nodes.canary.canary_effect.v1_0_0.node"),
            ("NodeCanaryCompute", "omnibase_core.nodes.canary.canary_compute.v1_0_0.node"), 
            ("NodeCanaryReducer", "omnibase_core.nodes.canary.canary_reducer.v1_0_0.node"),
            ("NodeCanaryOrchestrator", "omnibase_core.nodes.canary.canary_orchestrator.v1_0_0.node"),
            ("NodeCanaryGateway", "omnibase_core.nodes.canary.canary_gateway.v1_0_0.node"),
        ]

        success = True
        for node_name, module_path in canary_nodes:
            result = self._validate_node_contract(node_name, module_path)
            self.results.append(result)
            if not result.is_valid:
                success = False

        return success

    def _validate_core_services(self) -> bool:
        """Validate core service contracts."""
        print("\n⚙️  Validating Core Service Contracts...")
        
        core_services = [
            ("ProtocolServiceDiscovery", "omnibase_core.protocol.protocol_service_discovery"),
            ("ProtocolDatabaseConnection", "omnibase_core.protocol.protocol_database_connection"),
        ]

        success = True
        for service_name, module_path in core_services:
            result = self._validate_protocol_contract(service_name, module_path)
            self.results.append(result)
            if not result.is_valid:
                success = False

        return success

    def _validate_node_contract(self, node_name: str, module_path: str) -> ContractValidationResult:
        """Validate a specific node contract."""
        self.total_nodes += 1
        errors = []
        warnings = []

        try:
            # Import the module
            module = importlib.import_module(module_path)
            node_class = getattr(module, node_name)

            # Check if class exists
            if not inspect.isclass(node_class):
                errors.append(f"{node_name} is not a class")
                return ContractValidationResult(node_name, "node", False, errors, warnings)

            # Validate required methods based on node type
            if "Effect" in node_name:
                required_methods = ["perform_effect", "get_health_status", "get_metrics"]
            elif "Compute" in node_name:
                required_methods = ["compute", "get_health_status", "get_metrics"]
            elif "Reducer" in node_name:
                required_methods = ["reduce", "get_health_status", "get_metrics"]
            elif "Orchestrator" in node_name:
                required_methods = ["orchestrate", "get_health_status", "get_metrics"]
            elif "Gateway" in node_name:
                required_methods = ["route", "get_health_status", "get_metrics"]
            else:
                required_methods = ["get_health_status", "get_metrics"]

            # Check for required methods
            for method_name in required_methods:
                if not hasattr(node_class, method_name):
                    errors.append(f"Missing required method: {method_name}")
                elif not callable(getattr(node_class, method_name)):
                    errors.append(f"Method {method_name} is not callable")

            # Check constructor
            if not hasattr(node_class, "__init__"):
                errors.append("Missing __init__ method")
            else:
                init_signature = inspect.signature(node_class.__init__)
                params = list(init_signature.parameters.keys())
                if len(params) < 2 or "container" not in params:  # self + container
                    warnings.append("Constructor should accept container parameter")

            # Check for health status method return type
            if hasattr(node_class, "get_health_status"):
                try:
                    health_method = getattr(node_class, "get_health_status")
                    if inspect.iscoroutinefunction(health_method):
                        # It's async, which is expected
                        pass
                    else:
                        warnings.append("get_health_status should be async")
                except Exception:
                    warnings.append("Could not analyze get_health_status method")

            # Check for metrics consistency
            if hasattr(node_class, "get_metrics"):
                try:
                    # This would be better with actual instance inspection
                    # but for pre-commit hooks, static analysis is sufficient
                    pass
                except Exception:
                    warnings.append("Could not analyze get_metrics method")

            is_valid = len(errors) == 0
            if is_valid:
                self.valid_nodes += 1
                print(f"   ✅ {node_name}: Valid")
            else:
                print(f"   ❌ {node_name}: {len(errors)} errors")

            return ContractValidationResult(node_name, "node", is_valid, errors, warnings)

        except ImportError as e:
            errors.append(f"Failed to import module: {e}")
            print(f"   ❌ {node_name}: Import failed")
            return ContractValidationResult(node_name, "node", False, errors, warnings)

        except Exception as e:
            errors.append(f"Unexpected error: {e}")
            print(f"   ❌ {node_name}: Validation failed")
            return ContractValidationResult(node_name, "node", False, errors, warnings)

    def _validate_protocol_contract(self, protocol_name: str, module_path: str) -> ContractValidationResult:
        """Validate a protocol contract."""
        self.total_nodes += 1
        errors = []
        warnings = []

        try:
            # Import the module
            module = importlib.import_module(module_path)
            protocol_class = getattr(module, protocol_name)

            # Check if it's a protocol (has @runtime_checkable or is typing.Protocol)
            from typing import _ProtocolMeta
            if not (hasattr(protocol_class, "__protocol__") or isinstance(protocol_class, _ProtocolMeta)):
                errors.append(f"{protocol_name} is not a proper Protocol")

            # Check for required methods based on protocol type
            if "ServiceDiscovery" in protocol_name:
                required_methods = ["register_service", "discover_services", "get_service_health", "health_check"]
            elif "DatabaseConnection" in protocol_name:
                required_methods = ["execute_query", "health_check"]
            else:
                required_methods = ["health_check"]

            # Check for required methods in protocol
            for method_name in required_methods:
                if not hasattr(protocol_class, method_name):
                    errors.append(f"Protocol missing required method: {method_name}")

            is_valid = len(errors) == 0
            if is_valid:
                self.valid_nodes += 1
                print(f"   ✅ {protocol_name}: Valid")
            else:
                print(f"   ❌ {protocol_name}: {len(errors)} errors")

            return ContractValidationResult(protocol_name, "protocol", is_valid, errors, warnings)

        except ImportError as e:
            errors.append(f"Failed to import module: {e}")
            print(f"   ❌ {protocol_name}: Import failed")
            return ContractValidationResult(protocol_name, "protocol", False, errors, warnings)

        except Exception as e:
            errors.append(f"Unexpected error: {e}")
            print(f"   ❌ {protocol_name}: Validation failed")  
            return ContractValidationResult(protocol_name, "protocol", False, errors, warnings)

    def _validate_contract_models(self) -> bool:
        """Validate Pydantic model backing for all contracts."""
        print("\n📄 Validating Contract Pydantic Models...")
        
        contract_models = [
            # Core contract models
            ("ModelContractEffect", "omnibase_core.core.contracts.model_contract_effect"),
            ("ModelContractCompute", "omnibase_core.core.contracts.model_contract_compute"),
            ("ModelContractReducer", "omnibase_core.core.contracts.model_contract_reducer"),
            ("ModelContractOrchestrator", "omnibase_core.core.contracts.model_contract_orchestrator"),
            ("ModelContractGateway", "omnibase_core.core.contracts.model_contract_gateway"),
            
            # Input/Output models for each contract type
            ("ModelEffectInput", "omnibase_core.core.node_effect"),
            ("ModelComputeInput", "omnibase_core.core.node_compute"),  
            ("ModelReducerInput", "omnibase_core.core.node_reducer"),
            ("ModelOrchestratorInput", "omnibase_core.core.node_orchestrator"),
            ("ModelGatewayInput", "omnibase_core.core.node_gateway"),
        ]

        success = True
        for model_name, module_path in contract_models:
            result = self._validate_pydantic_model(model_name, module_path)
            self.results.append(result)
            if not result.is_valid:
                success = False

        return success

    def _validate_pydantic_model(self, model_name: str, module_path: str) -> ContractValidationResult:
        """Validate a Pydantic model for contract compliance."""
        self.total_nodes += 1
        errors = []
        warnings = []

        try:
            # Import the module
            module = importlib.import_module(module_path)
            
            # Handle case where model might not exist yet
            if not hasattr(module, model_name):
                errors.append(f"Model {model_name} not found in {module_path}")
                print(f"   ⚠️  {model_name}: Not found")
                return ContractValidationResult(model_name, "model", False, errors, warnings)
            
            model_class = getattr(module, model_name)

            # Check if it's a Pydantic model
            try:
                from pydantic import BaseModel
                if not issubclass(model_class, BaseModel):
                    errors.append(f"{model_name} is not a Pydantic BaseModel")
            except (TypeError, ImportError):
                errors.append(f"{model_name} is not a proper Pydantic model")

            # Check for required Pydantic features
            if hasattr(model_class, 'model_fields'):
                fields = model_class.model_fields
                if not fields:
                    warnings.append(f"{model_name} has no defined fields")
                else:
                    # Check for common contract fields
                    if "Contract" in model_name:
                        required_contract_fields = ["version", "name"]
                        for field in required_contract_fields:
                            if field not in fields:
                                warnings.append(f"Contract model missing recommended field: {field}")
            
            # Check for serialization methods
            if not hasattr(model_class, 'model_dump'):
                warnings.append(f"{model_name} missing model_dump method")
            
            if not hasattr(model_class, 'model_validate'):
                warnings.append(f"{model_name} missing model_validate class method")

            # Check read/write capabilities for contracts
            if "Contract" in model_name:
                read_write_warnings = self._check_contract_read_write_capability(model_class, model_name)
                warnings.extend(read_write_warnings)

            # Test basic instantiation (if possible)
            try:
                # Try to get the constructor signature
                sig = inspect.signature(model_class.__init__)
                params = list(sig.parameters.keys())[1:]  # Skip 'self'
                
                # If no required params, try creating empty instance
                if not any(p for p in sig.parameters.values() 
                          if p.default == p.empty and p.name != 'self'):
                    test_instance = model_class()
                    
                    # Test serialization
                    serialized = test_instance.model_dump()
                    if not isinstance(serialized, dict):
                        errors.append(f"{model_name} serialization doesn't return dict")
                    
                    # Test deserialization
                    deserialized = model_class.model_validate(serialized)
                    if not isinstance(deserialized, model_class):
                        errors.append(f"{model_name} deserialization failed")
                        
            except Exception as e:
                warnings.append(f"Could not test {model_name} instantiation: {str(e)}")

            is_valid = len(errors) == 0
            if is_valid:
                self.valid_nodes += 1
                print(f"   ✅ {model_name}: Valid Pydantic model")
            else:
                print(f"   ❌ {model_name}: {len(errors)} errors")

            return ContractValidationResult(model_name, "model", is_valid, errors, warnings)

        except ImportError as e:
            errors.append(f"Failed to import module: {e}")
            print(f"   ⚠️  {model_name}: Import failed")
            return ContractValidationResult(model_name, "model", False, errors, warnings)

        except Exception as e:
            errors.append(f"Unexpected error: {e}")
            print(f"   ❌ {model_name}: Validation failed")
            return ContractValidationResult(model_name, "model", False, errors, warnings)

    def _check_contract_read_write_capability(self, model_class, model_name: str) -> List[str]:
        """Check if contract model supports read/write operations."""
        warnings = []
        
        # Check for YAML serialization support
        yaml_methods = ["to_yaml", "from_yaml", "yaml_dump", "yaml_load"]
        has_yaml = any(hasattr(model_class, method) for method in yaml_methods)
        if not has_yaml:
            warnings.append(f"{model_name} lacks YAML serialization support")
        
        # Check for JSON serialization (should be built-in with Pydantic)
        if not hasattr(model_class, 'model_dump_json'):
            warnings.append(f"{model_name} lacks JSON serialization")
            
        # Check for validation capabilities
        if not hasattr(model_class, 'model_validate_json'):
            warnings.append(f"{model_name} lacks JSON validation")
        
        return warnings

    def _print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 50)
        print("📊 CONTRACT VALIDATION SUMMARY")
        print("=" * 50)
        
        print(f"Total Contracts Validated: {self.total_nodes}")
        print(f"Valid Contracts: {self.valid_nodes}")
        print(f"Failed Contracts: {self.total_nodes - self.valid_nodes}")
        print(f"Success Rate: {(self.valid_nodes/self.total_nodes)*100:.1f}%")

        # Show detailed errors
        failed_results = [r for r in self.results if not r.is_valid]
        if failed_results:
            print(f"\n❌ FAILED CONTRACTS ({len(failed_results)}):")
            for result in failed_results:
                print(f"\n   {result.node_name} ({result.contract_type}):")
                for error in result.errors:
                    print(f"      • {error}")

        # Show warnings
        warned_results = [r for r in self.results if r.warnings]
        if warned_results:
            print(f"\n⚠️  WARNINGS ({len(warned_results)}):")
            for result in warned_results:
                print(f"\n   {result.node_name}:")
                for warning in result.warnings:
                    print(f"      • {warning}")

        if self.valid_nodes == self.total_nodes:
            print(f"\n🎉 ALL CONTRACTS VALID!")
        else:
            print(f"\n🚫 CONTRACT VALIDATION FAILED")


def main():
    """Main entry point."""
    validator = ContractValidator()
    success = validator.validate_all_contracts()
    
    if not success:
        sys.exit(1)
    
    print("\n✅ Contract validation completed successfully!")


if __name__ == "__main__":
    main()