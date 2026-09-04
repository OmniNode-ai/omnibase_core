# OmniNode Architecture – Constraint Map (omnidash)

> **Role**: Composable widget dashboard — Vite + React frontend, services-led
> **Handshake Version**: 0.2.0

## Core Principles

- Widgets render authoritative projection/API data and presentation-only state; they never create truth ([OmniNode deterministic truth doctrine](https://github.com/OmniNode-ai/omni_home/blob/main/docs/standards/OMNINODE_DETERMINISTIC_TRUTH_DOCTRINE.md)).
- Information density over white space; IBM Plex Sans/Mono typography (`src/styles/globals.css`).
- Live updates are HTTP polling (`useProjectionQuery`) only. The `/ws` WebSocket path was permanently removed (OMN-12969) after the projection backend rejected the upgrade (403) and never delivered an event; raw WebSocket construction is blocked by the `local/no-projection-websocket` ESLint rule. <!-- doc-content-ok: OMN-12969 substantiates why this constraint exists, not a stale/dangling reference -->

## This Repo Contains

- Vite + React 19 SPA (TypeScript). There is no `client/` directory — app code lives in `src/`.
- Express bridge (`server/`) used only in `http`/`sqlite`/`postgres` data-source modes — a thin HTTP proxy to the projection-api and the onboarding routes, not a general backend.
- TanStack Query (`@tanstack/react-query`) for server state, alongside Zustand (`zustand`) for client/UI state (edit mode, layout, filters). Both are live core deps used together, not alternatives.
- shadcn/ui primitives (`components.json`: `style: "default"`, base color `slate`) in `src/components/ui/` — a handful of primitives (`button`, `input`, `tooltip`, `separator`, `positioned-menu`, `typography`), not the "New York" variant and not a full component library.
- Dashboard widgets under `src/components/dashboard/` — count drifts, verify live with `ls src/components/dashboard | wc -l` rather than trusting a stamped number here; see `docs/implementation-status.md`.

## Rules the Agent Must Obey

1. **Vite dev port is 3001, Express bridge port is 3002** — not 3000/5000. See `vite.config.ts` (`VITE_DEV_PORT` env override) and `server/index.ts` (`PORT` env override).
2. **Always check `.env` file first** - Never assume configuration values.
3. **TanStack Query for server state, Zustand for client/UI state** - both are used together in this repo; neither replaces the other.
4. **Follow shadcn/ui patterns** - Components live in `src/components/ui/`, not `client/src/components/ui/`.
5. **TypeScript strict mode** - No `any` types without justification.
6. **Repo layout is `src/` + `server/` + `shared/`** - there is no `client/` directory; do not treat this as a three-way `client/server/shared` monorepo.

## Platform-Wide Rules

1. **No backwards compatibility** - Breaking changes always acceptable. No deprecation periods, shims, or migration paths.
2. **Delete old code immediately** - Never leave deprecated code "for reference." If unused, delete it.
3. **No speculative refactors** - Only make changes that are directly requested or clearly necessary.
4. **No silent schema changes** - All schema changes must be explicit and deliberate.
5. **Frozen event schemas** - All models crossing boundaries (events, intents, actions, envelopes, projections) must use `frozen=True`. Internal mutable state is fine.
6. **Explicit timestamps** - Never use `datetime.now()` defaults. Inject timestamps explicitly.
7. **No hardcoded configuration** - All config via `.env` or Pydantic Settings. No localhost defaults.
8. **No direct Kafka/backend-DB access from this repo** - omnidash reads via the HTTP projection-api only (`src/data-source/`); Kafka event-bus infrastructure is owned by `omnibase_infra`, out of this repo's scope.
9. **No unexplained type-suppression** - `@ts-expect-error` / ESLint-disable comments require an explanation and ticket reference.

## Non-Goals (DO NOT)

- ❌ No CSS-in-JS - use Tailwind CSS (plus vanilla-extract for the small set of files that need it: `@vanilla-extract/css`, `@vanilla-extract/recipes`)
- ❌ No blocking API calls without loading states
- ❌ No component reading `VITE_DATA_SOURCE` directly - always go through `resolveEffectiveDataSource()` (`src/data-source/data-source-override.ts`), the single runtime-override seam
- ❌ No hand-editing generated artifacts - `src/registry/component-registry.json` (`npm run generate:registry`), `src/config/generated/data-source-defaults.ts` (`npm run generate:config`)

## Path Aliases

| Alias | Path | Usage |
|-------|------|-------|
| `@/` | `src/` | React components (`tsconfig.json`, `vite.config.ts`) |
| `@shared/` | `shared/` | Shared types/schemas |

## API Endpoints

There is no `/api/intelligence/*` surface. The Express bridge (port 3002) serves onboarding + projection-proxy routes (`server/onboarding/onboarding-routes.ts`, `server/routes.ts`):

```
POST /api/onboarding/provision
GET  /api/onboarding/me
GET  /projection/:topic          (proxied to the projection-api base URL in http mode)
```

## Design System

- **Typography**: IBM Plex Sans/Mono (`src/styles/globals.css` `:root` tokens), rendered only through `<Text>`/`<Heading>` (`src/components/ui/typography`) — enforced by the `local/no-typography-inline` ESLint rule.
- **Density**: High information density for monitoring.
- **Data-source mode banner**: `src/components/frame/DataModeBanner.tsx` — visible in `file`/`sqlite` modes, hidden in `http`/`postgres`. Live default mode is `http` (`contract.yaml`, OMN-14642) — do not assume a zero-infra default. <!-- doc-content-ok: OMN-14642 substantiates why the default mode is http, not a stale/dangling reference -->
