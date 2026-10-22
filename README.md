# RoadSense Vision — Phase 2 public web application

A map-first civic website for exploring potholes recorded by RoadSense road-monitoring
vehicles. The app shows **canonical potholes only** — repeated vehicle observations are
deduplicated server-side before publication — and preserves provenance for linked road and
public-works records.

## What is included

- **Public map** with a canonical feed loaded once, clustering, PIN code search, time filters,
  deep links, and a pothole preview card.
- **Detections ledger** with server-side search, time filters, pagination, empty/loading/error
  states, and mobile card layout.
- **Pothole detail** page with road metadata, confidence, observation history summary, a
  micro-location inset, and source-backed contract records.
- **About** and **Public Data Note** pages.
- **Read-only public API** with an authenticated ingestion endpoint for fleet observations.
- **PostgreSQL/PostGIS production path** with real geometry, geography, GiST indexes, and sync
  triggers, plus a zero-setup SQLite fallback for local development and tests.
- **Deployment assets**: multi-stage frontend image, gunicorn backend image, nginx proxy, and
  Docker Compose with PostGIS.

## Architecture

```
RoadSense Android app (Phase 1)
        │  POST /api/v1/internal/reports  (Bearer ingest key)
        ▼
Flask API ── deduplication ──► PostgreSQL + PostGIS
        │                         canonical_potholes
        │                         detection_reports
        │                         road_segments / road_projects
        │  GET /api/v1/*  (read-only)
        ▼
React + Vite public site ── MapLibre GL JS / React Query
        │
        ├── MapTiler Streets vector tiles (Stadia fallback)
        └── server-side Nominatim proxy for PIN code search
```

The Flask API and PostgreSQL/PostGIS run on the home server at the Tailscale address
`100.104.179.69`. The browser reaches Flask at `http://100.104.179.69:5001`; it never connects
to PostgreSQL and never receives raw observations, camera media, sensor payloads, device
identifiers, or internal identifiers. The Android app performs all YOLO inference locally and
only sends the existing minimal ingestion payload (report ID, GPS coordinates, timestamp,
confidence, and GPS accuracy) to the home-server API.

## Quick start (SQLite, no Docker)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app wsgi:app run --debug --port 5001
```

Without `DATABASE_URL`, the API uses `backend/instance/roadsense.db` and creates the schema on
boot. Check it with:

```bash
curl http://127.0.0.1:5001/api/v1/health
curl http://127.0.0.1:5001/api/v1/meta
```

### Frontend

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

`frontend/.env.local` uses the home-server API directly:

```env
VITE_API_BASE_URL=http://100.104.179.69:5001/api/v1
```

Open http://localhost:5173. The browser calls Flask over Tailscale; the backend allows the
local and Tailscale Vite origins through `CORS_ORIGINS`. PostgreSQL is never contacted by the
browser. The local map uses Stadia keyless access; see [Frontend](#frontend-1) for deployed
basemap keys.

For a same-origin alternative, set `VITE_API_BASE_URL=/api/v1` and
`VITE_API_PROXY_TARGET=http://100.104.179.69:5001`; Vite then proxies `/api` to Flask.

### Tests and checks

```bash
# backend
cd backend
.venv/bin/pytest -q

# frontend
cd frontend
npm test
npm run typecheck
npm run lint
npm run build
```

The backend suite covers bbox filtering, nearby queries, pagination/search, detail and road
endpoints, PIN code validation/geocoding, read-only behaviour, ingestion authentication,
deduplication, and contractor provenance rules. Test fixtures are synthetic and never loaded
into a production database.

## Docker Compose (PostGIS)

```bash
cp .env.example .env
# Edit POSTGRES_PASSWORD, INGEST_API_KEY, and GEOCODING_USER_AGENT.
docker compose up --build
```

Open http://localhost:8091. Services:

- `db` — PostGIS 16 / PostGIS 3.4, internal to the Compose network only.
- `backend` — gunicorn on container port 5000, published on the home server as
  `API_BIND_ADDRESS:API_PORT` (default `0.0.0.0:5001`).
- `frontend` — nginx on port 80, published as `WEB_PORT`; the default image points directly at
  `http://100.104.179.69:5001/api/v1`, while the nginx `/api/` proxy remains available for
  same-origin builds.

The API is available on the home server at `http://100.104.179.69:5001/api/v1/*`. Bind the API
to the Tailscale/LAN interface and keep the host firewall closed to the public internet unless
the read-only public API is intentionally exposed. PostgreSQL is never published.

The compose backend runs a one-time schema initialisation from its entrypoint
(`RUN_DB_INIT=true`) before gunicorn starts. For a production deployment, disable that and run
schema setup as a single deploy step instead:

```bash
# set RUN_DB_INIT=false in the backend environment
docker compose run --rm backend flask --app wsgi:app init-db
```

Then start the services. Use HTTPS at the edge, restrict `CORS_ORIGINS` to real origins, and
replace the development secrets.

### Home-server API connectivity

The home server is reachable over Tailscale at `100.104.179.69`, and Flask listens on port
`5001`. The complete browser-facing base, including `/api/v1`, is:

```env
VITE_API_BASE_URL=http://100.104.179.69:5001/api/v1
```

`frontend/.env.example` contains this value, and `frontend/.env.local` (ignored by Git) is
configured for the current Tailscale deployment. The browser talks to Flask directly; it never
talks to PostgreSQL.

The backend CORS defaults allow these website origins:

```text
http://localhost:5173
http://127.0.0.1:5173
http://100.104.179.69:5173
http://localhost:5174
http://127.0.0.1:5174
http://100.104.179.69:5174
http://localhost:8091
http://127.0.0.1:8091
http://100.104.179.69:8091
```

If Vite uses another port or hostname, add that exact origin to `CORS_ORIGINS` and restart the
API. For an HTTPS production deployment, use an HTTPS API base and add the production website
origin; do not send the public site over HTTPS while calling an HTTP API.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Liveness check |
| `GET` | `/api/v1/meta` | Canonical pothole count and latest observation time |
| `GET` | `/api/v1/potholes?bbox=...` | Canonical potholes in a bounding box |
| `GET` | `/api/v1/potholes/recent` | Paginated ledger with `q`, `since`, `limit`, `offset` |
| `GET` | `/api/v1/potholes/nearby` | Potholes within a radius of a coordinate |
| `GET` | `/api/v1/potholes/<PH-ID>` | Detail payload |
| `GET` | `/api/v1/roads/<id>` | Road, linked project, and recent potholes |
| `GET` | `/api/v1/geocode?pincode=691001` | Server-side PIN code lookup |
| `POST` | `/api/v1/internal/reports` | Authenticated fleet ingestion |

Bounding boxes use `min_lng,min_lat,max_lng,max_lat`. Public reads are capped by
`PUBLIC_MAX_LIMIT`; the map requests at most 2,000 recent canonical records once and applies
time-period filters client-side.

### Ingestion payload

```http
POST /api/v1/internal/reports
Authorization: Bearer <INGEST_API_KEY>
Content-Type: application/json

{
  "report_id": "device-42-2026-10-21T09-32-11Z",
  "latitude": 8.893214,
  "longitude": 76.614102,
  "observed_at": "2026-10-21T09:32:11+05:30",
  "confidence": 0.94,
  "gps_accuracy_m": 4.2
}
```

`report_id` is idempotent. Nearby observations inside `DEDUPE_RADIUS_M` and
`DEDUPE_WINDOW_DAYS` are merged into one canonical pothole. The endpoint returns
`duplicate_report: true` for a repeated `report_id` and `created` to distinguish new canonical
records. The current Android app still keeps observations in its local Room database; wiring it
to this endpoint is a separate integration step.

## Data and editorial rules

- **Canonical only**: individual `detection_reports` are never used as map markers.
- **No proximity inference**: a contractor is never inferred from the nearest coordinate or a
  similar road name.
- **Provenance-aware contractor display**: a contractor name is shown only when the linked
  project has `verification_status` of `verified` or `unverified`. A record marked `verified`
  without a source is downgraded to `unknown`.
- **No false negatives**: absence of a marker means the road may not have been surveyed, not
  that it is defect-free.
- **PIN search** goes through the API rather than the browser, so the geocoder user agent and
  rate limiting remain under server control.

## Configuration

### Backend

| Variable | Default | Notes |
| --- | --- | --- |
| `DATABASE_URL` | SQLite file | Use `postgresql://...` in production |
| `AUTO_INIT_DB` | `true` | Set `false` in production and run `init-db` |
| `INGEST_API_KEY` | empty | Ingestion returns `503` when unset |
| `CORS_ORIGINS` | local and Tailscale Vite/Compose origins | Comma-separated exact origins |
| `DEDUPE_RADIUS_M` | `25` | Canonical merge radius |
| `DEDUPE_WINDOW_DAYS` | `45` | Canonical merge window |
| `ROAD_MATCH_RADIUS_M` | `30` | Road-segment matching tolerance |
| `GEOCODING_PROVIDER_URL` | Nominatim | No API key required by default |
| `GEOCODING_USER_AGENT` | development value | Set a real contact address |
| `PUBLIC_DEFAULT_LIMIT` / `PUBLIC_MAX_LIMIT` | `500` / `2000` | Public read caps |

### Frontend

See `frontend/.env.example`. The API variables are:

| Variable | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | Complete browser-facing API base, including `/api/v1`; default `http://100.104.179.69:5001/api/v1` |
| `VITE_API_PROXY_TARGET` | Optional Flask origin for the same-origin `/api` proxy alternative |

Map variables select the vector basemap:

| Variable | Purpose |
| --- | --- |
| `VITE_MAP_PROVIDER` | Optional override: `maptiler` or `stadia`; otherwise MapTiler is chosen when its key exists, else Stadia |
| `VITE_MAPTILER_API_KEY` | MapTiler browser key; preferred when present |
| `VITE_MAPTILER_STYLE_URL` | MapTiler style JSON; defaults to `streets-v2-light` |
| `VITE_STADIA_API_KEY` | Stadia Maps browser key; Stadia is keyless for localhost development only |
| `VITE_STADIA_STYLE_URL` | Stadia style JSON; defaults to `alidade_smooth` |

Other values control the initial map view. Keep provider attribution visible. The Compose
frontend build accepts `VITE_API_BASE_URL` and the map variables from the root `.env`; it points
at the Tailscale Flask API by default. If no provider key is available or the style cannot load,
the map falls back to a plain background and keeps the canonical pothole layers visible.

## Production notes

- Terminate TLS at a reverse proxy or load balancer; the bundled nginx speaks HTTP internally.
- Add rate limiting and caching at the edge for `/api/v1/geocode` and public reads.
- Keep the ingest key in a secret manager and rotate it.
- Publish the Flask API only on the intended LAN/Tailscale interface. Never publish PostgreSQL
  (`5432`) or give the frontend database credentials.
- Back up the PostGIS volume and run migrations before deploying schema changes.
- Set a valid contact in `GEOCODING_USER_AGENT` and respect provider usage policies.
- Restrict vector basemap keys to the deployed origin in the provider dashboard. Stadia
  keyless access is for localhost only; deployed builds need MapTiler or Stadia credentials.
- Review provider quotas before high-traffic deployment.

## Project layout

```
backend/        Flask API, spatial services, serializers, schema, tests
frontend/       React + Vite app, map, pages, styles, nginx config
docker-compose.yml
.env.example    Compose secrets and deployment settings
Design files/   Supplied visual references
```

## Known limitations

- Local SQLite fallback is for development and testing, not production scale.
- The website has no account system; all published data is public.
- Repair status is stored data and is not inferred or automatically updated.
- Geocoding depends on the external Nominatim service; failures are surfaced in the UI.
- Android ingestion is implemented with an offline WorkManager queue; physical-device
  validation of the upload/retry path is still pending.
- The Tailscale address is deployment-specific; update `VITE_API_BASE_URL`, the Android build
  property, and `CORS_ORIGINS` if the home server's Tailscale IP changes.
