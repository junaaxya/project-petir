# Public access security plan — Petir 2

Target hostname: `nelayan-sungailiat.petirlabs.com`.

This document is a plan only. Applying Cloudflare, DNS, Access policies, or production environment changes requires a separate approval.

## Non-negotiable boundaries

- Browser authentication must never replace node authentication.
- `POST /api/ingest/sync-batch`, `GET /api/siren/commands/pending`, and `POST /api/siren/audit-test/status` remain protected by the per-node bearer token and node/envelope identity checks.
- Admin authorization must be enforced by the backend or an identity-aware proxy in front of the backend. Hiding a page or navigation link is not authorization.
- Siren, relay, and GPIO activation remain disabled. Petir 2 must retain an empty operator allowlist and no registered production node until a separately reviewed hardware rollout.
- API keys, node tokens, and Access service tokens must never be embedded in browser JavaScript or `NEXT_PUBLIC_*` variables.

## Phase 2.6 backend boundaries

| Surface | Current backend guard | Public classification |
|---|---|---|
| Weather, lightning, health, forecast reads | Petir 1-compatible `verify_dashboard_user` | Candidate public monitoring data |
| System events and summary | `verify_operator_user` | Operator-only; events may reveal internal details |
| `GET /api/ingest/runs` | `verify_operator_user` | Operator-only; includes error details and node activity |
| `POST /api/ingest/sync-batch` | `verify_node_token` | Machine endpoint; bypass browser Access and retain node token |
| Siren options/latest/history/create | feature flag plus `verify_admin_user` | Admin-only; disabled in Petir 2 Compose |
| Siren pending/status callbacks | feature flag plus `verify_node_token`, omitted from OpenAPI | Machine endpoint; disabled in Petir 2 Compose |
| `/api/admin/*` | `verify_admin_user` | Admin-only, including retention and job mutations |
| Backend `/openapi.json`, `/docs`, `/redoc` | controlled by `API_DOCS_ENABLED` | Disabled in Petir 2 Compose; `/healthz` is the internal healthcheck |

There is no separate node-management HTTP route in the current application. Node registration is database/bootstrap work and must remain an explicit operator procedure.

## Resolved source-level risks

`DASHBOARD_AUTH_ENABLED=false` still preserves Petir 1-compatible public telemetry,
but it no longer controls privileged routes. `ADMIN_AUTH_MODE=disabled` fails closed
with `503` for operator/admin APIs. The supported privileged modes are server-only
API keys and backend-verified Cloudflare Access JWTs.

The backend no longer trusts client-supplied `requestedBy`; persisted siren audit
identity and role are derived from the verified principal. `SIREN_AUDIT_ENABLED=false`
returns `404` from browser creation/history and machine poll/callback routes before
any command can be read or created.

The generic Compose file retains an explicit `legacy_dashboard` access mode solely
to preserve Petir 1 behavior during future upgrades. That mode may inherit anonymous
privileged access when legacy dashboard auth is disabled and therefore must never be
used for Petir 2 or a new public deployment. Generic Compose still defaults siren
routes off and the operator list empty. The dedicated `deploy/petir2-nelayan`
template remains the only reviewed deployment path for this station.

No edge polling/relay execution implementation was found, so there is no current
physical actuation path. Preserve that state and keep the backend siren feature
flag disabled throughout Phase 3.

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

Remaining policy work for Approach A:

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

Use **Approach B for the first Phase 3 pilot**, because Petir 2 is an
internal/customer pilot. Phase 2.6 now separates public-reader, operator, and admin
backend surfaces, but the first public route should still minimize anonymous exposure.

Completed in source:

1. Backend operator/admin authorization with API-key and verified Cloudflare Access
   JWT modes.
2. Negative tests for missing, invalid, wrong-role, and expired credentials.
3. A fail-closed siren feature flag covering browser and node-token routes.
4. Production controls for OpenAPI, Swagger, and ReDoc, plus a separate `/healthz`.
5. Server-derived siren audit identity; client `requestedBy` is ignored.

Remaining operational blockers before public routing:

1. Put the browser dashboard behind Cloudflare Access.
2. Add exact machine-path policies for node-token endpoints; do not broadly bypass `/api/*`.
3. Configure `PETIR2_ADMIN_AUTH_MODE=cloudflare_access`, the exact Access audience,
   team domain, and reviewed admin/operator email allowlists in the mode-0600 runtime
   environment. Keep the mode `disabled` until those values are approved.
4. Verify the Access JWT reaches the backend through the final Next.js proxy path;
   reject a forged header and a valid but non-allowlisted identity.
5. Keep `PETIR2_SIREN_AUDIT_OPERATORS_JSON=[]`, no production node registration,
   and no siren/relay worker activation.
6. Test allowed node-token requests and rejected unauthenticated/admin requests through
   the final public hostname before connecting a Raspberry Pi.

Approach A can follow later after an explicit public-data contract, event-disclosure
review, and separate public-read rate/cache policy are implemented and approved.

## Phase 4B.3 pre-auth protection

The application now applies a bounded, process-local invalid-bearer limiter before
performing an `edge_nodes` token lookup. Its state is protected by a lock, capped by
`INVALID_BEARER_MAX_CLIENTS`, stores only a client identity (never a bearer token),
and returns HTTP `429 BACKPRESSURE` when the threshold is exceeded. A successful
node authentication clears only that client's failed-attempt state.

`CF-Connecting-IP` and `X-Forwarded-For` are ignored unless the immediate TCP peer
belongs to `TRUSTED_PROXY_CIDRS`. For Petir 2, configure that value to the exact
Docker subnet/CIDR containing the reviewed Next.js reverse proxy. Do not put arbitrary
client, campus, Tailscale, or broad Internet CIDRs in this setting. The reverse proxy
must replace—not append untrusted client values to—`CF-Connecting-IP`. With an empty
setting, the backend conservatively keys on the direct peer; this is safe against
header spoofing but is not the desired production identity boundary behind a shared
proxy.

Recommended Petir 2 application values:

```dotenv
INVALID_BEARER_MAX_FAILURES=10
INVALID_BEARER_WINDOW_SECONDS=60
INVALID_BEARER_BLOCK_SECONDS=300
INVALID_BEARER_MAX_CLIENTS=10000
TRUSTED_PROXY_CIDRS=<exact internal reverse-proxy subnet or address>
```

These controls are per application process and are defense in depth, not a distributed
rate limiter. If the backend is scaled to multiple workers/replicas, keep the Cloudflare
rule below and move shared limiter state to an approved bounded store before relying on
one global application threshold.

## Exact Cloudflare rate-limit recommendation (do not apply in this change)

Create one rate-limiting rule scoped only to the Petir 2 machine-ingest endpoint:

```text
Rule name: petir2-ingest-invalid-abuse-guard
Expression:
(http.host eq "nelayan-sungailiat.petirlabs.com" and
 http.request.method eq "POST" and
 http.request.uri.path eq "/api/ingest/sync-batch")
Counting characteristic: ip.src
Threshold: 60 requests
Period: 60 seconds
Action: Block
Mitigation timeout: 600 seconds
Response: Cloudflare default 429 response
```

Rationale: a normal first sync currently sends at most six logical batches before
retries, so 60 requests/minute leaves substantial retry margin while bounding repeated
invalid-bearer traffic. Do not use Managed Challenge for this machine endpoint, do not
scope the rule to the entire hostname or `/api/*`, and do not create an interactive
Access redirect on this path. Cloudflare cannot know whether a bearer is valid, so the
rule counts all matching POSTs; application authentication remains authoritative.
Before any separate production activation, confirm the observed legitimate retry rate
and raise the threshold only with evidence. This document does not change Cloudflare.
