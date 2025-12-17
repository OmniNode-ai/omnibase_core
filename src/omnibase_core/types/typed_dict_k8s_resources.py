# ONEX-EXEMPT: typed-dict-collection - K8s resource types form a cohesive collection
"""
TypedDict definitions for Kubernetes resource structures.

These TypedDicts provide type safety for Kubernetes manifest generation,
matching the actual K8s API resource specifications.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict

# === Base K8s Types ===


class TypedDictK8sMetadata(TypedDict):
    """Kubernetes resource metadata."""

    name: str
    namespace: NotRequired[str]
    labels: NotRequired[dict[str, str]]
    annotations: NotRequired[dict[str, str]]


class TypedDictK8sEnvVar(TypedDict):
    """Kubernetes environment variable definition."""

    name: str
    value: NotRequired[str]
    valueFrom: NotRequired[dict[str, object]]


class TypedDictK8sResourceLimits(TypedDict, total=False):
    """Kubernetes resource limits (memory, CPU)."""

    memory: str
    cpu: str


class TypedDictK8sResourceRequirements(TypedDict, total=False):
    """Kubernetes container resource requirements."""

    limits: TypedDictK8sResourceLimits
    requests: TypedDictK8sResourceLimits


class TypedDictK8sContainerPort(TypedDict):
    """Kubernetes container port definition."""

    containerPort: int
    name: NotRequired[str]
    protocol: NotRequired[str]


class TypedDictK8sHttpGetProbe(TypedDict):
    """Kubernetes HTTP GET probe configuration."""

    path: str
    port: int
    host: NotRequired[str]
    scheme: NotRequired[str]


class TypedDictK8sProbe(TypedDict, total=False):
    """Kubernetes probe (liveness/readiness) configuration."""

    httpGet: TypedDictK8sHttpGetProbe
    tcpSocket: dict[str, object]
    exec: dict[str, object]
    initialDelaySeconds: int
    periodSeconds: int
    timeoutSeconds: int
    failureThreshold: int
    successThreshold: int


class TypedDictK8sContainer(TypedDict):
    """Kubernetes container specification."""

    name: str
    image: str
    ports: NotRequired[list[TypedDictK8sContainerPort]]
    env: NotRequired[list[TypedDictK8sEnvVar]]
    resources: NotRequired[TypedDictK8sResourceRequirements]
    livenessProbe: NotRequired[TypedDictK8sProbe]
    readinessProbe: NotRequired[TypedDictK8sProbe]
    command: NotRequired[list[str]]
    args: NotRequired[list[str]]


class TypedDictK8sPodSpec(TypedDict):
    """Kubernetes pod specification."""

    containers: list[TypedDictK8sContainer]
    serviceAccountName: NotRequired[str]
    restartPolicy: NotRequired[str]
    volumes: NotRequired[list[dict[str, object]]]


class TypedDictK8sPodTemplateSpec(TypedDict):
    """Kubernetes pod template specification."""

    metadata: TypedDictK8sMetadata
    spec: TypedDictK8sPodSpec


class TypedDictK8sLabelSelector(TypedDict):
    """Kubernetes label selector."""

    matchLabels: dict[str, str]
    matchExpressions: NotRequired[list[dict[str, object]]]


# === Deployment Types ===


class TypedDictK8sDeploymentSpec(TypedDict):
    """Kubernetes Deployment spec."""

    replicas: int
    selector: TypedDictK8sLabelSelector
    template: TypedDictK8sPodTemplateSpec
    strategy: NotRequired[dict[str, object]]


class TypedDictK8sDeployment(TypedDict):
    """
    Kubernetes Deployment resource.

    Structure matching K8s apps/v1 Deployment API.
    """

    apiVersion: str  # "apps/v1"
    kind: str  # "Deployment"
    metadata: TypedDictK8sMetadata
    spec: TypedDictK8sDeploymentSpec


# === Service Types ===


class TypedDictK8sServicePort(TypedDict):
    """Kubernetes Service port definition."""

    name: NotRequired[str]
    port: int
    targetPort: int
    protocol: NotRequired[str]
    nodePort: NotRequired[int]


class TypedDictK8sServiceSpec(TypedDict):
    """Kubernetes Service spec."""

    selector: dict[str, str]
    ports: list[TypedDictK8sServicePort]
    type: NotRequired[str]  # ClusterIP, NodePort, LoadBalancer
    clusterIP: NotRequired[str]
    loadBalancerIP: NotRequired[str]


class TypedDictK8sService(TypedDict):
    """
    Kubernetes Service resource.

    Structure matching K8s v1 Service API.
    """

    apiVersion: str  # "v1"
    kind: str  # "Service"
    metadata: TypedDictK8sMetadata
    spec: TypedDictK8sServiceSpec


# === ConfigMap Types ===


class TypedDictK8sConfigMap(TypedDict):
    """
    Kubernetes ConfigMap resource.

    Structure matching K8s v1 ConfigMap API.
    """

    apiVersion: str  # "v1"
    kind: str  # "ConfigMap"
    metadata: TypedDictK8sMetadata
    data: NotRequired[dict[str, str]]
    binaryData: NotRequired[dict[str, str]]


__all__ = [
    # Base types
    "TypedDictK8sMetadata",
    "TypedDictK8sEnvVar",
    "TypedDictK8sResourceLimits",
    "TypedDictK8sResourceRequirements",
    "TypedDictK8sContainerPort",
    "TypedDictK8sHttpGetProbe",
    "TypedDictK8sProbe",
    "TypedDictK8sContainer",
    "TypedDictK8sPodSpec",
    "TypedDictK8sPodTemplateSpec",
    "TypedDictK8sLabelSelector",
    # Deployment
    "TypedDictK8sDeploymentSpec",
    "TypedDictK8sDeployment",
    # Service
    "TypedDictK8sServicePort",
    "TypedDictK8sServiceSpec",
    "TypedDictK8sService",
    # ConfigMap
    "TypedDictK8sConfigMap",
]
