import json

from omnibase_core.models.services.model_node_service_config import (
    ModelNodeServiceConfig,
)
from omnibase_core.types.typed_dict_k8s_resources import (
    TypedDictK8sConfigMap,
    TypedDictK8sContainer,
    TypedDictK8sDeployment,
    TypedDictK8sDeploymentSpec,
    TypedDictK8sLabelSelector,
    TypedDictK8sMetadata,
    TypedDictK8sPodSpec,
    TypedDictK8sPodTemplateSpec,
    TypedDictK8sProbe,
    TypedDictK8sResourceLimits,
    TypedDictK8sResourceRequirements,
    TypedDictK8sService,
    TypedDictK8sServicePort,
    TypedDictK8sServiceSpec,
)
from omnibase_core.utils.util_safe_yaml_loader import serialize_data_to_yaml


class ModelKubernetesTemplateGenerator:
    """Generator for Kubernetes deployment templates."""

    def __init__(self, service_config: ModelNodeServiceConfig):
        """Initialize generator with service configuration."""
        self.config = service_config

    def generate_deployment(self) -> TypedDictK8sDeployment:
        """
        Generate Kubernetes Deployment manifest.

        Returns:
            Kubernetes Deployment configuration dictionary
        """
        app_name = self.config.node_name.replace("_", "-")
        labels = self.config.get_kubernetes_labels()

        # Build container spec
        container: TypedDictK8sContainer = {
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
        }

        # Add resource limits
        if self.config.resources:
            if self.config.resources.memory_mb or self.config.resources.cpu_cores:
                resources: TypedDictK8sResourceRequirements = {}
                limits: TypedDictK8sResourceLimits = {}
                if self.config.resources.memory_mb:
                    limits["memory"] = f"{self.config.resources.memory_mb}Mi"
                if self.config.resources.cpu_cores:
                    limits["cpu"] = f"{int(self.config.resources.cpu_cores * 1000)}m"
                if limits:
                    resources["limits"] = limits
                container["resources"] = resources

        # Add health checks
        if self.config.health_check.enabled:
            health_probe: TypedDictK8sProbe = {
                "httpGet": {
                    "path": self.config.health_check.check_path,
                    "port": self.config.network.port,
                },
                "initialDelaySeconds": 30,  # Default startup delay
                "periodSeconds": self.config.health_check.check_interval_seconds,
                "timeoutSeconds": self.config.health_check.timeout_seconds,
                "failureThreshold": self.config.health_check.unhealthy_threshold,
            }
            container["livenessProbe"] = health_probe
            container["readinessProbe"] = health_probe

        # Build pod spec
        pod_spec: TypedDictK8sPodSpec = {
            "containers": [container],
        }

        # Add service account
        if self.config.kubernetes_service_account:
            pod_spec["serviceAccountName"] = self.config.kubernetes_service_account

        # Build pod template
        pod_template: TypedDictK8sPodTemplateSpec = {
            "metadata": {"labels": labels, "name": f"{app_name}-pod"},
            "spec": pod_spec,
        }

        # Build label selector
        selector: TypedDictK8sLabelSelector = {
            "matchLabels": {"app": app_name},
        }

        # Build deployment spec
        deployment_spec: TypedDictK8sDeploymentSpec = {
            "replicas": 1 if not self.config.supports_scaling() else 3,
            "selector": selector,
            "template": pod_template,
        }

        # Build deployment metadata
        metadata: TypedDictK8sMetadata = {
            "name": f"{app_name}-deployment",
            "namespace": self.config.kubernetes_namespace,
            "labels": labels,
        }

        # Build deployment
        deployment: TypedDictK8sDeployment = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": metadata,
            "spec": deployment_spec,
        }

        return deployment

    def generate_service(self) -> TypedDictK8sService:
        """
        Generate Kubernetes Service manifest.

        Returns:
            Kubernetes Service configuration dictionary
        """
        app_name = self.config.node_name.replace("_", "-")

        ports: list[TypedDictK8sServicePort] = [
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

        # Build service metadata
        metadata: TypedDictK8sMetadata = {
            "name": f"{app_name}-service",
            "namespace": self.config.kubernetes_namespace,
            "labels": self.config.get_kubernetes_labels(),
        }

        # Build service spec
        spec: TypedDictK8sServiceSpec = {
            "selector": {"app": app_name},
            "ports": ports,
            "type": "ClusterIP",
        }

        # Build service
        service: TypedDictK8sService = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": metadata,
            "spec": spec,
        }

        return service

    def generate_configmap(self) -> TypedDictK8sConfigMap:
        """
        Generate Kubernetes ConfigMap for configuration.

        Returns:
            Kubernetes ConfigMap configuration dictionary
        """
        app_name = self.config.node_name.replace("_", "-")

        # Build configmap metadata
        metadata: TypedDictK8sMetadata = {
            "name": f"{app_name}-config",
            "namespace": self.config.kubernetes_namespace,
        }

        # Build configmap
        configmap: TypedDictK8sConfigMap = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": metadata,
            "data": {
                "service-config.json": json.dumps(self.config.model_dump(), indent=2)
            },
        }

        return configmap

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
