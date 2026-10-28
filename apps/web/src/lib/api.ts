import type { components } from "./api-schema";

export type Evidence = components["schemas"]["Evidence"];
export type DebugReport = components["schemas"]["DebugReport"];
export type Health = components["schemas"]["HealthResponse"];
export type DebugRequest = components["schemas"]["DebugRequest"];
export type Fixture = components["schemas"]["FixtureInfo"];
type FixtureList = components["schemas"]["FixtureList"];
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const object = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null;
function isEvidence(value: unknown): value is Evidence {
  return object(value) && typeof value.fixture_id === "string" && Array.isArray(value.test_command)
    && typeof value.image_reference === "string" && (value.container_image_id === null || typeof value.container_image_id === "string")
    && (value.error == null || typeof value.error === "string")
    && value.test_command.every((item) => typeof item === "string") && typeof value.stdout === "string"
    && typeof value.stderr === "string" && typeof value.duration_seconds === "number"
    && typeof value.started_at === "string" && typeof value.timed_out === "boolean"
    && (value.exit_code === null || typeof value.exit_code === "number")
    && ["tests_passed", "tests_failed", "timeout", "infrastructure_failure"].includes(String(value.status));
}
function isReport(value: unknown): value is DebugReport {
  return object(value) && typeof value.fixture_id === "string" && typeof value.verified === "boolean"
    && typeof value.provider === "string" && ["blocked_execution", "baseline_unexpected", "provider_error", "patch_rejected", "verification_failed", "verified"].includes(String(value.status))
    && (value.error == null || typeof value.error === "string")
    && (value.source_sha256 == null || (object(value.source_sha256) && Object.values(value.source_sha256).every((hash) => typeof hash === "string")))
    && [value.baseline, value.failing_test, value.regression].every((stage) => stage == null || isEvidence(stage))
    && (value.candidate == null || (object(value.candidate) && typeof value.candidate.hypothesis === "string"
      && typeof value.candidate.unified_diff === "string" && Array.isArray(value.candidate.references)
      && value.candidate.references.every((ref) => object(ref) && typeof ref.path === "string" && typeof ref.line === "number" && typeof ref.quote === "string")));
}
export class ApiError extends Error {}
async function request<T>(path: string, guard: (value: unknown) => value is T, body?: unknown): Promise<{ data: T; httpStatus: number }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), body ? 180000 : 8000);
  try {
    const response = await fetch(API_BASE + path, {
      method: body ? "POST" : "GET", signal: controller.signal, cache: "no-store", credentials: "omit",
      ...(body ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}),
    });
    let data: unknown;
    try { data = await response.json(); } catch { throw new ApiError(`The API returned an unreadable response (HTTP ${response.status}).`); }
    // Reports on 422/502/503 contain real evidence and must remain visible.
    if (guard(data)) return { data, httpStatus: response.status };
    if (object(data) && object(data.error) && typeof data.error.message === "string") {
      throw new ApiError(`${data.error.message} (HTTP ${response.status})${response.status === 404 ? ". Check that the backend is in development mode." : ""}`);
    }
    throw new ApiError(`Unexpected API response (HTTP ${response.status}). Check the backend version.`);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(controller.signal.aborted
      ? "The request timed out. The backend may still be running; wait before retrying."
      : "Cannot reach the API. Check that FastAPI is running on port 8000 and that this browser origin is allowed by CORS.");
  } finally { clearTimeout(timeout); }
}
export const getHealth = () => request("/health", (v): v is Health => object(v) && typeof v.service === "string" && typeof v.status === "string" && typeof v.version === "string");
export const getFixtures = () => request("/api/v1/fixtures", (v): v is FixtureList => object(v) && Array.isArray(v.fixtures)
  && v.fixtures.every((f) => object(f) && ["fixture_id", "name", "category", "description", "example_bug_description"].every((key) => typeof f[key] === "string")
    && typeof f.expected_failed === "number" && typeof f.expected_passed === "number"));
export const reproduce = (fixture_id: DebugRequest["fixture_id"]) => request("/api/v1/reproductions", isEvidence, { fixture_id });
export const debug = (body: DebugRequest) => request("/api/v1/debug-runs", isReport, body);
