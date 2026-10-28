# Local backend API contract

Base URL: `http://127.0.0.1:8000`. JSON requests/responses, no authentication.
`/docs` (Swagger), `/redoc`, and `/openapi.json` describe the running application's
schemas. Both execution routes exist only when `PATCHPILOT_ENVIRONMENT=development`;
otherwise they return 404. This is a local curated-fixture API, not a public service.

## Endpoints

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| GET | `/health` | None | `HealthResponse` |
| GET | `/api/v1/fixtures` | None | `FixtureList` (read-only metadata) |
| POST | `/api/v1/reproductions` | `ReproductionRequest` | `Evidence` |
| POST | `/api/v1/debug-runs` | `DebugRequest` | `DebugReport` |

Health returns `{"service":"patchpilot-api","status":"ok","version":"0.1.0"}`.
The service name is configurable. This is process liveness, not Docker readiness.

## Read-only fixture discovery

`GET /api/v1/fixtures` returns `FixtureList`: `{"fixtures": [FixtureInfo, ...]}`.
It is available in every environment; execution routes remain development-only.
No directory scan, Docker operation or provider call occurs. The list is metadata,
not a claim that Docker is ready or that a fixture has been verified.

| FixtureInfo field | JSON type / meaning |
| --- | --- |
| `fixture_id` | One of the four approved IDs below |
| `name`, `description` | string; display name and intended behavior |
| `category` | string; currently edge_case, business_logic, input_validation or data_parsing |
| `example_bug_description` | string; editable form example, not execution evidence |
| `language`, `test_framework` | string; currently python and pytest |
| `expected_failed`, `expected_passed` | integer; intended baseline counts, not observations |

The selector must use discovered IDs and disable submission if discovery fails.
No host paths, credentials or client-editable execution configuration are exposed.

Reproduction request:

```json
{"fixture_id":"checkout-empty-cart"}
```

Debug request:

```json
{"fixture_id":"checkout-empty-cart","bug_description":"An empty cart should total zero."}
```

`fixture_id` accepts only `checkout-empty-cart`, `shipping-threshold`,
`quantity-bool` or `csv-quoted-fields`, from the explicit registry. The examples
above remain valid. `bug_description` is required and
1–2,000 characters. Both request models reject extra fields. Commands, model
names, repository URLs, paths and patches cannot be supplied by the frontend.

## Evidence schema

| Field | JSON type / values |
| --- | --- |
| `fixture_id`, `image_reference` | string |
| `test_command` | string array; exact allowlisted command |
| `container_image_id` | string or null; immutable image ID when resolved |
| `started_at` | string; UTC ISO timestamp |
| `duration_seconds` | number; total runner duration including setup/cleanup |
| `exit_code` | integer or null if no completed test process |
| `stdout`, `stderr` | string; actual captured output |
| `timed_out` | boolean; test execution timeout, not infrastructure check timeout |
| `status` | `tests_passed`, `tests_failed`, `timeout`, `infrastructure_failure` |
| `stdout_truncated`, `stderr_truncated` | boolean; each stream retains at most 64 KiB |
| `error` | string or null; safe infrastructure error |

The original fixture intentionally returns `tests_failed`, exit 1, with one failed
and three passed tests. HTTP 200 means evidence was obtained, not that tests passed.

## DebugReport schema

| Field | JSON type / meaning |
| --- | --- |
| `fixture_id`, `provider` | string; current live provider is `groq` |
| `status` | See status table below |
| `verified` | boolean; computed from real sandbox results, never model claims |
| `candidate` | `Candidate` or null |
| `model_unified_diff` | string or null; original model diff before canonicalization |
| `baseline`, `failing_test`, `regression` | `Evidence` or null when a stage did not run |
| `source_sha256` | object mapping source path strings to SHA256 strings |
| `patch_attempts` | integer; zero or one per run |
| `error` | string or null |

`Candidate` has `hypothesis` (1–2,000 characters), `unified_diff` (1–16,000
characters, also subject to the patcher's byte limit), and `references` (1–8).
Each reference has `path` (1–120 characters, restricted during validation to the selected fixture's source/test files),
`line` (1-based integer, 1–1,000), and `quote` (1–500 characters). Paths/quotes are
validated against actual source. Candidate/reference models forbid extra fields.

The applied diff may change only the selected fixture's registered source file in a disposable copy.
Verification requires the expected failing baseline, a passing original failing
test and the fixture's full expected passing count, complete evidence and the same image ID.
Stage evidence is authoritative; display errors/timeouts separately from failed tests.

| Debug status | HTTP | Meaning |
| --- | --- | --- |
| `verified` | 200 | Both required sandbox checks passed |
| `verification_failed` | 200 | Candidate checks did not verify the patch; inspect stage evidence |
| `baseline_unexpected` | 200 | Expected original bug was not observed; no proposal |
| `patch_rejected` | 422 | Model candidate/reference/diff rejected |
| `provider_error` | 502 | Missing key, provider/transport error or invalid model output |
| `blocked_execution` | 503 | Baseline/container/workspace preparation or cleanup unavailable |

Reproduction uses HTTP 200 for `tests_passed`, `tests_failed` and `timeout`;
infrastructure failures use HTTP 503 with an `Evidence` body.

## Shared errors and browser handling

Invalid requests use HTTP 422 with this **different** shape:

```json
{"error":{"code":"validation_error","message":"Request validation failed"}}
```

HTTP 429 uses the same envelope with `code=reproduction_busy`: one reproduction
or debug run is already active in this API process. Missing routes use 404 with
`code=http_error`; unexpected failures use 500 with `code=internal_error` and a
generic message. OpenAPI documents the union of `DebugReport` and `ErrorResponse`
for debug HTTP 422. Do not assume all non-2xx responses have the same body.

## Local Next.js integration

CORS defaults to exactly `http://localhost:3000` and `http://127.0.0.1:3000`,
allowing GET/POST and the Content-Type header. Credentialed requests are disabled;
wildcards and origin paths are rejected. To change ports, set a JSON array in
the API environment, e.g. `PATCHPILOT_CORS_ORIGINS=["http://localhost:3001"]`.
Set `[]` to disable cross-origin access. Restart the API after configuration changes.
CORS governs browsers; it is not authentication or authorization.

Use one small typed fetch client against this base URL. Derive TypeScript types
from `/openapi.json` in the frontend milestone. Always parse JSON before deciding
how to present `response.ok`, and distinguish `typeof body.error === "object"`
(shared envelope) from a report's string/null `error`. Handle network failures
separately, including server failures without a readable browser response.

Requests are synchronous: show an indeterminate busy state and disable duplicate
submissions. There are no job IDs, polling, streaming, saved history or cancellation
endpoints. Aborting fetch does not cancel server-side execution. A debug run may
take several test/control timeouts plus a 30-second model request; allow roughly
three minutes at the client/proxy for local use. Show the returned stage evidence
after completion; never fabricate intermediate progress or verification.

Keep Groq credentials on the backend. The frontend needs only a public API base
URL, such as `NEXT_PUBLIC_API_BASE_URL`; never use a NEXT_PUBLIC variable for a key.
