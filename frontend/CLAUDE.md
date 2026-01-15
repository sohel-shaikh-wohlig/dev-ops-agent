# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
npm run dev       # Start Vite dev server (http://localhost:5173)
npm run build     # TypeScript check + Vite production build
npm run lint      # ESLint check
npm run preview   # Preview production build locally
```

## Architecture Overview

This is a **React 19 + Vite + TypeScript** GitOps automation dashboard for managing ArgoCD applications. The UI follows Metronic design patterns with a light/dark theme system.

### Tech Stack
- **React 19** with React Router DOM 7 for routing
- **Vite 7** as build tool
- **TanStack Query** for server state management (auto-refetch, caching)
- **TanStack Table** for complex data tables (sorting, filtering, pagination)
- **TanStack Form + Zod** for type-safe form handling and validation
- **Tailwind CSS 4** + Radix UI primitives (Shadcn/ui pattern)
- **Sonner** for toast notifications
- **Lucide React** for icons

### Path Alias
`@/` resolves to `src/` (configured in vite.config.ts and tsconfig)

## Project Structure (Feature-based)

```
src/
├── components/
│   ├── layout/              # Sidebar, Topbar (global layout)
│   └── ui/                  # Shadcn/ui primitives (button, card, badge, etc.)
├── features/                # Self-contained feature modules
│   ├── argocd/
│   │   ├── components/      # DeploymentCard, StatusBadge, ApplicationSidebar
│   │   ├── services/        # argocd-service.ts (API calls + data mapping)
│   │   ├── types/           # ArgoCD + Deployment types
│   │   ├── ArgoCDPage.tsx   # Main page component
│   │   └── index.ts         # Barrel exports
│   ├── dashboard/
│   │   ├── DashboardPage.tsx
│   │   └── index.ts         # Barrel exports
│   └── members/
│       ├── components/      # MemberManagement, AddMemberForm
│       ├── services/        # member-service.ts
│       ├── types/           # Member types
│       └── index.ts         # Barrel exports
├── services/                # Shared services
│   └── api-client.ts        # Base HTTP client (http://localhost:8000/api)
├── hooks/                   # Shared hooks (useGitOpsData)
└── lib/utils.ts             # cn() utility for className merging
```

### Feature Module Pattern
Each feature is self-contained with its own components, services, types, and barrel export:
```typescript
// Import from feature barrel exports
import { DashboardPage } from "@/features/dashboard";
import { ArgoCDPage, DeploymentCard } from "@/features/argocd";
import { MemberManagement, type Member } from "@/features/members";
```

## Key Patterns

### API Client Pattern
- Base client in `services/api-client.ts` points to `http://localhost:8000/api`
- Feature services (e.g., `argocd-service.ts`) extend base client with domain-specific endpoints
- Data mapping functions transform API responses to UI types

### Component Variants (CVA)
UI components use `class-variance-authority` for variants:
```typescript
// Example: badge variants
variant: "default" | "success" | "warning" | "error" | "outline" | "secondary" | "destructive"
```

### React Query Usage
Queries use consistent patterns:
```typescript
useQuery({
  queryKey: ['argocd-applications'],
  queryFn: fetchApplications,
  refetchInterval: 30000,  // Auto-refetch intervals vary by feature
})
```

### Theme System
- CSS variables defined in `index.css` using HSL values
- `ThemeProvider` context with `useTheme()` hook
- Supports "light", "dark", "system" modes
- Class-based dark mode (`darkMode: "class"` in Tailwind)

## Routes

- `/` - Dashboard landing page
- `/argocd` - ArgoCD applications management (main feature)
- `/members` - Team member management with data table
- `*` - Redirects to `/`

## Type Definitions

### Deployment Status Types (features/argocd/types)
```typescript
type DeploymentStatus = "Healthy" | "Progressing" | "Degraded"
type HealthStatus = "Healthy" | "Progressing" | "Degraded" | "Missing"
type SyncStatus = "Synced" | "OutOfSync" | "Unknown"
```

## Development Notes

- Backend API expected at `http://localhost:8000/api`
- ArgoCD endpoints: `/argocd/applications`, `/argocd/applications/{appName}`
- Toast notifications use `toast()` from sonner
- Date formatting uses date-fns (`formatDistanceToNow` for relative times)
