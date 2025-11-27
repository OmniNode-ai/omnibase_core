"""Unit tests for EnumCacheEvictionPolicy."""

from omnibase_core.enums.enum_cache_eviction_policy import EnumCacheEvictionPolicy


class TestEnumCacheEvictionPolicy:
    """Test suite for EnumCacheEvictionPolicy enumeration."""

    def test_enum_values(self) -> None:
        """Test that all cache eviction policies are defined."""
        assert EnumCacheEvictionPolicy.LRU.value == "lru"
        assert EnumCacheEvictionPolicy.LFU.value == "lfu"
        assert EnumCacheEvictionPolicy.FIFO.value == "fifo"

    def test_enum_count(self) -> None:
        """Test that enum has exactly 3 members."""
        members = list(EnumCacheEvictionPolicy)
        assert len(members) == 3

    def test_string_enum_behavior(self) -> None:
        """Test that enum inherits from str."""
        assert isinstance(EnumCacheEvictionPolicy.LRU, str)
        assert EnumCacheEvictionPolicy.LFU == "lfu"

    def test_lru_policy(self) -> None:
        """Test LRU (Least Recently Used) policy."""
        assert EnumCacheEvictionPolicy.LRU.value == "lru"

    def test_lfu_policy(self) -> None:
        """Test LFU (Least Frequently Used) policy."""
        assert EnumCacheEvictionPolicy.LFU.value == "lfu"

    def test_fifo_policy(self) -> None:
        """Test FIFO (First In First Out) policy."""
        assert EnumCacheEvictionPolicy.FIFO.value == "fifo"

    def test_enum_comparison(self) -> None:
        """Test enum member equality."""
        policy1 = EnumCacheEvictionPolicy.LRU
        policy2 = EnumCacheEvictionPolicy.LRU
        policy3 = EnumCacheEvictionPolicy.LFU

        assert policy1 == policy2
        assert policy1 != policy3
        assert policy1 is policy2

    def test_enum_in_collection(self) -> None:
        """Test enum usage in collections."""
        policies = {EnumCacheEvictionPolicy.LRU, EnumCacheEvictionPolicy.FIFO}
        assert EnumCacheEvictionPolicy.LRU in policies
        assert EnumCacheEvictionPolicy.LFU not in policies

    def test_enum_iteration(self) -> None:
        """Test iterating over enum members."""
        policies = list(EnumCacheEvictionPolicy)
        assert EnumCacheEvictionPolicy.LRU in policies
        assert EnumCacheEvictionPolicy.LFU in policies
        assert EnumCacheEvictionPolicy.FIFO in policies
        assert len(policies) == 3

    def test_enum_membership_check(self) -> None:
        """Test membership checks."""
        assert "lru" in [e.value for e in EnumCacheEvictionPolicy]
        assert "random" not in [e.value for e in EnumCacheEvictionPolicy]

    def test_enum_string_representation(self) -> None:
        """Test string representation."""
        # str() returns the enum name, not value (even though it inherits from str)
        assert str(EnumCacheEvictionPolicy.LRU) == "EnumCacheEvictionPolicy.LRU"
        assert (
            repr(EnumCacheEvictionPolicy.LFU) == "<EnumCacheEvictionPolicy.LFU: 'lfu'>"
        )
        # The value itself equals the string
        assert EnumCacheEvictionPolicy.LRU == "lru"

    def test_enum_value_uniqueness(self) -> None:
        """Test that all enum values are unique."""
        values = [e.value for e in EnumCacheEvictionPolicy]
        assert len(values) == len(set(values))

    def test_enum_as_dict_key(self) -> None:
        """Test using enum as dictionary key."""
        cache_config = {
            EnumCacheEvictionPolicy.LRU: {"max_size": 100},
            EnumCacheEvictionPolicy.LFU: {"max_size": 50},
        }
        assert cache_config[EnumCacheEvictionPolicy.LRU]["max_size"] == 100

    def test_enum_sorting(self) -> None:
        """Test enum sorting by value."""
        policies = [
            EnumCacheEvictionPolicy.LRU,
            EnumCacheEvictionPolicy.FIFO,
            EnumCacheEvictionPolicy.LFU,
        ]
        sorted_policies = sorted(policies, key=lambda x: x.value)
        assert (
            sorted_policies[0] == EnumCacheEvictionPolicy.FIFO
        )  # "fifo" < "lfu" < "lru"
