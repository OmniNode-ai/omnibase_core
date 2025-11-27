"""
Tests for infrastructure_bases module.

Validates that infrastructure base imports are accessible and properly exposed.
"""


def test_can_import_infrastructure_bases():
    """Test that infrastructure_bases module imports successfully."""
    from omnibase_core.infrastructure import infrastructure_bases

    assert infrastructure_bases is not None


def test_service_effect_available():
    """Test that ModelServiceEffect is accessible."""
    from omnibase_core.infrastructure.infrastructure_bases import ModelServiceEffect

    assert ModelServiceEffect is not None


def test_service_compute_available():
    """Test that ModelServiceCompute is accessible."""
    from omnibase_core.infrastructure.infrastructure_bases import ModelServiceCompute

    assert ModelServiceCompute is not None


def test_all_exports_defined():
    """Test that __all__ contains expected exports."""
    from omnibase_core.infrastructure import infrastructure_bases

    assert hasattr(infrastructure_bases, "__all__")
    assert "ModelServiceEffect" in infrastructure_bases.__all__
    assert "ModelServiceCompute" in infrastructure_bases.__all__
