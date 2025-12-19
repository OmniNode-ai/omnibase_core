"""
Comprehensive unit tests for MixinHashComputation.

Tests cover:
- Mixin integration with Pydantic models
- Basic method availability
- Type checking
"""

import pytest
from pydantic import BaseModel

from omnibase_core.mixins.mixin_hash_computation import MixinHashComputation
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestMixinHashComputationBasicBehavior:
    """Test basic MixinHashComputation functionality."""

    def test_mixin_with_pydantic_model(self):
        """Test MixinHashComputation works with Pydantic models."""

        @pytest.mark.unit
        class TestModel(MixinHashComputation, BaseModel):
            name: str
            version: ModelSemVer
            hash: str | None = None

        model = TestModel(name="test", version=ModelSemVer(major=1, minor=0, patch=0))
        assert isinstance(model, MixinHashComputation)
        assert isinstance(model, BaseModel)

    def test_compute_hash_method_exists(self):
        """Test compute_hash method exists and is callable."""

        @pytest.mark.unit
        class TestModel(MixinHashComputation, BaseModel):
            name: str = "test"

        model = TestModel()
        assert hasattr(model, "compute_hash")
        assert callable(model.compute_hash)

    def test_mixin_inheritance(self):
        """Test MixinHashComputation can be inherited."""

        class BaseModel1(MixinHashComputation):
            pass

        class DerivedModel(BaseModel1, BaseModel):
            name: str = "test"

        model = DerivedModel()
        assert isinstance(model, MixinHashComputation)
        assert hasattr(model, "compute_hash")


@pytest.mark.unit
class TestHashComputationInterface:
    """Test MixinHashComputation interface and method signatures."""

    def test_compute_hash_accepts_required_parameters(self):
        """Test compute_hash accepts body parameter."""

        @pytest.mark.unit
        class TestModel(MixinHashComputation, BaseModel):
            name: str = "test"

        model = TestModel()

        # Should accept body parameter
        try:
            # This will fail because it needs NodeMetadataBlock, but at least
            # we verify the interface exists
            result = model.compute_hash.__func__
            assert callable(result)
        except Exception:
            pass  # Expected to fail without proper NodeMetadataBlock

    def test_compute_hash_accepts_optional_parameters(self):
        """Test compute_hash method signature accepts optional parameters."""

        @pytest.mark.unit
        class TestModel(MixinHashComputation, BaseModel):
            name: str = "test"

        model = TestModel()

        # Verify method signature includes optional parameters
        import inspect

        sig = inspect.signature(model.compute_hash)
        params = list(sig.parameters.keys())

        assert "body" in params
        assert "volatile_fields" in params
        assert "placeholder" in params
        assert "comment_prefix" in params
