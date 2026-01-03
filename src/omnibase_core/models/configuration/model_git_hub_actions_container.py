"""GitHub Actions container configuration model.

This module defines ModelGitHubActionsContainer, a Pydantic model representing
the container configuration for a GitHub Actions job. Containers allow jobs
to run in isolated environments with specific dependencies.

Example:
    Container definition in YAML::

        container:
          image: node:14
          credentials:
            username: ${{ github.actor }}
            password: ${{ secrets.GITHUB_TOKEN }}
          env:
            NODE_ENV: production
          ports:
            - 80
            - "8080:8080"
          volumes:
            - /data:/data
          options: --cpus 2

See Also:
    - ModelJob: Job that uses this container configuration
    - ModelServiceContainer: Service container configuration (sidecars)
"""

from pydantic import BaseModel, Field


class ModelGitHubActionsContainer(BaseModel):
    """GitHub Actions job container configuration.

    Represents the container configuration for running a GitHub Actions job
    in a Docker container. This allows jobs to run in isolated environments
    with specific images, credentials, and resource configurations.

    Attributes:
        image: Docker image to use for the container (required).
            Can be a public image like "node:14" or a private registry image.
        credentials: Registry credentials for private images.
            Typically contains "username" and "password" keys.
        env: Environment variables to set in the container.
            These are available to all steps in the job.
        ports: Ports to expose from the container.
            Can be integers (e.g., 80) or strings with mappings (e.g., "8080:80").
        volumes: Volume mounts for the container.
            Format: "source:destination" or "source:destination:mode".
        options: Additional Docker create options.
            Passed directly to docker create command (e.g., "--cpus 2").

    Example:
        Creating a container configuration::

            container = ModelGitHubActionsContainer(
                image="node:18",
                env={"NODE_ENV": "test"},
                ports=[80, "8080:8080"],
                volumes=["/data:/data:ro"],
                options="--cpus 2 --memory 4g"
            )

    Note:
        When using private registries, credentials should use GitHub secrets
        for security (e.g., ${{ secrets.REGISTRY_PASSWORD }}).
    """

    image: str = Field(
        ...,
        description="Docker image to use for the container",
    )
    credentials: dict[str, str] | None = Field(
        default=None,
        description="Registry credentials (username/password) for private images",
    )
    env: dict[str, str] | None = Field(
        default=None,
        description="Environment variables for the container",
    )
    ports: list[str | int] | None = Field(
        default=None,
        description="Ports to expose from the container (e.g., 80 or '8080:80')",
    )
    volumes: list[str] | None = Field(
        default=None,
        description="Volume mounts in source:destination[:mode] format",
    )
    options: str | None = Field(
        default=None,
        description="Additional Docker create options",
    )
