# Frontend Dashboard

The operator-facing web application for the Smart Waste Bin platform. A single-page React app that gives municipal staff real-time visibility into the entire bin fleet, historical fill trends, active alerts, and — for administrators — the ability to provision and decommission physical bins.

## Role in the Architecture

```
┌─────────────────────────┐         REST + JWT         ┌──────────────┐
│   Frontend Dashboard    │ ─────────────────────────▶ │  API Gateway │
│   (this service)        │ ◀───────────────────────── │              │
└─────────────────────────┘                            └──────────────┘
```

This is a pure client — it holds no business logic of its own. Every number on screen is a direct reflection of what the API Gateway reports; the dashboard's only job is to fetch it, poll for freshness, and present it clearly to an operator, an administrator, or a driver, each with a different view depending on their role.

## Features

- **JWT-based authentication** with role-aware UI (`admin`, `operator`, `driver`), backed by a global `AuthContext`.
- **Live fleet grid** — one card per bin, color-coded by fill level (green `<50%`, amber `50–80%`, red `≥80%`), online/offline status, last-reading timestamp, and a "cleared" badge when recently emptied.
- **Per-bin history chart** — a time-series area chart of fill percentage for the selected bin, built with Recharts.
- **Alert center** — lists open alerts with acknowledge actions, hidden entirely for `driver` accounts (matching the API Gateway's own access rules).
- **Bin provisioning form** (admin only) — registers a new bin (`bin_id`, `zone_id`, `bin_depth_cm`, optional label/coordinates) directly against the API Gateway.
- **Manual overrides** (admin/operator) — force-reset a bin's state after a physical collection, or permanently delete a bin (admin only), with confirmation prompts before either destructive action.
- **Automatic session handling** — a `401`/expired-credentials response from any polling call transparently logs the user out and returns them to `/login`.
- **Client-side route protection** — unauthenticated users are redirected to `/login`; any unknown path falls back to the dashboard (or login, if unauthenticated).

## Tech Stack

| Component         | Choice                                                             |
| ----------------- | ------------------------------------------------------------------ |
| Framework         | React 18 + Vite 5                                                  |
| Routing           | `react-router-dom` v6                                              |
| Styling           | Tailwind CSS v3 (compiled via PostCSS — no CDN dependency)         |
| Charts            | Recharts                                                           |
| Icons             | `lucide-react`                                                     |
| Production server | Nginx (Alpine), serving the static build with SPA fallback routing |

## Project Structure

```
frontend/
├── src/
│   ├── api/
│   │   └── index.js              # Centralized fetch client — one function per API Gateway endpoint
│   ├── context/
│   │   └── AuthContext.jsx       # Session state: token/username/role, backed by sessionStorage
│   ├── hooks/
│   │   └── useDashboardData.js   # Polling, mutations, and derived state for the dashboard page
│   ├── components/
│   │   ├── Header.jsx            # Top bar: branding, provisioning toggle, user badge, refresh, logout
│   │   ├── BinCard.jsx           # Single bin summary tile in the fleet grid
│   │   ├── HistoryChart.jsx      # Time-series chart + admin/operator action buttons for the selected bin
│   │   ├── AlertList.jsx         # Open alerts panel with acknowledge action
│   │   └── ProvisioningForm.jsx  # Admin-only new-bin registration form
│   ├── pages/
│   │   ├── Login.jsx             # Public login screen
│   │   └── Dashboard.jsx         # Authenticated main view, composes the components above
│   ├── App.jsx                    # Route table + ProtectedRoute guard
│   ├── main.jsx                   # Entry point, wraps <App /> in <AuthProvider />
│   └── index.css                  # Tailwind directives
├── index.html
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── nginx.conf                     # SPA fallback routing for production
├── Dockerfile
├── package.json
└── package-lock.json
```

## Data Flow

`useDashboardData` runs two independent polling loops:

1. **Fleet polling** (every 3 seconds) — fetches `GET /api/bins` and `GET /api/alerts` in parallel. A `403` on alerts (expected for `driver` accounts, which the API Gateway blocks from that endpoint) is treated as an empty list rather than an error.
2. **History polling** (every 3 seconds, only while a bin is selected) — fetches `GET /api/bins/{id}/history` for the currently selected card.

Any authentication failure (`401` or a credentials-related error message) during either loop triggers an automatic logout, so a session that has expired server-side doesn't leave the UI silently stuck on stale data.

## Configuration

The API base URL is derived at runtime from the browser's own hostname rather than a build-time environment variable:

```js
const API_BASE_URL = `http://${window.location.hostname}:8000`;
```

This means the dashboard automatically points at the API Gateway on the same host it was served from, on port `8000`, with no rebuild required when moving between environments — as long as the API Gateway is reachable on that host/port combination. If the gateway is deployed behind a different host or port (e.g. behind a reverse proxy on a standard HTTPS port), this constant is the single place to adjust.

Session data (`token`, `username`, `role`) is kept in `sessionStorage`, so a session is automatically cleared when the browser tab is closed, rather than persisting indefinitely like `localStorage` would.

## Running Locally

### Development server

```bash
npm ci
npm run dev
```

Runs on `http://localhost:5173` with hot module reloading.

### Production build via Docker

```bash
docker build -t frontend-dashboard .
docker run --rm -p 80:80 frontend-dashboard
```

The build is a two-stage Docker image: `node:20-alpine` compiles the Vite production bundle with `npm ci` (using the committed `package-lock.json` for fully reproducible installs, with fail-fast network retry limits to avoid hanging builds), and the static output is served by `nginx:1.25-alpine`. The included `nginx.conf` adds SPA fallback routing (`try_files ... /index.html`) so that deep links and browser refreshes on client-side routes (e.g. `/`) don't return a 404 from Nginx.

## Design Notes

- **Why poll instead of a WebSocket/SSE connection?** At current fleet scale, a fixed 3-second polling interval keeps the UI responsive without the added operational complexity of a persistent connection. This is a known area to revisit (in favor of Server-Sent Events or WebSockets) as the fleet grows into the hundreds/thousands of bins, where polling the full bin list every few seconds stops being cheap.
- **Why is role-based UI enforced client-side at all, if the API Gateway already enforces RBAC server-side?** The server-side checks are the actual security boundary — the client-side role checks here (hiding the alerts panel from drivers, hiding admin actions from operators) exist purely for a cleaner, less confusing user experience, not as a security control. A driver account calling the API directly would still be correctly rejected by the gateway regardless of what this UI shows or hides.
- **Known limitation:** the bin registry is currently a single flat grid with no pagination, search, or map view. This is adequate at pilot scale; as the fleet grows, this is the first area planned for expansion (a dedicated paginated/filterable bins page and a geographic map view, both already supported by the coordinate fields captured during provisioning).
