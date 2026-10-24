# RoadSense Vision — Phase 2 public web application

A map-first civic website for exploring potholes recorded by RoadSense road-monitoring
vehicles. The app shows **canonical potholes only** — repeated vehicle observations are
deduplicated server-side before publication — and preserves provenance for linked road and
public-works records. A self-hosted research worker uses SearXNG and a small local Ollama
model to look for public tender/work-order evidence for each road.

## What is included

- **Public map** with a canonical feed loaded once, clustering, PIN code search, time filters,
  deep links, and a pothole preview card.
- **Detections ledger** with server-side search (including cached road, locality, district,
  state, and PIN), time filters, pagination, empty/loading/error states, and mobile card
  layout.
- **Pothole detail** page with cached reverse-geocoded address/road metadata, confidence,
  observation history summary, a micro-location inset, and source-backed contract records.
- **Automated public-record research** with deterministic search queries, SSRF-safe fetching,
  strict JSON extraction, cached results, and explicit `high`/`medium`/`low` confidence.
  Only a `high` result is shown as a verified contractor.
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
        │                         pothole_location_metadata (cached reverse geocoding)
        │                         pothole_research_runs / pothole_research_sources
        │  GET /api/v1/*  (read-only)
        ▼
React + Vite public site ── MapLibre GL JS / React Query
        │
        └── research worker ──► SearXNG ──► public web/PDF
                              └► Ollama (qwen3:0.6b, extraction only)
        │
        ├── MapTiler Streets vector tiles (Stadia fallback)
        ├── server-side MapTiler reverse geocoding for pothole addresses
        └── server-side Nominatim proxy for PIN code search
```

The Flask API and PostgreSQL/PostGIS run on the home server at the Tailscale address
`100.104.179.69`. The browser calls the same-origin path `/api/v1/*`; Vite (development) and
the bundled nginx (production) proxy that path to Flask. The browser never connects
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

`frontend/.env.local` uses the same-origin API path, which Vite proxies to the local Flask
server:

```env
VITE_API_BASE_URL=/api/v1
VITE_API_PROXY_TARGET=http://127.0.0.1:5001
```

Open http://localhost:5173/roadsense/. The browser calls `http://localhost:5173/api/v1/*`, so
there is no cross-origin request and no Tailscale address in the bundle. PostgreSQL is never
contacted by the browser. The local map uses Stadia keyless access; see
[Frontend](#frontend-1) for deployed basemap keys.

To use the deployed server during local development, point
`VITE_API_PROXY_TARGET` at the deployed HTTPS root and restart Vite:

```env
VITE_API_PROXY_TARGET=https://server.tailda589d.ts.net/roadsense
```

This makes the local website read the same canonical records that the Android fleet uploads.
Do not assume the Compose backend is directly reachable at `100.104.179.69:5001`; use the
Tailscale Funnel HTTPS root above. Keep `VITE_API_BASE_URL=/api/v1` so the browser stays
same-origin. Use `http://127.0.0.1:5001` only when intentionally reading the isolated local
SQLite database. Do not bake a machine-specific address into `VITE_API_BASE_URL` unless the
browser is meant to call Flask directly.

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
endpoints, PIN code validation/geocoding, reverse-geocoding parsing/caching, read-only
behaviour, ingestion authentication, deduplication, contractor provenance rules, research
query generation, road-alias matching, source selection/ranking, and strict result validation.
Test fixtures are synthetic and never loaded into a production database.

## Docker Compose (PostGIS)

```bash
cp .env.example .env
# Edit POSTGRES_PASSWORD, INGEST_API_KEY, MAPTILER_API_KEY,
# MAPTILER_REFERER (when the key is origin-restricted), SEARXNG_SECRET,
# and RESEARCH_ADMIN_KEY.
docker compose up --build
```

Open http://localhost:8091. Services:

- `db` — PostGIS 16 / PostGIS 3.4, internal to the Compose network only.
- `backend` — gunicorn on container port 5000, published on the home server as
  `API_BIND_ADDRESS:API_PORT` (default `0.0.0.0:5001`).
- `frontend` — nginx on port 80, published as `WEB_PORT`; the app is served under
  `/roadsense/`, and nginx proxies `/api/` to `API_ORIGIN` (default `backend:5000`). Set
  `API_ORIGIN` to the deployed HTTPS root when the local website should read fleet data.
- `searxng` — private metasearch service used only by the backend/worker. The default
  deployment uses the `yep` engine; CAPTCHAs and provider blocks are not bypassed.
- `ollama` / `ollama-init` — private local model runtime and one-time
  `qwen3:0.6b` pull. The model extracts structured facts; it does not browse the web.
- `research-worker` — DB-backed queue worker for asynchronous road research.

The API is also available directly on the home server at
`http://100.104.179.69:5001/api/v1/*` for the Android app and diagnostics. Bind the API
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

### Reverse-geocoding existing records

New canonical potholes get a `pending` metadata row and are enriched in the background after
ingestion. Existing records can be backfilled without changing their coordinates:

```bash
docker compose exec backend flask --app wsgi:app enrich-locations --limit 100
docker compose exec backend flask --app wsgi:app enrich-locations --pothole PH-000003
docker compose exec backend flask --app wsgi:app enrich-locations --retry-failed
docker compose exec backend flask --app wsgi:app enrich-locations --force
```

Public reads only use cached metadata; they never call the provider. `MAPTILER_API_KEY` is
server-side only. If the key is origin-restricted, set `MAPTILER_REFERER` to the exact allowed
site origin, including any path and trailing slash.

### Automated public-record research

The backend builds deterministic road-level queries from cached road, locality, district,
state, PIN code, municipality, authority, and administrative-area metadata. Official-domain
queries are state-aware; there are no hardcoded road names, tender numbers, contractors, or
pothole-specific aliases. The worker searches through the private SearXNG service, fetches a
limited number of public HTML/PDF pages with SSRF protections and size/time limits, and asks
Ollama for strict JSON extraction. The backend validates the extracted text, source URL, road
match, location context, and authority; the model's own confidence is ignored.

Road matching requires the target road plus locality, district, PIN, municipality, or
administrative-area context. A generic road base name (for example, “Engineering College”
from “Engineering College Road”) is accepted only when the source also contains a road term
and a strong location signal. The same road name in another district is rejected.

Results are cached for `RESEARCH_CACHE_DAYS` and stored in `pothole_research_runs` and
`pothole_research_sources`, separately from canonical potholes. Each fetched source stores
its URL, rank, tier, query, fetch status, text length, and `retrieved_at` timestamp. A result
is displayed as:

- `high` — a cited government/official source explicitly links the road to a contractor;
- `medium` — a cited source lists a related work/tender record, including records without a
  contractor; the UI says to verify the official record;
- `low` — no contractor is displayed.

Run one target synchronously:

```bash
docker compose exec backend flask --app wsgi:app research-pothole PH-000003 --force
```

Or enqueue it for the worker (requires `RESEARCH_ADMIN_KEY`):

```bash
curl -X POST http://127.0.0.1:5001/api/v1/internal/potholes/PH-000003/research \
  -H "Authorization: Bearer $RESEARCH_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

The browser never calls SearXNG, Ollama, or the internal research endpoints. Public detail
reads only the latest stored run. The detail page also exposes a public “Research again”
action:

```http
POST /api/v1/potholes/PH-000003/research
```

It returns `202` with a pending run, `429` with `Retry-After` while
`RESEARCH_REFRESH_COOLDOWN_SECONDS` is active, `409` when road metadata is unresolved, and
`503` when research is disabled or temporarily unavailable. Failed runs may be retried
immediately. Do not bypass CAPTCHAs, paywalls, or provider blocks.

### Home-server API connectivity

The home server is reachable over Tailscale at `100.104.179.69`, and Flask listens on port
`5001` for the Android app and diagnostics. The browser-facing base is the same-origin path:

```env
VITE_API_BASE_URL=/api/v1
```

`frontend/.env.example` contains this value, and `frontend/.env.local` (ignored by Git) pairs it
with `VITE_API_PROXY_TARGET=http://127.0.0.1:5001` for development. The deployed nginx proxies
`/api/` to `API_ORIGIN` inside the Compose network. The browser never talks to PostgreSQL and
never needs the Tailscale address.

Local development and the deployed website use separate databases by default. To make the
local website read the same canonical records as the Android fleet, point both proxies at the
deployed HTTPS root and restart the affected services:

```env
# frontend/.env.local (Vite)
VITE_API_PROXY_TARGET=https://server.tailda589d.ts.net/roadsense

# .env (Compose frontend nginx)
API_ORIGIN=https://server.tailda589d.ts.net/roadsense
```

Keep `VITE_API_BASE_URL=/api/v1`; do not append `/api` or `/api/v1` to `API_ORIGIN`.
The default `API_ORIGIN=http://backend:5000` intentionally keeps a standalone local Compose
stack self-contained. Production should leave the default so nginx reaches its own backend.

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
| `POST` | `/api/v1/potholes/<PH-ID>/research` | Public manual refresh with cooldown |
| `GET` | `/api/v1/roads/<id>` | Road, linked project, and recent potholes |
| `GET` | `/api/v1/geocode?pincode=691001` | Server-side PIN code lookup |
| `POST` | `/api/v1/internal/reports` | Authenticated fleet ingestion |
| `POST` | `/api/v1/internal/potholes/<PH-ID>/research` | Enqueue research (`RESEARCH_ADMIN_KEY`) |
| `GET` | `/api/v1/internal/potholes/<PH-ID>/research` | Inspect latest research run (`RESEARCH_ADMIN_KEY`) |

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
- **Coordinate-derived addresses only**: reverse geocoding uses the canonical GPS coordinate.
  Provider-returned road name, locality, district, state, country, and PIN are cached in
  `pothole_location_metadata`; missing route numbers, classifications, and authorities stay
  unset instead of being guessed.
- **Provenance-aware contractor display**: a contractor name is shown only when the linked
  project has `verification_status` of `verified` or `unverified`. A record marked `verified`
  without a source is downgraded to `unknown`.
- **Research confidence is server-computed**: `high` requires a cited official source that
  explicitly links the road and contractor. Tender aggregators can support a `medium` related
  work record but never a verified contractor; general websites are not sufficient evidence.
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
| `MAPTILER_API_KEY` | empty | Server-side reverse-geocoding key; never exposed to the browser |
| `MAPTILER_GEOCODING_URL` | MapTiler geocoding API | Reverse-geocoding base URL |
| `MAPTILER_REFERER` | empty | Allowed site origin for an origin-restricted key |
| `REVERSE_GEOCODING_ENABLED` | `true` | Disable provider calls without removing cached data |
| `REVERSE_GEOCODING_ASYNC` | `true` | Enrich new potholes in a background thread |
| `REVERSE_GEOCODING_MAX_ATTEMPTS` | `6` | Stop retrying after this many failed attempts |
| `REVERSE_GEOCODING_NO_RESULT_RETRY_SECONDS` | `604800` | Retry interval when the provider returns no match |
| `PUBLIC_DEFAULT_LIMIT` / `PUBLIC_MAX_LIMIT` | `500` / `2000` | Public read caps |
| `RESEARCH_ENABLED` | `true` | Enable the research API/worker |
| `RESEARCH_ADMIN_KEY` | empty | Bearer key for internal research routes; unset disables them |
| `SEARCH_ENGINE_URL` | `http://searxng:8080` | Private SearXNG base URL (`SEARXNG_URL` remains a compatibility alias) |
| `SEARXNG_ENGINES` | `yep` | Comma-separated SearXNG engines used by the provider |
| `OLLAMA_URL` | `http://ollama:11434` | Private Ollama base URL |
| `RESEARCH_MODEL` | `qwen3:0.6b` | Local extraction model |
| `RESEARCH_MAX_QUERIES` | `12` | Dynamic queries per target |
| `RESEARCH_MAX_FETCHES` | `5` | Maximum pages fetched per run |
| `RESEARCH_MAX_DURATION_SECONDS` | `180` | Per-run wall-clock budget |
| `RESEARCH_CACHE_DAYS` | `30` | Reuse a completed result within this window |
| `RESEARCH_FAILED_RETRY_SECONDS` | `3600` | Retry delay after a failed run |
| `RESEARCH_REFRESH_COOLDOWN_SECONDS` | `600` | Minimum interval between manual refreshes of a completed run |

### Frontend

See `frontend/.env.example`. The API variables are:

| Variable | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | Complete browser-facing API base, including `/api/v1`; default `/api/v1` |
| `VITE_API_PROXY_TARGET` | Flask or deployed HTTPS root used by the Vite development proxy, without `/api`; default `http://127.0.0.1:5001` |
| `API_ORIGIN` | Compose nginx upstream root, without `/api`; default `http://backend:5000`. Set to the deployed HTTPS root for local fleet data |

Map variables select the vector basemap:

| Variable | Purpose |
| --- | --- |
| `VITE_MAP_PROVIDER` | Optional override: `maptiler` or `stadia`; otherwise MapTiler is chosen when its key exists, else Stadia |
| `VITE_MAPTILER_API_KEY` | MapTiler browser key; preferred when present |
| `VITE_MAPTILER_STYLE_URL` | MapTiler style JSON; defaults to `streets-v2-light` |
| `VITE_STADIA_API_KEY` | Stadia Maps browser key; Stadia is keyless for localhost development only |
| `VITE_STADIA_STYLE_URL` | Stadia style JSON; defaults to `alidade_smooth` |

Other values control the initial map view. Keep provider attribution visible. The Compose
frontend build accepts `VITE_API_BASE_URL` and the map variables from the root `.env`; it uses
the same-origin `/api/v1` path by default, proxied by nginx. The nginx container reads
`API_ORIGIN` at startup. If no provider key is available or the style cannot load,
the map falls back to a plain background and keeps the canonical pothole layers visible.

## Production notes

- Terminate TLS at a reverse proxy or load balancer; the bundled nginx speaks HTTP internally.
- Add rate limiting and caching at the edge for `/api/v1/geocode`, reverse-geocoding provider
  calls, and public reads.
- Keep the ingest key and `MAPTILER_API_KEY` in a secret manager and rotate them.
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
- PIN geocoding depends on the external Nominatim service; failures are surfaced in the UI.
- Reverse geocoding depends on MapTiler availability and quota. Existing coordinates are never
  rewritten, and missing provider fields remain “Not recorded”.
- An origin-restricted MapTiler key needs `MAPTILER_REFERER`; a server key without origin
  restrictions is preferred.
- Automated research is best-effort and depends on public search coverage. Tender aggregators
  may be the only accessible source for some works; those results remain `medium` until a
  government/official source is verified. Official portals that require CAPTCHA are not
  bypassed. The local model can still return invalid JSON on weak source context, which is
  surfaced as a failed run rather than guessed data. Search/fetch/Ollama failures show
  “Road research temporarily unavailable.”; an empty search shows “No source-backed road work
  record found.”; a matched record without a contractor says “Not recorded in the cited
  source.”
- Android ingestion uses an offline WorkManager queue and has been exercised end to end on a
  physical device, including idempotent replay of an already-synced report. Observations
  without a GPS fix stay local and are marked failed.
- Local and deployed databases are separate. Align `VITE_API_PROXY_TARGET` and `API_ORIGIN` with
  the intended backend; otherwise the local site can look empty while the deployed site has data.
- Purging local Android observations clears Room and evidence only. There is no public delete
  endpoint, so local purge does not remove canonical server records.
- The Tailscale address is deployment-specific; update the Android build property,
  `VITE_API_PROXY_TARGET`/`API_ORIGIN` for local development, and `CORS_ORIGINS` if the home
  server's Tailscale IP changes. The browser bundle itself uses the same-origin `/api/v1` path.
