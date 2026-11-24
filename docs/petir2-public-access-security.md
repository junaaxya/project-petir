# Public access security plan — Petir 2

Target hostname: `nelayan-sungailiat.petirlabs.com`.

This document is a plan only. Applying Cloudflare, DNS, Access policies, or production environment changes requires a separate approval.

## Non-negotiable boundaries

- Browser authentication must never replace node authentication.
- `POST /api/ingest/sync-batch`, `GET /api/siren/commands/pending`, and `POST /api/siren/audit-test/status` remain protected by the per-node bearer token and node/envelope identity checks.
- Admin authorization must be enforced by the backend or an identity-aware proxy in front of the backend. Hiding a page or navigation link is not authorization.
- Siren, relay, and GPIO activation remain disabled. Petir 2 must retain an empty operator allowlist and no registered production node until a separately reviewed hardware rollout.
- API keys, node tokens, and Access service tokens must never be embedded in browser JavaScript or `NEXT_PUBLIC_*` variables.

## Current backend boundaries

| Surface | Current backend guard | Public classification |
|---|---|---|
| Weather, lightning, health, forecast reads | `verify_dashboard_user` | Candidate public monitoring data |
| System events and summary | `verify_dashboard_user` | Operator-only; events may reveal internal details |
| `GET /api/ingest/runs` | `verify_dashboard_user` | Operator-only; includes error details and node activity |
| `POST /api/ingest/sync-batch` | `verify_node_token` | Machine endpoint; bypass browser Access and retain node token |
| Siren options/latest/history/create | `verify_dashboard_user` | Admin-only; create is a physical-action request path |
| Siren pending/status callbacks | `verify_node_token`, omitted from OpenAPI | Machine endpoint; no browser authentication |
| `/api/admin/retention/run` | `verify_dashboard_user` | Critical admin-only; can delete retained data |
| `/api/admin/availability/run` and `/api/admin/ai/run` | `verify_dashboard_user` | Admin/operator-only mutation |
| `/api/admin/*` reads | `verify_dashboard_user` | Operator-only |
| Backend `/openapi.json`, `/docs`, `/redoc` | FastAPI defaults; unguarded on the internal-only backend | Not currently proxied by web (`/api/openapi.json` returns 404); disable or protect before any direct API publication |

There is no separate node-management HTTP route in the current application. Node registration is database/bootstrap work and must remain an explicit operator procedure.

## Approach A — public monitoring, protected admin/API

Public:

- dashboard pages;
- narrowly selected read-only weather, lightning, health, quality, and forecast endpoints.

Protected:

- `/admin/*` UI;
- `/api/admin/*`;
- `/api/siren/audit-test*` browser/admin routes;
- `/api/ingest/runs`;
- `/api/system/events` and detailed operational events;
- `/openapi.json`, `/docs`, and `/redoc`.

Machine exceptions:

- `/api/ingest/sync-batch` uses node bearer tokens;
- `/api/siren/commands/pending` and `/api/siren/audit-test/status` use node bearer tokens;
- Cloudflare policies must not redirect these machine requests to an interactive login page.

Advantages:

- public monitoring remains easy to access;
- ingest can operate independently of browser sessions;
- public product visibility is preserved.

Risks and required source work:

- the current `verify_dashboard_user` switch is all-or-nothing, so public and operator read APIs need explicit backend policy groups;
- admin identity needs a backend-verifiable mechanism (for example validated Cloudflare Access JWT headers), not a frontend-only check;
- event payloads need a disclosure review before any public exposure;
- rate limits and cache policy should be set separately for public reads and machine writes.

## Approach B — Cloudflare Access for the whole dashboard

Protect the hostname and browser/API reads with Cloudflare Access, while defining explicit machine-path policies for node-token endpoints.

Advantages:

- smallest application change for a private pilot;
- strong default-deny posture;
- lower risk of accidentally publishing operational event details.

Risks:

- a blanket Access policy can break Raspberry Pi ingest by returning login HTML or a redirect;
- path exceptions must be exact and tested with real non-browser requests;
- Cloudflare Access alone does not replace backend authorization for physical-action or destructive admin endpoints. Those endpoints still need an application-side admin guard.

## Recommendation

Use **Approach B for the first Phase 3 pilot**, because Petir 2 is an internal/customer pilot and the current backend does not yet have separate public-reader and operator roles.

Before public routing:

1. Put the browser dashboard behind Cloudflare Access.
2. Add exact machine-path policies for node-token endpoints; do not broadly bypass `/api/*`.
3. Add backend admin authorization for `/api/admin/*` and `/api/siren/audit-test*`; validate the trusted Access identity/JWT server-side or use another reviewed admin identity mechanism.
4. Disable or protect OpenAPI, Swagger, and ReDoc in the production environment.
5. Keep `PETIR2_SIREN_AUDIT_OPERATORS_JSON=[]`, no production node registration, and no siren/relay worker activation.
6. Test allowed node-token requests and rejected unauthenticated/admin requests through the final public hostname before connecting a Raspberry Pi.

Approach A can follow later after an explicit public-data contract and backend role split are implemented and reviewed.
