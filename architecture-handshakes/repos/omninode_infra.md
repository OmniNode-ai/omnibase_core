# OmniNode Architecture – Constraint Map (omninode_infra)

> **Role**: Infrastructure services – AWS, k3s, Kubernetes, deployment
> **Handshake Version**: 0.1.0

## Core Principles

- Infrastructure as Code (Terraform)
- Kubernetes-native deployment
- OIDC-based authentication (no long-lived credentials)
- Least-privilege IAM policies

## This Repo Contains

- Terraform modules (`aws/`) for VPC, k3s, IAM
- Kubernetes manifests (`k8s/`) for data-plane, auth, observability
- Database migrations (`db/`) for Postgres
- onex-api FastAPI service (`docker/onex-api/`)
- Deployment scripts (`scripts/`)

## Rules the Agent Must Obey

1. **All tasks MUST run as Polymorphic Agent (Polly)** - Never background execution
2. **Never run agents in background** - No `run_in_background: true`
3. **For parallel tasks, spawn multiple parallel Pollys** - Single message, multiple Task calls
4. **Use internal DNS for service discovery** - e.g., `omninode-postgres.data-plane.svc.cluster.local`
5. **PodSecurityContext with non-root users** - Security baseline
6. **OIDC for CI/CD** - No long-lived credentials in GitHub Actions

## Non-Goals (DO NOT)

- ❌ No long-lived credentials - Use OIDC
- ❌ No running as root in containers
- ❌ No hardcoded secrets - Use Kubernetes secrets
- ❌ No background agent execution

## Kubernetes Namespaces

| Namespace | Purpose |
|-----------|---------|
| `data-plane` | Postgres, Redpanda, Qdrant, Memgraph |
| `auth` | Keycloak with `omninode` realm |
| `onex-dev` | onex-api backend + omniweb frontend |
| `observability` | Grafana dashboards |
| `system` | Traefik ingress, cert-manager |

## Authentication

Dual-mode auth in onex-api:
- **OIDC JWT** from Keycloak (primary)
- **API key** via `x-api-key` header (programmatic access)

## Database Migrations

- Sequential migrations with advisory locks
- Concurrent index creation for production
- Rollback scripts for each migration
