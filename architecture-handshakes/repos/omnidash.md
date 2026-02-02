# OmniNode Architecture – Constraint Map (omnidash)

> **Role**: Dashboard and visualization – React/TypeScript frontend
> **Handshake Version**: 0.1.0

## Core Principles

- Data-dense enterprise dashboards
- Information density over white space
- Carbon Design System principles (IBM)
- Real-time monitoring with WebSocket updates

## This Repo Contains

- React frontend (Vite + TypeScript)
- Express backend (minimal API surface)
- TanStack Query for server state
- shadcn/ui components (New York variant)
- 9 dashboard routes

## Rules the Agent Must Obey

1. **Port is 3000, not 5000** - Check `package.json` dev script
2. **Always check `.env` file first** - Never assume configuration values
3. **Use TanStack Query for server state** - Not Redux or other state managers
4. **Follow shadcn/ui patterns** - Components in `client/src/components/ui/`
5. **TypeScript strict mode** - No `any` types without justification
6. **Three-directory monorepo**: `client/`, `server/`, `shared/`

## Non-Goals (DO NOT)

- ❌ No Redux or Zustand - use TanStack Query for server state
- ❌ No CSS-in-JS - use Tailwind CSS
- ❌ No hardcoded configuration - read from `.env`
- ❌ No blocking API calls without loading states

## Path Aliases

| Alias | Path | Usage |
|-------|------|-------|
| `@/` | `client/` | React components |
| `@shared/` | `shared/` | Shared types/schemas |

## API Endpoints (port 3000)

```
/api/intelligence/patterns/summary
/api/intelligence/agents/summary
/api/intelligence/events/recent
/api/intelligence/routing/metrics
/api/intelligence/quality/summary
```

## Design System

- **Typography**: IBM Plex Sans/Mono
- **Theme**: Dark mode default, light mode supported
- **Density**: High information density for monitoring
- **Layout**: Sidebar (w-64) + Header (h-16) + Main content
