"""
Tests for ModelBaseFactory abstract base class.

Validates that ModelBaseFactory works correctly with concrete implementations
and enforces the factory protocol.
"""

import pytest
from pydantic import BaseModel, Field, ValidationError

from omnibase_core.models.base.model_factory import ModelBaseFactory


# Test models to be created by factories
class Product(BaseModel):
    """Test product model."""

    name: str
    price: float
    category: str = "general"


class User(BaseModel):
    """Test user model."""

    username: str
    email: str
    active: bool = True


class ConcreteProductFactory(ModelBaseFactory[Product]):
    """Concrete factory for creating products."""

    default_category: str = Field(default="general")
    supported_types: list[str] = Field(default_factory=lambda: ["basic", "premium"])

    def create(self, **kwargs: object) -> Product:
        """Create a product instance."""
        # Merge default category if not provided
        if "category" not in kwargs:
            kwargs["category"] = self.default_category
        return Product(**kwargs)  # type: ignore[arg-type]

    def can_create(self, type_name: str) -> bool:
        """Check if the factory can create the given type."""
        return type_name in self.supported_types


class UserFactory(ModelBaseFactory[User]):
    """Concrete factory for creating users."""

    domain: str = Field(default="example.com")

    def create(self, **kwargs: object) -> User:
        """Create a user instance."""
        # Auto-generate email if not provided
        if "email" not in kwargs and "username" in kwargs:
            kwargs["email"] = f"{kwargs['username']}@{self.domain}"
        return User(**kwargs)  # type: ignore[arg-type]

    def can_create(self, type_name: str) -> bool:
        """Check if the factory can create the given type."""
        return type_name in ["standard", "admin", "guest"]


@pytest.mark.unit
class TestModelBaseFactoryAbstract:
    """Test that ModelBaseFactory enforces abstract methods."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that ModelBaseFactory cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ModelBaseFactory()  # type: ignore[abstract]

    def test_missing_create_method(self):
        """Test that implementations must define create."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):

            class IncompleteFactory(ModelBaseFactory[Product]):
                def can_create(self, type_name: str) -> bool:
                    return True

            IncompleteFactory()  # type: ignore[abstract]

    def test_missing_can_create_method(self):
        """Test that implementations must define can_create."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):

            class IncompleteFactory(ModelBaseFactory[Product]):
                def create(self, **kwargs: object) -> Product:
                    return Product(name="test", price=0.0)

            IncompleteFactory()  # type: ignore[abstract]


@pytest.mark.unit
class TestConcreteFactoryImplementation:
    """Test concrete factory implementations."""

    def test_create_basic_product(self):
        """Test creating a basic product."""
        factory = ConcreteProductFactory()
        product = factory.create(name="Widget", price=9.99)
        assert product.name == "Widget"
        assert product.price == 9.99
        assert product.category == "general"

    def test_create_product_with_category(self):
        """Test creating a product with explicit category."""
        factory = ConcreteProductFactory()
        product = factory.create(name="Premium Widget", price=19.99, category="premium")
        assert product.category == "premium"

    def test_create_with_custom_default_category(self):
        """Test factory with custom default category."""
        factory = ConcreteProductFactory(default_category="electronics")
        product = factory.create(name="Gadget", price=49.99)
        assert product.category == "electronics"

    def test_can_create_supported_type(self):
        """Test can_create returns True for supported types."""
        factory = ConcreteProductFactory()
        assert factory.can_create("basic") is True
        assert factory.can_create("premium") is True

    def test_can_create_unsupported_type(self):
        """Test can_create returns False for unsupported types."""
        factory = ConcreteProductFactory()
        assert factory.can_create("enterprise") is False
        assert factory.can_create("unknown") is False

    def test_factory_configuration(self):
        """Test factory with custom configuration."""
        factory = ConcreteProductFactory(
            default_category="tools",
            supported_types=["basic", "premium", "professional"],
        )
        assert factory.default_category == "tools"
        assert factory.can_create("professional") is True


@pytest.mark.unit
class TestUserFactoryImplementation:
    """Test user factory implementation."""

    def test_create_user_with_email(self):
        """Test creating user with explicit email."""
        factory = UserFactory()
        user = factory.create(username="john", email="john@custom.com")
        assert user.username == "john"
        assert user.email == "john@custom.com"
        assert user.active is True

    def test_create_user_auto_email(self):
        """Test creating user with auto-generated email."""
        factory = UserFactory()
        user = factory.create(username="jane")
        assert user.username == "jane"
        assert user.email == "jane@example.com"

    def test_create_user_custom_domain(self):
        """Test user factory with custom domain."""
        factory = UserFactory(domain="company.com")
        user = factory.create(username="bob")
        assert user.email == "bob@company.com"

    def test_can_create_user_types(self):
        """Test can_create for different user types."""
        factory = UserFactory()
        assert factory.can_create("standard") is True
        assert factory.can_create("admin") is True
        assert factory.can_create("guest") is True
        assert factory.can_create("superuser") is False


@pytest.mark.unit
class TestFactoryModelConfiguration:
    """Test factory model configuration."""

    def test_factory_pydantic_validation(self):
        """Test that Pydantic validation works on factory."""
        factory = ConcreteProductFactory(default_category="test")
        assert factory.default_category == "test"

    def test_factory_model_config_extra_ignore(self):
        """Test that extra fields are ignored."""
        factory = ConcreteProductFactory(
            default_category="test",
            unknown_field="ignored",  # type: ignore[call-arg]
        )
        assert factory.default_category == "test"
        assert not hasattr(factory, "unknown_field")

    def test_factory_model_config_validate_assignment(self):
        """Test that assignment validation is enabled."""
        factory = ConcreteProductFactory()
        factory.default_category = "new_category"
        assert factory.default_category == "new_category"

    def test_factory_serialization(self):
        """Test serializing factory to dict."""
        factory = ConcreteProductFactory(default_category="electronics")
        data = factory.model_dump()
        assert data["default_category"] == "electronics"
        assert "supported_types" in data


@pytest.mark.unit
class TestFactoryCreationPatterns:
    """Test various factory creation patterns."""

    def test_create_with_all_parameters(self):
        """Test create with all possible parameters."""
        factory = ConcreteProductFactory()
        product = factory.create(
            name="Complete Product",
            price=99.99,
            category="complete",
        )
        assert product.name == "Complete Product"
        assert product.price == 99.99
        assert product.category == "complete"

    def test_create_multiple_instances(self):
        """Test creating multiple instances from same factory."""
        factory = ConcreteProductFactory()
        product1 = factory.create(name="Product 1", price=10.0)
        product2 = factory.create(name="Product 2", price=20.0)

        assert product1.name == "Product 1"
        assert product2.name == "Product 2"
        assert product1.price != product2.price

    def test_create_with_validation_error(self):
        """Test that create raises validation error for invalid data."""
        factory = ConcreteProductFactory()
        with pytest.raises(ValidationError):
            factory.create(name="Test", price="invalid_price")  # type: ignore[arg-type]

    def test_factory_state_independence(self):
        """Test that factory instances are independent."""
        factory1 = ConcreteProductFactory(default_category="cat1")
        factory2 = ConcreteProductFactory(default_category="cat2")

        product1 = factory1.create(name="P1", price=10.0)
        product2 = factory2.create(name="P2", price=20.0)

        assert product1.category == "cat1"
        assert product2.category == "cat2"


@pytest.mark.unit
class TestFactoryEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_create_with_no_kwargs(self):
        """Test create with no keyword arguments."""

        class SimpleFactory(ModelBaseFactory[Product]):
            def create(self, **kwargs: object) -> Product:
                return Product(name="default", price=0.0, **kwargs)  # type: ignore[arg-type]

            def can_create(self, type_name: str) -> bool:
                return True

        factory = SimpleFactory()
        product = factory.create()
        assert product.name == "default"
        assert product.price == 0.0

    def test_create_with_many_kwargs(self):
        """Test create with many keyword arguments."""
        factory = ConcreteProductFactory()
        # Should ignore extra kwargs that aren't part of Product model
        product = factory.create(
            name="Test",
            price=10.0,
            category="test",
        )
        assert product.name == "Test"

    def test_can_create_empty_string(self):
        """Test can_create with empty string."""
        factory = ConcreteProductFactory()
        assert factory.can_create("") is False

    def test_can_create_none_type(self):
        """Test can_create with None."""

        class FlexibleFactory(ModelBaseFactory[Product]):
            def create(self, **kwargs: object) -> Product:
                return Product(name="test", price=0.0)

            def can_create(self, type_name: str) -> bool:
                return type_name is not None

        factory = FlexibleFactory()
        assert factory.can_create(None) is False  # type: ignore[arg-type]

    def test_factory_reuse(self):
        """Test reusing factory multiple times."""
        factory = ConcreteProductFactory()
        products = [factory.create(name=f"P{i}", price=float(i)) for i in range(100)]
        assert len(products) == 100
        assert all(isinstance(p, Product) for p in products)


@pytest.mark.unit
class TestFactoryTypeParameter:
    """Test that factory works with different type parameters."""

    def test_product_factory_type(self):
        """Test factory with Product type."""
        factory = ConcreteProductFactory()
        product = factory.create(name="Test", price=1.0)
        assert isinstance(product, Product)

    def test_user_factory_type(self):
        """Test factory with User type."""
        factory = UserFactory()
        user = factory.create(username="test")
        assert isinstance(user, User)

    def test_factory_type_safety(self):
        """Test that factory returns correct type."""
        product_factory = ConcreteProductFactory()
        user_factory = UserFactory()

        product = product_factory.create(name="Widget", price=5.0)
        user = user_factory.create(username="alice")

        assert isinstance(product, Product)
        assert isinstance(user, User)
        assert not isinstance(product, User)
        assert not isinstance(user, Product)


@pytest.mark.unit
class TestFactoryInheritance:
    """Test factory inheritance patterns."""

    def test_extend_factory(self):
        """Test extending a factory with additional functionality."""

        class AdvancedProductFactory(ConcreteProductFactory):
            """Extended factory with additional features."""

            apply_discount: bool = False
            discount_rate: float = 0.1

            def create(self, **kwargs: object) -> Product:
                """Create product with optional discount."""
                product = super().create(**kwargs)
                if self.apply_discount and isinstance(product.price, (int, float)):
                    product.price = product.price * (1 - self.discount_rate)
                return product

        factory = AdvancedProductFactory(apply_discount=True, discount_rate=0.2)
        product = factory.create(name="Sale Item", price=100.0)
        assert product.price == 80.0  # 20% discount applied

    def test_override_can_create(self):
        """Test overriding can_create behavior."""

        class PermissiveFactory(ConcreteProductFactory):
            """Factory that accepts all types."""

            def can_create(self, type_name: str) -> bool:
                return True

        factory = PermissiveFactory()
        assert factory.can_create("any_type") is True
        assert factory.can_create("unknown") is True


@pytest.mark.unit
class TestFactoryWithComplexTypes:
    """Test factory with complex model types."""

    def test_nested_model_creation(self):
        """Test creating models with nested structures."""

        class Address(BaseModel):
            street: str
            city: str

        class Person(BaseModel):
            name: str
            address: Address

        class PersonFactory(ModelBaseFactory[Person]):
            default_city: str = "Unknown"

            def create(self, **kwargs: object) -> Person:
                if "address" not in kwargs and "street" in kwargs:
                    kwargs["address"] = Address(
                        street=kwargs.pop("street"),  # type: ignore[arg-type]
                        city=self.default_city,
                    )
                return Person(**kwargs)  # type: ignore[arg-type]

            def can_create(self, type_name: str) -> bool:
                return type_name == "person"

        factory = PersonFactory(default_city="Seattle")
        person = factory.create(name="John", street="123 Main St")
        assert person.name == "John"
        assert person.address.street == "123 Main St"
        assert person.address.city == "Seattle"
