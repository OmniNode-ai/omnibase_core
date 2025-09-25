#!/usr/bin/env python3
"""
Performance tests for validation scripts.

Tests performance characteristics including:
- Large file handling
- Memory usage optimization
- Processing time limits
- Scalability with many files
- Resource consumption monitoring
"""

import os
import shutil

# Import validation modules
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import psutil
import pytest

sys.path.insert(
    0, str(Path(__file__).parent.parent.parent.parent / "scripts" / "validation")
)

try:
    from validate_contracts import validate_yaml_file
    from validate_naming import NamingConventionValidator
    from validate_no_backward_compatibility import BackwardCompatibilityDetector
    from validate_structure import OmniStructureValidator
except ImportError as e:
    pytest.skip(f"Could not import validation modules: {e}", allow_module_level=True)


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for performance testing."""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    yield repo_path
    shutil.rmtree(temp_dir)


@pytest.fixture
def memory_monitor():
    """Monitor memory usage during tests."""
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    class MemoryMonitor:
        def __init__(self):
            self.initial_memory = initial_memory
            self.peak_memory = initial_memory

        def check_memory(self):
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            self.peak_memory = max(self.peak_memory, current_memory)
            return current_memory

        def get_peak_usage(self):
            return self.peak_memory - self.initial_memory

    return MemoryMonitor()


class TestLargeFilePerformance:
    """Test performance with large files."""

    def test_large_python_file_naming_validation(self, temp_repo, memory_monitor):
        """Test naming validation performance with large Python files."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        # Create large Python file
        large_content = '''
"""Large Python file for performance testing."""

from pydantic import BaseModel, ConfigDict
from typing import Dict, List, Optional
from enum import Enum

'''

        # Add many model classes
        for i in range(500):
            large_content += f'''
class ModelTest{i:04d}(BaseModel):
    """Test model {i} for performance validation."""

    # Fields for model {i}
    id_{i}: str
    name_{i}: str
    value_{i}: int = {i}
    active_{i}: bool = True
    metadata_{i}: Optional[Dict[str, str]] = None
    tags_{i}: List[str] = []

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    def get_summary_{i}(self) -> Dict[str, any]:
        """Get summary for model {i}."""
        return {{
            "id": self.id_{i},
            "name": self.name_{i},
            "value": self.value_{i},
            "active": self.active_{i}
        }}

'''

        large_file = models_dir / "model_large_collection.py"
        large_file.write_text(large_content)

        # Test performance
        start_time = time.time()
        memory_monitor.check_memory()

        validator = NamingConventionValidator(temp_repo)
        is_valid = validator.validate_naming_conventions()

        end_time = time.time()
        peak_memory = memory_monitor.get_peak_usage()

        # Performance assertions
        processing_time = end_time - start_time
        assert (
            processing_time < 30.0
        ), f"Large file processing took {processing_time:.2f}s (should be < 30s)"
        assert (
            peak_memory < 500
        ), f"Peak memory usage was {peak_memory:.1f}MB (should be < 500MB)"
        assert is_valid is True, "Large file should pass naming validation"

        print(
            f"Large file performance: {processing_time:.2f}s, {peak_memory:.1f}MB peak memory"
        )

    def test_large_file_backward_compatibility_validation(
        self, temp_repo, memory_monitor
    ):
        """Test backward compatibility validation performance with large files."""
        # Create large file with mixed content
        large_content = '''
"""Large file for backward compatibility testing."""

from pydantic import BaseModel
import re
import ast
from typing import Dict, List, Any

'''

        # Add many classes and functions
        for i in range(200):
            large_content += f'''
class ModelProcessor{i:03d}(BaseModel):
    """Data processor model {i}."""

    processor_id: str
    name: str = "processor_{i}"
    config: Dict[str, Any] = {{}}

    def process_data_{i}(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process data using algorithm {i}."""
        result = {{}}
        for key, value in input_data.items():
            if isinstance(value, str):
                result[f"processed_{{key}}_{i}"] = value.upper()
            elif isinstance(value, (int, float)):
                result[f"processed_{{key}}_{i}"] = value * {i + 1}
            else:
                result[f"processed_{{key}}_{i}"] = str(value)
        return result

    def validate_input_{i}(self, data: Dict[str, Any]) -> bool:
        """Validate input data for processor {i}."""
        required_fields = ["id", "type", "data"]
        return all(field in data for field in required_fields)

'''

        large_file = temp_repo / "large_processor.py"
        large_file.write_text(large_content)

        # Test performance
        start_time = time.time()
        memory_monitor.check_memory()

        detector = BackwardCompatibilityDetector()
        is_valid = detector.validate_python_file(large_file)

        end_time = time.time()
        peak_memory = memory_monitor.get_peak_usage()

        # Performance assertions
        processing_time = end_time - start_time
        assert (
            processing_time < 45.0
        ), f"Large file compatibility check took {processing_time:.2f}s"
        assert peak_memory < 200, f"Peak memory usage was {peak_memory:.1f}MB"
        assert is_valid is True, "Large file should pass compatibility validation"

        print(
            f"Large file compatibility check: {processing_time:.2f}s, {peak_memory:.1f}MB peak"
        )

    def test_very_large_yaml_file_validation(self, temp_repo, memory_monitor):
        """Test YAML validation performance with large files."""
        # Create large YAML contract
        large_yaml = """
contract_version:
  major: 1
  minor: 0
  patch: 0
node_type: "compute"
description: "Large contract for performance testing"

metadata:
  name: "LargeDataProcessor"
  version:
    major: 1
    minor: 0
    patch: 0
  author: "performance-test"

configuration:
  timeout: 300
  retries: 5
  batch_size: 1000

inputs:
"""

        # Add many input definitions
        for i in range(1000):
            large_yaml += f"""
  - name: "input_field_{i:04d}"
    type: "object"
    required: true
    description: "Input field {i} for processing"
    schema:
      type: "object"
      properties:
        id_{i}:
          type: "string"
          description: "Identifier for input {i}"
        value_{i}:
          type: "number"
          description: "Numeric value for input {i}"
        metadata_{i}:
          type: "object"
          description: "Metadata for input {i}"
"""

        large_yaml += """
outputs:
  - name: "processed_data"
    type: "object"
    description: "Processed output data"
    schema:
      type: "object"
      properties:
        results:
          type: "array"
          items:
            type: "object"
"""

        large_yaml_file = temp_repo / "large_contract.yaml"
        large_yaml_file.write_text(large_yaml)

        # Test performance
        start_time = time.time()
        memory_monitor.check_memory()

        errors = validate_yaml_file(large_yaml_file)

        end_time = time.time()
        peak_memory = memory_monitor.get_peak_usage()

        # Performance assertions
        processing_time = end_time - start_time
        assert (
            processing_time < 10.0
        ), f"Large YAML validation took {processing_time:.2f}s"
        assert peak_memory < 100, f"Peak memory usage was {peak_memory:.1f}MB"
        assert len(errors) == 0, f"Large YAML should be valid, got errors: {errors}"

        print(
            f"Large YAML validation: {processing_time:.2f}s, {peak_memory:.1f}MB peak"
        )


class TestManyFilesPerformance:
    """Test performance with many files."""

    def test_many_model_files_validation(self, temp_repo, memory_monitor):
        """Test validation performance with many model files."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        # Create many model files
        num_files = 100
        for i in range(num_files):
            model_content = f'''
from pydantic import BaseModel
from typing import Optional

class ModelBatch{i:03d}(BaseModel):
    """Batch model {i} for performance testing."""

    batch_id: str
    name: str = "batch_{i}"
    count: int = {i}
    active: bool = True
    description: Optional[str] = None

    def get_info(self) -> dict:
        """Get batch information."""
        return {{
            "id": self.batch_id,
            "name": self.name,
            "count": self.count,
            "active": self.active
        }}
'''
            model_file = models_dir / f"model_batch_{i:03d}.py"
            model_file.write_text(model_content)

        # Test naming validation performance
        start_time = time.time()
        memory_monitor.check_memory()

        validator = NamingConventionValidator(temp_repo)
        is_valid = validator.validate_naming_conventions()

        end_time = time.time()
        peak_memory = memory_monitor.get_peak_usage()

        # Performance assertions
        processing_time = end_time - start_time
        files_per_second = num_files / processing_time

        assert (
            processing_time < 60.0
        ), f"Many files validation took {processing_time:.2f}s"
        assert peak_memory < 300, f"Peak memory usage was {peak_memory:.1f}MB"
        assert (
            files_per_second > 2
        ), f"Processing rate was {files_per_second:.1f} files/s (should be > 2)"
        assert is_valid is True, "All model files should pass validation"

        print(
            f"Many files validation: {num_files} files in {processing_time:.2f}s "
            f"({files_per_second:.1f} files/s), {peak_memory:.1f}MB peak"
        )

    def test_many_yaml_files_validation(self, temp_repo, memory_monitor):
        """Test YAML validation performance with many files."""
        contracts_dir = temp_repo / "contracts"
        contracts_dir.mkdir(parents=True)

        # Create many YAML files
        num_files = 50
        for i in range(num_files):
            yaml_content = f"""
contract_version:
  major: 1
  minor: 0
  patch: {i}
node_type: "compute"
description: "Performance test contract {i}"

metadata:
  name: "TestProcessor{i:03d}"
  version:
    major: 1
    minor: 0
    patch: {i}

inputs:
  - name: "input_data_{i}"
    type: "object"
    required: true

outputs:
  - name: "output_data_{i}"
    type: "object"

configuration:
  timeout: {30 + i}
  retries: {3 + (i % 5)}
"""
            yaml_file = contracts_dir / f"contract_{i:03d}.yaml"
            yaml_file.write_text(yaml_content)

        # Test validation performance
        start_time = time.time()
        memory_monitor.check_memory()

        total_errors = 0
        for yaml_file in contracts_dir.glob("*.yaml"):
            errors = validate_yaml_file(yaml_file)
            total_errors += len(errors)

        end_time = time.time()
        peak_memory = memory_monitor.get_peak_usage()

        # Performance assertions
        processing_time = end_time - start_time
        files_per_second = num_files / processing_time

        assert (
            processing_time < 30.0
        ), f"Many YAML files validation took {processing_time:.2f}s"
        assert peak_memory < 150, f"Peak memory usage was {peak_memory:.1f}MB"
        assert (
            files_per_second > 2
        ), f"Processing rate was {files_per_second:.1f} files/s"
        assert (
            total_errors == 0
        ), f"All YAML files should be valid, got {total_errors} errors"

        print(
            f"Many YAML files validation: {num_files} files in {processing_time:.2f}s "
            f"({files_per_second:.1f} files/s), {peak_memory:.1f}MB peak"
        )

    def test_deep_directory_structure_performance(self, temp_repo, memory_monitor):
        """Test performance with deeply nested directory structures."""
        # Create deep directory structure
        current_path = temp_repo / "src" / "omnibase_core"
        current_path.mkdir(parents=True)

        # Create 10 levels deep with files at each level
        for level in range(10):
            level_dir = current_path / f"level_{level}"
            level_dir.mkdir()

            # Add model files at each level
            for i in range(5):
                model_content = f'''
from pydantic import BaseModel

class ModelLevel{level}Item{i}(BaseModel):
    """Model at level {level}, item {i}."""
    level: int = {level}
    item: int = {i}
    path: str = "{level_dir}"
'''
                model_file = level_dir / f"model_level_{level}_item_{i}.py"
                model_file.write_text(model_content)

            current_path = level_dir

        # Test structure validation performance
        start_time = time.time()
        memory_monitor.check_memory()

        validator = OmniStructureValidator(str(temp_repo), "omnibase_core")
        violations = validator.validate_all()

        end_time = time.time()
        peak_memory = memory_monitor.get_peak_usage()

        # Performance assertions
        processing_time = end_time - start_time
        assert (
            processing_time < 45.0
        ), f"Deep structure validation took {processing_time:.2f}s"
        assert peak_memory < 200, f"Peak memory usage was {peak_memory:.1f}MB"

        print(
            f"Deep structure validation: {processing_time:.2f}s, {peak_memory:.1f}MB peak"
        )


class TestMemoryOptimization:
    """Test memory usage optimization."""

    def test_memory_cleanup_between_files(self, temp_repo, memory_monitor):
        """Test that memory is cleaned up between file validations."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        detector = BackwardCompatibilityDetector()
        memory_measurements = []

        # Process files one by one and measure memory
        for i in range(20):
            # Create a moderately large file
            file_content = f'''
from pydantic import BaseModel

class ModelMemoryTest{i:03d}(BaseModel):
    """Memory test model {i}."""
    data: str = "{'x' * 1000}"  # Some data to consume memory
'''
            for j in range(50):  # Add many methods
                file_content += f'''
    def method_{j}(self) -> str:
        """Method {j} for memory testing."""
        return "result_{j}_{'x' * 100}"
'''

            test_file = models_dir / f"model_memory_test_{i:03d}.py"
            test_file.write_text(file_content)

            # Validate and measure memory
            memory_before = memory_monitor.check_memory()
            detector.validate_python_file(test_file)
            memory_after = memory_monitor.check_memory()

            memory_measurements.append(memory_after - memory_before)

        # Memory usage should not grow significantly over time
        early_average = sum(memory_measurements[:5]) / 5
        late_average = sum(memory_measurements[-5:]) / 5
        memory_growth = late_average - early_average

        assert (
            memory_growth < 50
        ), f"Memory grew by {memory_growth:.1f}MB (should be < 50MB)"
        print(f"Memory growth over 20 files: {memory_growth:.1f}MB")

    def test_large_file_memory_limit(self, temp_repo):
        """Test that very large files are rejected to prevent memory issues."""
        # Create a file that's too large
        huge_content = "# Very large file\n" + "x = 'data'\n" * 2000000  # ~40MB of text

        large_file = temp_repo / "huge_file.py"
        try:
            large_file.write_text(huge_content)

            # Check if file exceeds size limit
            if large_file.stat().st_size > 10 * 1024 * 1024:  # 10MB limit
                detector = BackwardCompatibilityDetector()
                result = detector.validate_python_file(large_file)

                # Should reject the file
                assert result is False
                assert any("too large" in error.lower() for error in detector.errors)
                print("Large file correctly rejected")
            else:
                pytest.skip("Could not create file large enough to test size limit")

        except MemoryError:
            pytest.skip("Cannot create large enough file due to memory constraints")


class TestConcurrentPerformance:
    """Test performance under concurrent access."""

    def test_concurrent_validation_simulation(self, temp_repo, memory_monitor):
        """Simulate concurrent validation as might happen in CI."""
        import queue
        import threading

        # Create test files
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        files = []
        for i in range(20):
            model_content = f'''
from pydantic import BaseModel

class ModelConcurrent{i:03d}(BaseModel):
    """Concurrent test model {i}."""
    test_id: str = "test_{i}"
    value: int = {i}
'''
            model_file = models_dir / f"model_concurrent_{i:03d}.py"
            model_file.write_text(model_content)
            files.append(model_file)

        results_queue = queue.Queue()

        def validate_worker(file_subset):
            """Worker function for concurrent validation."""
            start_time = time.time()
            detector = BackwardCompatibilityDetector()

            errors = 0
            for file_path in file_subset:
                if not detector.validate_python_file(file_path):
                    errors += 1

            end_time = time.time()
            results_queue.put((len(file_subset), errors, end_time - start_time))

        # Split files among multiple threads
        num_threads = 4
        files_per_thread = len(files) // num_threads
        threads = []

        start_time = time.time()
        memory_monitor.check_memory()

        for i in range(num_threads):
            start_idx = i * files_per_thread
            end_idx = (
                start_idx + files_per_thread if i < num_threads - 1 else len(files)
            )
            file_subset = files[start_idx:end_idx]

            thread = threading.Thread(target=validate_worker, args=(file_subset,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        end_time = time.time()
        peak_memory = memory_monitor.get_peak_usage()

        # Collect results
        total_files = 0
        total_errors = 0
        total_thread_time = 0

        while not results_queue.empty():
            files_processed, errors, thread_time = results_queue.get()
            total_files += files_processed
            total_errors += errors
            total_thread_time += thread_time

        # Performance assertions
        wall_time = end_time - start_time
        efficiency = total_thread_time / wall_time if wall_time > 0 else 0

        assert wall_time < 30.0, f"Concurrent validation took {wall_time:.2f}s"
        assert peak_memory < 300, f"Peak memory usage was {peak_memory:.1f}MB"
        assert total_errors == 0, f"All files should pass validation"
        assert (
            efficiency > 1.5
        ), f"Concurrent efficiency was {efficiency:.1f}x (should be > 1.5x)"

        print(
            f"Concurrent validation: {total_files} files in {wall_time:.2f}s "
            f"(efficiency: {efficiency:.1f}x), {peak_memory:.1f}MB peak"
        )


class TestScalabilityLimits:
    """Test scalability limits and boundaries."""

    def test_maximum_file_count_handling(self, temp_repo, memory_monitor):
        """Test handling of maximum number of files."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        # Create many small files
        num_files = 200
        for i in range(num_files):
            simple_content = f'''
from pydantic import BaseModel

class ModelScale{i:04d}(BaseModel):
    """Scale test model {i}."""
    id: str = "scale_{i}"
'''
            model_file = models_dir / f"model_scale_{i:04d}.py"
            model_file.write_text(simple_content)

        # Test with file discovery and validation
        start_time = time.time()
        memory_monitor.check_memory()

        detector = BackwardCompatibilityDetector()
        python_files = detector.find_python_files_in_directory(temp_repo)
        success = detector.validate_all_python_files(python_files)

        end_time = time.time()
        peak_memory = memory_monitor.get_peak_usage()

        # Performance assertions
        processing_time = end_time - start_time
        files_per_second = len(python_files) / processing_time

        assert processing_time < 120.0, f"Scale test took {processing_time:.2f}s"
        assert peak_memory < 500, f"Peak memory usage was {peak_memory:.1f}MB"
        assert (
            files_per_second > 1
        ), f"Processing rate was {files_per_second:.1f} files/s"
        assert success is True, "All files should pass validation"

        print(
            f"Scale test: {len(python_files)} files in {processing_time:.2f}s "
            f"({files_per_second:.1f} files/s), {peak_memory:.1f}MB peak"
        )

    def test_file_size_progression_performance(self, temp_repo, memory_monitor):
        """Test performance with progressively larger files."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        detector = BackwardCompatibilityDetector()
        processing_times = []

        # Test with progressively larger files
        for size_factor in [1, 2, 5, 10, 20]:
            num_classes = size_factor * 10
            content = """
from pydantic import BaseModel

"""
            for i in range(num_classes):
                content += f'''
class ModelSize{size_factor}_{i:03d}(BaseModel):
    """Size test model {i} for factor {size_factor}."""
    field_1: str = "data_{i}"
    field_2: int = {i}
'''

            test_file = models_dir / f"model_size_test_{size_factor}.py"
            test_file.write_text(content)

            # Measure processing time
            start_time = time.time()
            detector.validate_python_file(test_file)
            end_time = time.time()

            processing_times.append(end_time - start_time)

        # Performance should scale reasonably
        for i in range(1, len(processing_times)):
            scaling_factor = processing_times[i] / processing_times[0]
            size_factor = [1, 2, 5, 10, 20][i]

            # Time should not scale worse than quadratically with size
            assert (
                scaling_factor < size_factor**1.5
            ), f"Processing time scaling is too poor: {scaling_factor:.1f}x for {size_factor}x size"

        print(f"Size progression times: {[f'{t:.3f}s' for t in processing_times]}")


@pytest.mark.slow
class TestExtremeCases:
    """Test extreme cases that might occur in real usage."""

    def test_extremely_deep_nesting(self, temp_repo, memory_monitor):
        """Test with extremely deep directory nesting."""
        current_path = temp_repo / "src" / "omnibase_core"
        current_path.mkdir(parents=True)

        # Create very deep nesting (20 levels)
        for level in range(20):
            current_path = current_path / f"nested_{level}"
            current_path.mkdir()

            # Add a model file at the deepest level only
            if level == 19:
                model_content = '''
from pydantic import BaseModel

class ModelDeepNested(BaseModel):
    """Model at maximum nesting depth."""
    depth: int = 20
    path: str = "very/deep/path"
'''
                model_file = current_path / "model_deep_nested.py"
                model_file.write_text(model_content)

        # Test that validators can handle deep nesting
        start_time = time.time()
        validator = NamingConventionValidator(temp_repo)
        validator.validate_naming_conventions()
        end_time = time.time()

        assert (
            end_time - start_time < 60.0
        ), "Deep nesting validation should complete in reasonable time"

    def test_files_with_complex_ast(self, temp_repo, memory_monitor):
        """Test files with complex AST structures."""
        models_dir = temp_repo / "src" / "omnibase_core" / "models"
        models_dir.mkdir(parents=True)

        # Create file with complex nested structures
        complex_content = '''
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from enum import Enum

class ModelComplexAST(BaseModel):
    """Model with complex AST for testing."""

    def complex_method(self, data: Dict[str, List[Dict[str, Any]] | str | None]) -> Dict[str, Any]:
        """Method with complex type annotations."""
        result = {}

        for key, value in data.items():
            if isinstance(value, list):
                processed_list = []
                for item in value:
                    if isinstance(item, dict):
                        nested_result = {}
                        for nested_key, nested_value in item.items():
                            if isinstance(nested_value, str):
                                nested_result[f"processed_{nested_key}"] = nested_value.upper()
                            elif isinstance(nested_value, (int, float)):
                                nested_result[f"processed_{nested_key}"] = nested_value * 2
                            else:
                                nested_result[f"processed_{nested_key}"] = str(nested_value)
                        processed_list.append(nested_result)
                result[f"list_{key}"] = processed_list
            elif isinstance(value, str):
                result[f"string_{key}"] = value.upper()
            else:
                result[f"other_{key}"] = str(value)

        return result
'''

        complex_file = models_dir / "model_complex_ast.py"
        complex_file.write_text(complex_content)

        # Test that complex AST is handled efficiently
        start_time = time.time()
        memory_monitor.check_memory()

        detector = BackwardCompatibilityDetector()
        success = detector.validate_python_file(complex_file)

        end_time = time.time()
        peak_memory = memory_monitor.get_peak_usage()

        assert end_time - start_time < 5.0, "Complex AST should be processed quickly"
        assert peak_memory < 100, "Complex AST should not consume excessive memory"
        assert success is True, "Complex AST file should pass validation"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "not slow"])
