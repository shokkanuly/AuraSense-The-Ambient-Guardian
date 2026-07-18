# Frontend / Dashboard Subsystem Conventions — AuraSense

## Purpose
The fleet-management dashboard is a web UI for power users / installers — not the primary consumer interface (that's the Flutter app). It provides:
- Node health and status overview
- Historical time-series charts (energy, anomaly scores)
- Event log and alert management
- OTA firmware management
- Model performance monitoring

## Stack
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript (strict mode)
- **Styling**: Tailwind CSS + shadcn/ui components
- **Charts**: Recharts
- **State**: Zustand for client state; React Query (TanStack) for server state
- **Auth**: JWT from hub API (same token as mobile)

## API integration
- All hub API calls go through `lib/api/hub-client.ts` — a typed fetch wrapper
- Types are generated from `shared/types/api_types.py` via `scripts/gen_ts_types.py`
- Never hand-write TypeScript types that duplicate backend types

## Folder structure
```
app/
  (dashboard)/
    page.tsx          # overview
    nodes/page.tsx
    events/page.tsx
    settings/page.tsx
  layout.tsx
  globals.css
components/
  ui/                 # shadcn primitives
  charts/             # Recharts wrappers
  nodes/              # node-specific components
lib/
  api/                # hub-client.ts, query hooks
  store/              # Zustand stores
  utils/
```

## WebSocket
- Dashboard subscribes to `/ws/v1/events` for live event updates
- Managed in `lib/api/event-socket.ts` with auto-reconnect

## Conventions
- Page components are Server Components by default; use `"use client"` only when needed
- No direct DB access from frontend — always goes through hub API
- All date/times displayed in local timezone; stored as UTC Unix timestamps internally
