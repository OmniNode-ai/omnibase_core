"""Tests for ModelDockerComposeManifest."""

import tempfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.models.docker.model_docker_compose_manifest import (
    ModelDockerComposeManifest,
)
from omnibase_core.models.docker.model_docker_config_file import ModelDockerConfigFile
from omnibase_core.models.docker.model_docker_network_config import (
    ModelDockerNetworkConfig,
)
from omnibase_core.models.docker.model_docker_secret_file import ModelDockerSecretFile
from omnibase_core.models.docker.model_docker_service import ModelDockerService
from omnibase_core.models.docker.model_docker_volume_config import (
    ModelDockerVolumeConfig,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class TestModelDockerComposeManifest:
    """Test suite for ModelDockerComposeManifest."""

    def test_create_empty_manifest(self) -> None:
        """Test creating empty manifest with defaults."""
        manifest = ModelDockerComposeManifest()

        assert manifest.version == ModelSemVer(major=3, minor=8, patch=0)
        assert manifest.services == {}
        assert manifest.networks == {}
        assert manifest.volumes == {}
        assert manifest.configs == {}
        assert manifest.secrets == {}
        assert manifest.name is None

    def test_create_manifest_with_services(self) -> None:
        """Test creating manifest with services."""
        service = ModelDockerService(
            name="api",
            image="python:3.12",
            ports=["8000:8000"],
            environment={"ENV": "production"},
        )

        manifest = ModelDockerComposeManifest(
            services={"api": service},
        )

        assert "api" in manifest.services
        assert manifest.services["api"].image == "python:3.12"
        assert manifest.services["api"].ports == ["8000:8000"]

    def test_version_validation_valid(self) -> None:
        """Test version validation with valid versions."""
        valid_versions = [
            ("3.8", ModelSemVer(major=3, minor=8, patch=0)),
            ("3", ModelSemVer(major=3, minor=0, patch=0)),
            ("2.4", ModelSemVer(major=2, minor=4, patch=0)),
            ("3.9", ModelSemVer(major=3, minor=9, patch=0)),
            ("2", ModelSemVer(major=2, minor=0, patch=0)),
        ]

        for version_str, expected_semver in valid_versions:
            manifest = ModelDockerComposeManifest(version=version_str)
            assert manifest.version == expected_semver

    def test_version_validation_invalid(self) -> None:
        """Test version validation with invalid versions."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        invalid_versions = ["3.8.1beta", "v3.8", "latest", "3.x"]

        for version in invalid_versions:
            with pytest.raises((ValidationError, ModelOnexError)):
                ModelDockerComposeManifest(version=version)

    def test_get_service_exists(self) -> None:
        """Test getting existing service."""
        service = ModelDockerService(name="api", image="python:3.12")
        manifest = ModelDockerComposeManifest(services={"api": service})

        retrieved = manifest.get_service("api")
        assert retrieved.name == "api"
        assert retrieved.image == "python:3.12"

    def test_get_service_not_found(self) -> None:
        """Test getting non-existent service."""
        manifest = ModelDockerComposeManifest()

        with pytest.raises(ModelOnexError, match="Service 'api' not found"):
            manifest.get_service("api")

    def test_get_all_services(self) -> None:
        """Test getting all services."""
        service1 = ModelDockerService(name="api", image="python:3.12")
        service2 = ModelDockerService(name="db", image="postgres:15")

        manifest = ModelDockerComposeManifest(
            services={"api": service1, "db": service2},
        )

        services = manifest.get_all_services()
        assert len(services) == 2
        assert any(s.name == "api" for s in services)
        assert any(s.name == "db" for s in services)

    def test_validate_dependencies_valid(self) -> None:
        """Test dependency validation with valid dependencies."""
        service1 = ModelDockerService(
            name="api",
            image="python:3.12",
            depends_on={"db": {"condition": "service_healthy"}},
        )
        service2 = ModelDockerService(name="db", image="postgres:15")

        manifest = ModelDockerComposeManifest(
            services={"api": service1, "db": service2},
        )

        warnings = manifest.validate_dependencies()
        assert len(warnings) == 0

    def test_validate_dependencies_circular(self) -> None:
        """Test dependency validation detects circular dependencies."""
        service1 = ModelDockerService(
            name="api",
            image="python:3.12",
            depends_on={"db": {"condition": "service_started"}},
        )
        service2 = ModelDockerService(
            name="db",
            image="postgres:15",
            depends_on={"api": {"condition": "service_started"}},
        )

        manifest = ModelDockerComposeManifest(
            services={"api": service1, "db": service2},
        )

        warnings = manifest.validate_dependencies()
        assert len(warnings) > 0
        assert any("Circular dependency" in w for w in warnings)

    def test_validate_service_references_undefined_network(self) -> None:
        """Test validation fails for undefined network reference."""
        service = ModelDockerService(
            name="api",
            image="python:3.12",
            networks=["undefined_network"],
        )

        with pytest.raises(
            ModelOnexError, match="undefined network 'undefined_network'"
        ):
            ModelDockerComposeManifest(services={"api": service})

    def test_validate_service_references_valid_network(self) -> None:
        """Test validation succeeds for valid network reference."""
        service = ModelDockerService(
            name="api",
            image="python:3.12",
            networks=["app_network"],
        )
        network = ModelDockerNetworkConfig(driver="bridge")

        manifest = ModelDockerComposeManifest(
            services={"api": service},
            networks={"app_network": network},
        )

        assert manifest is not None

    def test_validate_service_references_undefined_dependency(self) -> None:
        """Test validation fails for undefined service dependency."""
        service = ModelDockerService(
            name="api",
            image="python:3.12",
            depends_on={"undefined_service": {"condition": "service_started"}},
        )

        with pytest.raises(
            ModelOnexError, match="undefined service 'undefined_service'"
        ):
            ModelDockerComposeManifest(services={"api": service})

    def test_detect_port_conflicts_no_conflicts(self) -> None:
        """Test port conflict detection with no conflicts."""
        service1 = ModelDockerService(
            name="api",
            image="python:3.12",
            ports=["8000:8000"],
        )
        service2 = ModelDockerService(
            name="db",
            image="postgres:15",
            ports=["5432:5432"],
        )

        manifest = ModelDockerComposeManifest(
            services={"api": service1, "db": service2},
        )

        warnings = manifest.detect_port_conflicts()
        assert len(warnings) == 0

    def test_detect_port_conflicts_with_conflicts(self) -> None:
        """Test port conflict detection finds conflicts."""
        service1 = ModelDockerService(
            name="api",
            image="python:3.12",
            ports=["8000:8000"],
        )
        service2 = ModelDockerService(
            name="admin",
            image="python:3.12",
            ports=["8000:8080"],
        )

        manifest = ModelDockerComposeManifest(
            services={"api": service1, "admin": service2},
        )

        warnings = manifest.detect_port_conflicts()
        assert len(warnings) == 1
        assert "8000" in warnings[0]
        assert "api" in warnings[0]
        assert "admin" in warnings[0]

    def test_load_from_yaml_basic(self, tmp_path: Path) -> None:
        """Test loading basic docker-compose.yaml."""
        yaml_content = """
version: "3.8"
services:
  api:
    image: python:3.12
    ports:
      - "8000:8000"
    environment:
      ENV: production
networks:
  app_network:
    driver: bridge
volumes:
  data:
    driver: local
"""
        yaml_path = tmp_path / "docker-compose.yaml"
        yaml_path.write_text(yaml_content)

        manifest = ModelDockerComposeManifest.from_yaml(yaml_path)

        assert manifest.version == ModelSemVer(major=3, minor=8, patch=0)
        assert "api" in manifest.services
        assert manifest.services["api"].image == "python:3.12"
        assert "app_network" in manifest.networks
        assert "data" in manifest.volumes

    def test_load_from_yaml_with_configs_and_secrets(self, tmp_path: Path) -> None:
        """Test loading docker-compose.yaml with configs and secrets."""
        yaml_content = """
version: "3.8"
services:
  api:
    image: python:3.12
configs:
  app_config:
    file: ./config.json
secrets:
  db_password:
    file: ./db_password.txt
"""
        yaml_path = tmp_path / "docker-compose.yaml"
        yaml_path.write_text(yaml_content)

        manifest = ModelDockerComposeManifest.from_yaml(yaml_path)

        assert "app_config" in manifest.configs
        assert manifest.configs["app_config"].file == "./config.json"
        assert "db_password" in manifest.secrets
        assert manifest.secrets["db_password"].file == "./db_password.txt"

    def test_load_from_yaml_file_not_found(self, tmp_path: Path) -> None:
        """Test loading from non-existent file."""
        yaml_path = tmp_path / "nonexistent.yaml"

        with pytest.raises(ModelOnexError, match="YAML file not found"):
            ModelDockerComposeManifest.from_yaml(yaml_path)

    def test_load_from_yaml_empty_file(self, tmp_path: Path) -> None:
        """Test loading from empty YAML file."""
        yaml_path = tmp_path / "empty.yaml"
        yaml_path.write_text("")

        with pytest.raises(ModelOnexError, match="Empty or invalid YAML"):
            ModelDockerComposeManifest.from_yaml(yaml_path)

    def test_save_to_yaml_basic(self, tmp_path: Path) -> None:
        """Test saving basic manifest to YAML."""
        service = ModelDockerService(
            name="api",
            image="python:3.12",
            ports=["8000:8000"],
            environment={"ENV": "production"},
        )
        network = ModelDockerNetworkConfig(driver="bridge")

        manifest = ModelDockerComposeManifest(
            version="3.8",
            services={"api": service},
            networks={"app_network": network},
        )

        yaml_path = tmp_path / "output.yaml"
        manifest.save_to_yaml(yaml_path)

        # Verify file was created and is valid YAML
        assert yaml_path.exists()
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        assert data["version"] == "3.8"
        assert "api" in data["services"]
        assert data["services"]["api"]["image"] == "python:3.12"
        assert "app_network" in data["networks"]

    def test_save_to_yaml_with_all_components(self, tmp_path: Path) -> None:
        """Test saving manifest with all components to YAML."""
        service = ModelDockerService(
            name="api",
            image="python:3.12",
        )
        network = ModelDockerNetworkConfig(driver="bridge")
        volume = ModelDockerVolumeConfig(driver="local")
        config = ModelDockerConfigFile(file="./config.json")
        secret = ModelDockerSecretFile(file="./secret.txt")

        manifest = ModelDockerComposeManifest(
            version="3.8",
            name="myproject",
            services={"api": service},
            networks={"app_network": network},
            volumes={"data": volume},
            configs={"app_config": config},
            secrets={"db_password": secret},
        )

        yaml_path = tmp_path / "output.yaml"
        manifest.save_to_yaml(yaml_path)

        # Verify all components are in YAML
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        assert data["name"] == "myproject"
        assert "services" in data
        assert "networks" in data
        assert "volumes" in data
        assert "configs" in data
        assert "secrets" in data

    def test_round_trip_yaml_load_save(self, tmp_path: Path) -> None:
        """Test round-trip: load YAML, save YAML, load again."""
        yaml_content = """
version: "3.8"
name: testproject
services:
  api:
    image: python:3.12
    ports:
      - "8000:8000"
    environment:
      ENV: production
networks:
  app_network:
    driver: bridge
"""
        yaml_path1 = tmp_path / "input.yaml"
        yaml_path1.write_text(yaml_content)

        # Load
        manifest1 = ModelDockerComposeManifest.from_yaml(yaml_path1)

        # Save
        yaml_path2 = tmp_path / "output.yaml"
        manifest1.save_to_yaml(yaml_path2)

        # Load again
        manifest2 = ModelDockerComposeManifest.from_yaml(yaml_path2)

        # Compare
        assert manifest1.version == manifest2.version
        assert manifest1.name == manifest2.name
        assert len(manifest1.services) == len(manifest2.services)
        assert "api" in manifest2.services


class TestModelDockerConfigFile:
    """Test suite for ModelDockerConfigFile."""

    def test_create_config_file_default(self) -> None:
        """Test creating config file with defaults."""
        config = ModelDockerConfigFile()

        assert config.file is None
        assert config.external is False
        assert config.name is None

    def test_create_config_file_with_values(self) -> None:
        """Test creating config file with values."""
        config = ModelDockerConfigFile(
            file="./config.json",
            external=True,
            name="app_config",
        )

        assert config.file == "./config.json"
        assert config.external is True
        assert config.name == "app_config"


class TestModelDockerSecretFile:
    """Test suite for ModelDockerSecretFile."""

    def test_create_secret_file_default(self) -> None:
        """Test creating secret file with defaults."""
        secret = ModelDockerSecretFile()

        assert secret.file is None
        assert secret.external is False
        assert secret.name is None

    def test_create_secret_file_with_values(self) -> None:
        """Test creating secret file with values."""
        secret = ModelDockerSecretFile(
            file="./secret.txt",
            external=True,
            name="db_password",
        )

        assert secret.file == "./secret.txt"
        assert secret.external is True
        assert secret.name == "db_password"
