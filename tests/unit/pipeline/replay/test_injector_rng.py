# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for InjectorRNG - RNG injection for deterministic replay.

This test module follows TDD approach - tests are written FIRST before implementation.

Tests validate:
1. Basic RNG functionality (random, randint, choice)
2. Determinism invariant: same seed produces same sequence
3. Seed isolation: different seeds produce different sequences
4. Seed property returns the used seed for manifest recording
5. Auto-generation of secure seed when none provided
6. Protocol compliance with ProtocolRNGService

Related:
    - OMN-1116: RNG Injector for Replay Infrastructure
    - MIXINS_TO_HANDLERS_REFACTOR.md Section 7.1

.. versionadded:: 0.4.0
"""

import pytest

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def seeded_rng():
    """Create an RNG with a known seed for deterministic tests."""
    from omnibase_core.pipeline.replay import InjectorRNG

    return InjectorRNG(seed=42)


@pytest.fixture
def unseeded_rng():
    """Create an RNG without explicit seed (auto-generated)."""
    from omnibase_core.pipeline.replay import InjectorRNG

    return InjectorRNG()


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.unit
class TestInjectorRNGBasicFunctionality:
    """Test basic RNG functionality."""

    def test_random_returns_float_in_range(self, seeded_rng):
        """Verify random() returns a float in [0.0, 1.0)."""
        value = seeded_rng.random()
        assert isinstance(value, float)
        assert 0.0 <= value < 1.0

    def test_random_returns_different_values_on_consecutive_calls(self, seeded_rng):
        """Verify consecutive calls return different values."""
        values = [seeded_rng.random() for _ in range(100)]
        # With 100 values, we should have many unique values
        unique_values = set(values)
        assert len(unique_values) > 90, "Expected many unique random values"

    def test_randint_returns_int_in_range(self, seeded_rng):
        """Verify randint() returns an integer in [a, b]."""
        for _ in range(100):
            value = seeded_rng.randint(1, 10)
            assert isinstance(value, int)
            assert 1 <= value <= 10

    def test_randint_with_equal_bounds(self, seeded_rng):
        """Verify randint() with equal bounds returns that value."""
        value = seeded_rng.randint(5, 5)
        assert value == 5

    def test_randint_produces_variety(self, seeded_rng):
        """Verify randint produces multiple different values."""
        values = [seeded_rng.randint(1, 100) for _ in range(100)]
        unique_values = set(values)
        assert len(unique_values) > 50, "Expected many unique random integers"

    def test_choice_returns_element_from_sequence(self, seeded_rng):
        """Verify choice() returns an element from the sequence."""
        seq = ["a", "b", "c", "d", "e"]
        for _ in range(100):
            value = seeded_rng.choice(seq)
            assert value in seq

    def test_choice_with_single_element(self, seeded_rng):
        """Verify choice() with single element returns that element."""
        seq = ["only_one"]
        value = seeded_rng.choice(seq)
        assert value == "only_one"

    def test_choice_produces_variety(self, seeded_rng):
        """Verify choice produces multiple different values."""
        seq = ["a", "b", "c", "d", "e"]
        values = [seeded_rng.choice(seq) for _ in range(100)]
        unique_values = set(values)
        assert len(unique_values) >= 4, "Expected most elements to be chosen"


@pytest.mark.unit
class TestInjectorRNGDeterminism:
    """Test determinism invariant - CRITICAL for replay."""

    def test_same_seed_produces_same_sequence(self):
        """
        CRITICAL: Same seed must produce identical sequence.

        This is the key invariant for replay infrastructure.
        """
        from omnibase_core.pipeline.replay import InjectorRNG

        rng1 = InjectorRNG(seed=42)
        rng2 = InjectorRNG(seed=42)

        # Generate sequences
        seq1 = [rng1.random() for _ in range(100)]
        seq2 = [rng2.random() for _ in range(100)]

        assert seq1 == seq2, "Same seed must produce identical sequence"

    def test_same_seed_produces_same_randint_sequence(self):
        """Verify same seed produces identical randint sequence."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng1 = InjectorRNG(seed=42)
        rng2 = InjectorRNG(seed=42)

        seq1 = [rng1.randint(0, 1000) for _ in range(100)]
        seq2 = [rng2.randint(0, 1000) for _ in range(100)]

        assert seq1 == seq2, "Same seed must produce identical randint sequence"

    def test_same_seed_produces_same_choice_sequence(self):
        """Verify same seed produces identical choice sequence."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng1 = InjectorRNG(seed=42)
        rng2 = InjectorRNG(seed=42)

        items = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        seq1 = [rng1.choice(items) for _ in range(100)]
        seq2 = [rng2.choice(items) for _ in range(100)]

        assert seq1 == seq2, "Same seed must produce identical choice sequence"

    def test_different_seeds_produce_different_sequences(self):
        """Verify different seeds produce different sequences."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng1 = InjectorRNG(seed=42)
        rng2 = InjectorRNG(seed=123)

        seq1 = [rng1.random() for _ in range(100)]
        seq2 = [rng2.random() for _ in range(100)]

        assert seq1 != seq2, "Different seeds should produce different sequences"

    def test_replay_produces_identical_sequence(self):
        """
        Full replay test: verify recorded seed can reproduce execution.

        This simulates the replay workflow:
        1. First execution: use RNG, record seed to manifest
        2. Replay: use recorded seed, get identical results
        """
        from omnibase_core.pipeline.replay import InjectorRNG

        # First execution - would be recorded to manifest
        first_rng = InjectorRNG(seed=12345)
        recorded_seed = first_rng.seed

        # Simulate operations during first execution
        first_results = {
            "random_values": [first_rng.random() for _ in range(10)],
            "random_ints": [first_rng.randint(1, 100) for _ in range(10)],
            "random_choices": [first_rng.choice(["x", "y", "z"]) for _ in range(10)],
        }

        # Replay using recorded seed
        replay_rng = InjectorRNG(seed=recorded_seed)
        replay_results = {
            "random_values": [replay_rng.random() for _ in range(10)],
            "random_ints": [replay_rng.randint(1, 100) for _ in range(10)],
            "random_choices": [replay_rng.choice(["x", "y", "z"]) for _ in range(10)],
        }

        # Results must be identical
        assert first_results == replay_results, "Replay must produce identical results"


@pytest.mark.unit
class TestInjectorRNGSeedManagement:
    """Test seed property and auto-generation."""

    def test_seed_property_returns_used_seed(self):
        """Verify seed property returns the seed used for initialization."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng = InjectorRNG(seed=42)
        assert rng.seed == 42

    def test_seed_property_with_different_seeds(self):
        """Verify seed property works with various seed values."""
        from omnibase_core.pipeline.replay import InjectorRNG

        test_seeds = [0, 1, 42, 12345, 2**31 - 1, 2**32 - 1]
        for seed in test_seeds:
            rng = InjectorRNG(seed=seed)
            assert rng.seed == seed, f"Seed property should return {seed}"

    def test_auto_generates_seed_when_none_provided(self):
        """Verify auto-generation of seed in production mode."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng = InjectorRNG()  # No seed provided
        seed = rng.seed

        # Seed should be a valid integer
        assert isinstance(seed, int)
        assert seed >= 0

    def test_auto_generated_seeds_are_different(self):
        """Verify auto-generated seeds are different (cryptographically random)."""
        from omnibase_core.pipeline.replay import InjectorRNG

        # Generate multiple RNGs without explicit seeds
        seeds = [InjectorRNG().seed for _ in range(10)]

        # All seeds should be different (extremely unlikely to collide)
        unique_seeds = set(seeds)
        assert len(unique_seeds) == 10, "Auto-generated seeds should be unique"

    def test_seed_remains_constant_after_operations(self):
        """Verify seed property remains constant after using the RNG."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng = InjectorRNG(seed=42)

        # Perform many operations
        for _ in range(1000):
            rng.random()
            rng.randint(0, 100)
            rng.choice([1, 2, 3])

        # Seed should still be 42
        assert rng.seed == 42, "Seed should remain constant after operations"


@pytest.mark.unit
class TestInjectorRNGProtocolCompliance:
    """Test protocol compliance with ProtocolRNGService."""

    def test_implements_protocol(self):
        """Verify InjectorRNG implements ProtocolRNGService."""
        from omnibase_core.pipeline.replay import InjectorRNG
        from omnibase_core.protocols.replay import ProtocolRNGService

        rng = InjectorRNG(seed=42)
        assert isinstance(rng, ProtocolRNGService)

    def test_non_conforming_class_fails_isinstance(self):
        """Verify isinstance returns False for non-conforming classes."""
        from omnibase_core.protocols.replay import ProtocolRNGService

        class NotAnRNGService:
            pass

        obj = NotAnRNGService()
        assert not isinstance(obj, ProtocolRNGService)

    def test_partial_implementation_fails_isinstance(self):
        """Verify partial implementations don't pass isinstance."""
        from omnibase_core.protocols.replay import ProtocolRNGService

        class PartialRNGService:
            @property
            def seed(self) -> int:
                return 0

            def random(self) -> float:
                return 0.0

            # Missing: randint, choice

        obj = PartialRNGService()
        assert not isinstance(obj, ProtocolRNGService)

    def test_protocol_methods_exist(self):
        """Verify protocol defines expected methods."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng = InjectorRNG(seed=42)

        # Property
        assert hasattr(rng, "seed")

        # Methods
        assert callable(getattr(rng, "random", None))
        assert callable(getattr(rng, "randint", None))
        assert callable(getattr(rng, "choice", None))

    def test_function_accepting_protocol(self):
        """Test function that accepts ProtocolRNGService."""
        from omnibase_core.pipeline.replay import InjectorRNG
        from omnibase_core.protocols.replay import ProtocolRNGService

        def use_rng(rng_service: ProtocolRNGService) -> float:
            """Function that accepts protocol type."""
            return rng_service.random()

        rng: ProtocolRNGService = InjectorRNG(seed=42)
        result = use_rng(rng)

        assert isinstance(result, float)
        assert 0.0 <= result < 1.0


@pytest.mark.unit
class TestInjectorRNGImports:
    """Test that imports work correctly."""

    def test_import_from_pipeline_replay_module(self):
        """Test import from omnibase_core.pipeline.replay."""
        from omnibase_core.pipeline.replay import InjectorRNG

        assert InjectorRNG is not None

    def test_import_from_injector_file(self):
        """Test direct import from injector file."""
        from omnibase_core.pipeline.replay.injector_rng import InjectorRNG

        assert InjectorRNG is not None

    def test_import_protocol_from_protocols_replay(self):
        """Test import protocol from omnibase_core.protocols.replay."""
        from omnibase_core.protocols.replay import ProtocolRNGService

        assert ProtocolRNGService is not None

    def test_import_protocol_from_protocol_file(self):
        """Test direct import from protocol file."""
        from omnibase_core.protocols.replay.protocol_rng_service import (
            ProtocolRNGService,
        )

        assert ProtocolRNGService is not None


@pytest.mark.unit
class TestInjectorRNGEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_randint_with_large_range(self):
        """Verify randint works with large ranges."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng = InjectorRNG(seed=42)
        for _ in range(100):
            value = rng.randint(0, 2**31 - 1)
            assert 0 <= value <= 2**31 - 1

    def test_randint_with_negative_bounds(self):
        """Verify randint works with negative bounds."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng = InjectorRNG(seed=42)
        for _ in range(100):
            value = rng.randint(-100, -1)
            assert -100 <= value <= -1

    def test_choice_with_list_of_integers(self):
        """Verify choice works with integer sequences."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng = InjectorRNG(seed=42)
        seq = [1, 2, 3, 4, 5]
        value = rng.choice(seq)
        assert value in seq
        assert isinstance(value, int)

    def test_choice_with_tuple(self):
        """Verify choice works with tuple sequences."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng = InjectorRNG(seed=42)
        seq = ("a", "b", "c")
        value = rng.choice(seq)
        assert value in seq

    def test_choice_preserves_type(self):
        """Verify choice preserves element type."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng = InjectorRNG(seed=42)

        # Test with different types
        int_seq = [1, 2, 3]
        str_seq = ["a", "b", "c"]
        dict_seq = [{"key": 1}, {"key": 2}]

        int_choice = rng.choice(int_seq)
        str_choice = rng.choice(str_seq)
        dict_choice = rng.choice(dict_seq)

        assert isinstance(int_choice, int)
        assert isinstance(str_choice, str)
        assert isinstance(dict_choice, dict)

    def test_seed_zero_is_valid(self):
        """Verify seed=0 is valid and deterministic."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng1 = InjectorRNG(seed=0)
        rng2 = InjectorRNG(seed=0)

        assert rng1.seed == 0
        assert rng2.seed == 0

        seq1 = [rng1.random() for _ in range(10)]
        seq2 = [rng2.random() for _ in range(10)]

        assert seq1 == seq2


@pytest.mark.unit
class TestInjectorRNGThreadSafety:
    """Test thread safety properties.

    Note: InjectorRNG uses isolated random.Random instances per injector,
    so thread safety is achieved by using separate instances per thread.
    """

    def test_isolated_instances_are_independent(self):
        """Verify separate instances don't interfere with each other."""
        from omnibase_core.pipeline.replay import InjectorRNG

        rng1 = InjectorRNG(seed=42)
        rng2 = InjectorRNG(seed=42)

        # Use rng1 extensively
        for _ in range(1000):
            rng1.random()

        # rng2 should still produce same first values as rng1 would have initially
        rng3 = InjectorRNG(seed=42)

        # rng2 and rng3 should produce same values since neither was used yet
        seq2 = [rng2.random() for _ in range(10)]
        seq3 = [rng3.random() for _ in range(10)]

        assert seq2 == seq3, "Fresh instances with same seed should be identical"
