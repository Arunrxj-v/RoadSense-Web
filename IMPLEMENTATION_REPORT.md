# Phase 2 implementation and verification report

## Scope delivered

The public RoadSense Vision web application is implemented in
`RoadSense_WEB/`, with a React frontend and a Flask/PostGIS backing service.
The repository previously contained only the Android application and design
references, so the backend and frontend were both built in this phase.

### Public experience

- Map-first landing page with canonical pothole markers, clustering, a single
  recent-feed load, time filters, deep-linkable map state, selected-pothole preview card,
  and shareable pothole links.
- Indian PIN code search, resolved server-side, with loading/error feedback.
- Detections ledger with time filters, server-side text search (including cached
  reverse-geocoded road, locality, district, state, and PIN), pagination,
  responsive card layout, and explicit empty/error states.
- Pothole detail page with canonical record metadata, cached reverse-geocoded
  address/road data, micro-location inset, provenance-aware contract record,
  verification labels, source link, and background research status.
- Research result panel that distinguishes a verified contractor (`high`) from a
  possible related work/tender record (`medium`, including records without a
  contractor) and an unverified/no-record result.
- About and Public Data Note pages, plus a branded 404 page.
- Responsive layouts checked at 1440 px, 834 px, and 390 px widths.
- No internal stack names, credentials, camera media, or raw sensor data are
  exposed in the public UI.

### Data service

- `POST /api/v1/internal/reports` for authenticated fleet ingestion, with idempotent
  `report_id` handling and spatial/temporal deduplication into canonical potholes.
- Read-only public endpoints for health, metadata, bbox queries, ledger search,
  nearby queries, detail, roads, and PIN geocoding.
- Cached MapTiler reverse geocoding for canonical potholes in a separate
  `pothole_location_metadata` table, with pending/resolved/failed/skipped
  lifecycle, background enrichment, retry backoff, and an idempotent
  `enrich-locations` CLI. Public reads never call the provider.
- PostGIS geometry/geography columns, GiST indexes, and sync triggers for
  production; SQLite fallback for development and tests.
- Self-hosted public-record research pipeline: dynamic road/locality/PIN/
  municipality/authority queries, state-aware official domains, private SearXNG
  search, SSRF-safe HTML/PDF fetching, strict JSON extraction with local Ollama
  (`qwen3:0.6b`), deterministic validation, source ranking, generic road-name
  matching with location context, caching, and a DB-backed async worker.
- No production hardcoded road, tender, contractor, or pothole-specific values.
  Road base-name aliases are derived generically and only accepted with a road
  term plus locality/district/PIN/municipality context.
- Research provenance in `pothole_research_runs` and
  `pothole_research_sources`, separate from canonical potholes; sources store
  `retrieved_at`, and public reads expose only the latest stored run.
- Public serializers deliberately omit internal identifiers and raw reports.
- Contractor names are only emitted for source-backed `verified` or `unverified`
  records; a `verified` record without provenance is downgraded to `unknown`.

### Deployment

- Multi-stage frontend image served by nginx with SPA fallback, immutable asset
  caching, security headers, and `/api/` reverse proxy.
- Gunicorn backend image with one-time entrypoint schema initialisation.
- Docker Compose stack with PostGIS, backend, frontend, private SearXNG,
  private Ollama plus a one-time model pull, and a research worker. The Flask API
  is published on the home server at a configurable
  `API_BIND_ADDRESS:API_PORT` (default `0.0.0.0:5001`); PostgreSQL, SearXNG, and
  Ollama remain internal to the Compose network.
- The browser-facing API base is centralized in `frontend/src/lib/api.ts` and
  uses the same-origin `/api/v1` path. Vite proxies `/api` to Flask during
  development, and the bundled nginx proxies `/api/` in production.
- CORS is environment-driven and defaults to the local and Tailscale website
  origins used by this deployment.
- Environment examples for local and Compose deployments.
- README covering local setup, API, ingestion, data rules, configuration, and
  production notes.

## Verification performed

| Check | Result |
| --- | --- |
| Backend test suite (`pytest -q`) | 41 passed |
| Frontend unit tests (`npm test`) | 14 passed |
| Frontend typecheck (`npm run typecheck`) | passed |
| Frontend lint (`npm run lint`) | passed |
| Frontend production build (`npm run build`) | passed |
| Reverse geocoding tests | MapTiler parser, cache/idempotency, no-result retry, pending/resolved API payloads passed |
| PostGIS smoke test | bbox, nearby, detail, road, ingestion, geometry triggers, and GiST indexes passed |
| Docker Compose build | db, backend, and frontend built and became healthy |
| Full-stack smoke via nginx | health, meta, recent potholes, bbox, ingestion, and SPA fallback passed |
| Home-server deployment | deployed at `http://100.104.179.69:8091`; db, backend, and frontend healthy; API and site reachable from a Tailscale client |
| Deployed ingestion and persistence | two nearby reports created one canonical pothole with `report_count = 2`; duplicate `report_id` was idempotent; record survived a backend restart |
| Deployed access control | missing or invalid ingest token returned 401; out-of-range coordinates returned 400 |
| Deployed browser validation | map marker and preview card showed 2 reports; detail page and detections ledger showed the same canonical record; no console/page errors |
| CORS environment config | allowed origin echoed; unlisted origin received no allow-origin header |
| Android debug build | passed with JDK 17 and SDK Platform 35/Build Tools 35; APK version `2.0.0-phase2` (`versionCode 2`) |
| Android unit tests | 56 passed, 0 failed, including ingestion payload, ONNX contract, detection tracker, duplicate policy, and geometry tests |
| Physical-device ingestion | CPH2689 running the debug APK captured and confirmed detections on-device, persisted them in Room, and uploaded metadata to the deployed API |
| Offline queue and retry | a geotagged observation recorded while Tailscale was disconnected was uploaded after connectivity returned; server row was created at `2026-10-21T20:41:33Z` for an observation captured at `20:40:18Z` |
| Deployed end-to-end result | one observation became canonical pothole `PH-000001`; map marker/preview, detail page, and detections ledger all showed it with matching coordinates and confidence |
| Android cleanup | local Room/evidence data purged through the app; deployed `PH-000001` removed and PostgreSQL sequences reset |
| Vector map migration | MapLibre GL JS with Stadia keyless localhost basemap; cluster expansion, point selection, PIN fly-to, detail inset, and mobile layout checked; no console/page errors |
| Production vector map | Vite build emitted the MapLibre worker asset; preview at `127.0.0.1:5174` loaded the basemap, canonical feed (2 records), cluster expansion, selected preview card, and detail inset with no console/page errors |
| Responsive review | desktop, tablet, and mobile screenshots inspected |
| Research pipeline tests | dynamic query generation for multiple roads, generic aliases, same-road/different-district rejection, authority validation, source ranking, aggregator handling, strict validation, no-contractor work records, provenance, refresh cooldown, and failure messages passed |
| Backend suite | `47 passed` after the dynamic-research and config changes |
| Frontend suite | `14 passed`; typecheck, lint, and production build passed |
| Deployed research services | SearXNG, Ollama, model pull, backend, and research worker healthy; `qwen3:0.6b` loaded |
| Deployed research result | `PH-000003` completed at `medium` from TenderShark with tender `2026_PWD_838718_1`, work reference `PWD/RB/TR/12265/2025_5_2_1/1`, authority PWD, and no contractor |
| Async research worker | forced admin enqueue created run 5, worker claimed it, and it completed at `medium` with 10 queries, 3 fetched sources, and 3 selected sources; the redeployed worker also completed dynamic runs with 11–12 queries |
| Public research refresh | detail page exposes “Research again”; `PH-000003` returned `429` with `Retry-After`, a failed run was retried with `202`, and the UI showed both the cooldown error and the pending state |
| Multi-coordinate live research | `PH-000003` (Engineering College Road, Chengannur) completed `medium` with 12 queries, 4 fetched sources, 2 selected, PWD/tender provenance, and no contractor; `PH-000001` (Kannakulangara-Nettiyadu Road, Kollam) and `PH-000004` (Wayanad Road, Kozhikode) completed with no verified record; `PH-000005` (Lane E, Thiruvananthapuram) returned “No source-backed road work record found.” |
| Failure-state live research | with SearXNG stopped, `PH-000007` failed with “Road research temporarily unavailable.”; after restart, the public retry returned `202`; an unresolved-road pothole returned `409`; the UI rendered both unavailable and no-record states |
| Live provenance | run 11 stored `retrieved_at` on every successfully fetched source and exposed 12 generated queries, 4 fetches, and 2 selected sources |
| UI/browser verification | desktop and mobile detail pages rendered the “Research again” action, cooldown error, pending state, failed state, no-record state, and medium/no-contractor result; map, detections, and detail APIs all returned `200` with no console/page errors |
| Public research API | `GET /api/v1/potholes/PH-000003` returned `completed`/`medium` with `contractor: null` and the cited source URL |

The local browser checks used a test database. Temporary multi-coordinate records used for
the live dynamic-research checks were deleted afterward; the current feed again contains the
three canonical fleet potholes (`PH-000001`–`PH-000003`).
The physical-device check also surfaced a model-quality limitation: while the
camera viewed a stationary desk scene, the detector confirmed 14 observations at
the configured `0.25` confidence threshold. This confirms the capture-to-upload
path but shows that field false-positive tuning is still required.

## Key decisions

- **Canonical-only map**: raw detection reports are never map features. This
  prevents a single physical pothole from appearing multiple times.
- **Server-side geocoding**: avoids exposing third-party API keys in the browser
  and keeps provider attribution and request limits under server control. PIN
  lookup uses Nominatim; reverse geocoding uses MapTiler with the canonical
  coordinate as the sole input.
- **Cached reverse geocoding**: provider results and lifecycle state are stored in
  `pothole_location_metadata`, so map/detail reads stay fast and do not depend on
  provider uptime. Missing route number, classification, or authority stays
  unset rather than being inferred.
- **Provenance over inference**: absent road/contract data is shown as absent
  rather than guessed from proximity.
- **PostGIS-first with SQLite fallback**: production gets real spatial indexing;
  local development and CI do not need a GIS server.
- **Vector basemap with graceful fallback**: MapLibre GL JS uses MapTiler when a key is
  present and Stadia otherwise. Stadia is keyless for localhost development only;
  deployed builds need a provider key. If no style can load, the pothole layers remain
  visible over a plain background instead of blanking the map.
- **Explicit MapLibre worker asset**: `main.tsx` imports
  `maplibre-gl/dist/maplibre-gl-worker.mjs?url` and calls `setWorkerUrl()` before rendering.
  This makes Vite emit the worker and prevents a production-only failure where the basemap
  renders but GeoJSON clustering cannot start.
- **One-time schema initialisation**: gunicorn workers do not race to create
  tables; Compose initialises once in the entrypoint, and production can run
  `init-db` as a separate deploy step.
- **Local model, deterministic guardrails**: Ollama extracts facts from fetched
  text only; it never searches the web. The backend generates queries, enforces
  fetch/SSRF/size/time limits, validates the cited source and road match, and
  computes confidence. A `high` result requires an explicit official-source
  contractor link; tender aggregators can only support `medium`.
- **No CAPTCHA bypass**: when an official portal requires CAPTCHA, the pipeline
  records the accessible related source as `medium` and tells the reader to
  verify the official record. It does not attempt to circumvent the control.
- **DB-backed async research**: a small worker claims pending runs and recovers
  stale `running` jobs without adding Redis/Celery to the resource-constrained
  home server.

## Environment notes

- Local verification used Python 3.9.6, Node 26, SQLite, and the supplied venv.
- The configured Tailscale home-server address is `100.104.179.69`; update the
  Android build property, `VITE_API_PROXY_TARGET`/`API_ORIGIN` for local
  development, and `CORS_ORIGINS` if it changes.
- Local development and the deployed site use separate databases by default.
  `VITE_API_PROXY_TARGET` and the Compose `API_ORIGIN` must point at the intended
  backend; point both at the deployed HTTPS root to read fleet data locally.
  The default `API_ORIGIN=http://backend:5000` keeps standalone Compose isolated.
- The local nginx upstream needs `proxy_ssl_server_name on` when `API_ORIGIN`
  uses HTTPS, otherwise the TLS handshake fails without SNI.
- The PostGIS path was verified against `postgis/postgis:16-3.4` under Docker.
- The deployed stack runs from `~/roadsense` on the home server under Compose
  project `roadsense`, using Docker 29.8.0 and Compose 5.5.1. PostgreSQL is not
  published to the host; the API and web UI bind only to the Tailscale address.
- Automated browser verification used a temporary Playwright install outside the
  project; Playwright is not a project dependency.
- Research runs on the same Compose network as the backend. SearXNG uses the
  `yep` engine by default; DuckDuckGo returned CAPTCHA pages, Bing returned
  generic results, and the official eTenders archive required CAPTCHA. The
  deployed stack therefore does not claim official primary-source verification
  for `PH-000003`.
- The home server has 4 CPU cores and about 3.3 GiB RAM. Ollama is limited to one
  loaded model, one parallel request, and a 5-minute keep-alive; a research run
  takes roughly 50–90 seconds.

## Known limitations and next steps

- The Android capture, Room persistence, WorkManager queue, deployed upload, and
  web display path have been exercised on a physical device. Field accuracy still
  needs work: the detector produced false positives on a stationary desk scene at
  the current `0.25` confidence threshold. Only detections with a recent GPS fix
  can upload; observations captured before the first fix correctly remain local
  and are marked failed.
- SQLite fallback is development-only; production should use PostGIS.
- Repair status is stored data, not inferred or automatically refreshed.
- Geocoding depends on external providers: Nominatim for PIN lookup and MapTiler
  for reverse geocoding. Nominatim returned HTTP 403 from the verification
  network; MapTiler succeeded with an origin-appropriate `Referer`. Configure
  `MAPTILER_API_KEY` and, for an origin-restricted key, `MAPTILER_REFERER`.
  Provider failures are cached as failed with retry backoff instead of blocking
  public reads.
- Edge rate limiting and caching for public reads and provider calls are
  recommended before high-traffic deployment.
- Research coverage depends on public search results. Some works are only
  discoverable through tender aggregators, which remain `medium` until a
  government/official record is verified. The small local model can return
  invalid JSON on weak source context; that is stored as a failed run rather
  than guessed data.
- A production deployment should replace the example secrets, restrict CORS,
  enable HTTPS, and back up the PostGIS volume.
- Deployed vector basemap verification requires a MapTiler or Stadia key for the
  non-local origin. The keyless Stadia style works only on localhost; without a
  deployed key the canonical pothole layers still render over the fallback background.
- The map bundle is a single ~1.34 MB minified chunk (~376 KB gzip) because of
  MapLibre GL; route-level code splitting is not yet implemented.
