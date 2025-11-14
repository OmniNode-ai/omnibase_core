import json
from typing import Any

from omnibase_core.models.service.model_node_service_config import (
    ModelNodeServiceConfig,
)
from omnibase_core.utils.util_safe_yaml_loader import serialize_data_to_yaml


class ModelKubernetesTemplateGenerator:
    """Generator for Kubernetes deployment templates."""

    def __init__(self, service_config: ModelNodeServiceConfig):
        """Initialize generator with service configuration."""
        self.config = service_config

    def generate_deployment(self) -> dict[str, Any]:
        """
        Generate Kubernetes Deployment manifest.

        Returns:
            Kubernetes Deployment configuration dictionary
        """
        app_name = self.config.node_name.replace("_", "-")
        labels = self.config.get_kubernetes_labels()

        deployment: dict[str, Any] = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": f"{app_name}-deployment",
                "namespace": self.config.kubernetes_namespace,
                "labels": labels,
            },
            "spec": {
                "replicas": 1 if not self.config.supports_scaling() else 3,
                "selector": {"matchLabels": {"app": app_name}},
                "template": {
                    "metadata": {"labels": labels},
                    "spec": {
                        "containers": [
                            {
                                "name": app_name,
                                "image": f"{self.config.docker_registry or 'onex'}/{self.config.docker_image or self.config.node_name}:{self.config.docker_tag or 'latest'}",
                                "ports": [
                                    {
                                        "containerPort": self.config.network.port,
                                        "name": "http",
                                    },
                                ],
                                "env": [
                                    {"name": k, "value": v}
                                    for k, v in self.config.get_environment_dict().items()
                                ],
                            },
                        ],
                    },
                },
            },
        }

        # Add resource limits
        if self.config.resources:
            resources = {}
            if self.config.resources.memory_mb or self.config.resources.cpu_cores:
                limits = {}
                if self.config.resources.memory_mb:
                    limits["memory"] = f"{self.config.resources.memory_mb}Mi"
                if self.config.resources.cpu_cores:
                    limits["cpu"] = f"{int(self.config.resources.cpu_cores * 1000)}m"
                resources["limits"] = limits

            deployment["spec"]["template"]["spec"]["containers"][0][
                "resources"
            ] = resources

        # Add health checks
        if self.config.health_check.enabled:
            health_probe = {
                "httpGet": {
                    "path": self.config.health_check.check_path,
                    "port": self.config.network.port,
                },
                "initialDelaySeconds": 30,  # Default startup delay
                "periodSeconds": self.config.health_check.check_interval_seconds,
                "timeoutSeconds": self.config.health_check.timeout_seconds,
                "failureThreshold": self.config.health_check.unhealthy_threshold,
            }
            container = deployment["spec"]["template"]["spec"]["containers"][0]
            container["livenessProbe"] = health_probe
            container["readinessProbe"] = health_probe

        # Add service account
        if self.config.kubernetes_service_account:
            deployment["spec"]["template"]["spec"][
                "serviceAccountName"
            ] = self.config.kubernetes_service_account

        return deployment

    def generate_service(self) -> dict[str, Any]:
        """
        Generate Kubernetes Service manifest.

        Returns:
            Kubernetes Service configuration dictionary
        """
        app_name = self.config.node_name.replace("_", "-")

        ports = [
            {
                "name": "http",
                "port": self.config.network.port,
                "targetPort": self.config.network.port,
                "protocol": "TCP",
            },
        ]

        if self.config.monitoring.prometheus_enabled:
            ports.append(
                {
                    "name": "metrics",
                    "port": self.config.monitoring.prometheus_port,
                    "targetPort": self.config.monitoring.prometheus_port,
                    "protocol": "TCP",
                },
            )

        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"{app_name}-service",
                "namespace": self.config.kubernetes_namespace,
                "labels": self.config.get_kubernetes_labels(),
            },
            "spec": {
                "selector": {"app": app_name},
                "ports": ports,
                "type": "ClusterIP",
            },
        }

    def generate_configmap(self) -> dict[str, Any]:
        """
        Generate Kubernetes ConfigMap for configuration.

        Returns:
            Kubernetes ConfigMap configuration dictionary
        """
        app_name = self.config.node_name.replace("_", "-")

        return {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": f"{app_name}-config",
                "namespace": self.config.kubernetes_namespace,
            },
            "data": {
                "service-config.json": json.dumps(self.config.model_dump(), indent=2)
            },
        }

    def generate_all_manifests(self) -> str:
        """
        Generate all Kubernetes manifests as a single YAML file.

        Returns:
            Complete Kubernetes manifests YAML content
        """
        manifests = [
            self.generate_configmap(),
            self.generate_service(),
            self.generate_deployment(),
        ]

        return "---\n".join(
            serialize_data_to_yaml(manifest, default_flow_style=False)
            for manifest in manifests
        )
