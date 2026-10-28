# PatchPilot contributor instructions

## Purpose and scope
PatchPilot will investigate repository bugs, propose patches, and present evidence from real isolated tests. Implement only the milestone requested. Prefer maintainable, understandable code over clever abstractions.

## Architecture and conventions
- `apps/api`: Python 3.11/3.12, FastAPI, Pydantic settings; later SQLAlchemy/Alembic and PostgreSQL.
- `apps/web`: Next.js App Router, TypeScript, Tailwind, reusable accessible components. Use npm and its lockfile; regenerate API types from FastAPI OpenAPI after contract changes.
- `services/sandbox-runner`: Docker orchestration for the curated fixture, pytest, strict time/resource limits.
- `benchmarks`: curated bug fixtures and evaluation cases.
- `infra`: deployment and Docker Compose configuration.
- `docs`: architecture, security boundaries, and technical decisions.
- `.github/workflows`: CI/CD when requested.
- Future AI uses provider-independent integration (initially Groq), validated structured responses and tool calling. Redis/Celery will handle background jobs. Avoid premature microservices.

## Coding and testing
- Use clear names, focused modules, useful type hints, and explicit error handling.
- Validate external input and configuration. Add only necessary dependencies.
- Run relevant tests after changes; test observable behavior, including failure paths.
- Never fabricate test results or AI investigation evidence. Report checks that could not run.
- Keep AI reasoning separate from execution and verification.

## Security boundaries
- Never execute untrusted code on the API server.
- Do not expose secrets to repository execution environments. Never commit credentials.
- Repository execution belongs in isolated, resource-limited environments. Only fixtures in the explicit reviewed registry are supported; arbitrary repositories remain prohibited.
- Require human approval before commits, pushes, deployments, or pull-request creation.

## Workflow
- Inspect existing files and instructions before editing. Make small, scoped changes.
- Explain important architectural decisions and tradeoffs.
- Keep the README and architecture documentation updated when necessary.
- At the end of each task, summarize changes, tests, failures, and next steps.
