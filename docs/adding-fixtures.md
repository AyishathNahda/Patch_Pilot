# Adding an approved fixture safely

Fixture admission is a reviewed source change, never an API operation. Do not
scan directories for fixtures or accept repository URLs, code, commands or paths
from requests. Preserve existing benchmark originals.

1. Create a small package under `benchmarks/fixtures/<id>`. Use one Python source
   file as the only patch target, one pytest test file, `manifest.json`, and a
   README. Prefer standard-library code. Package imports must not run on the host.
2. Document intended behavior and one realistic deliberate bug. Provide exactly
   one deterministic failing test node plus meaningful regression tests. Avoid
   time/network/random dependence. Keep original source buggy; candidate fixes
   belong only in disposable copies.
3. Document the expected failing node, `expected_failed=1`, passing count, and
   the fixed `TEST_COMMAND` in the manifest. The manifest is documentation and
   candidate identity metadata; it cannot authorize execution commands/files.
4. Add the exact ID to `FixtureId` and a frozen `Fixture` entry in
   `services/sandbox-runner/patchpilot_sandbox/fixtures.py`. Review its source/test
   paths, targeted node, observed failure marker, counts and intended behavior.
   Paths must be relative, inside this package, free of links/traversal, and
   distinct from each other. Never register tests as patch targets. The runner
   copies only these files plus the manifest; never include `.env` or host data.
5. Extend `NEW_IDS` and the **test-only** deterministic candidate helper in
   `apps/api/tests/test_multi_fixtures.py`. Add cross-fixture/path/identity rejection
   cases and any special regression cases. Do not add a production mock model.
6. Run the normal suite, then real Docker integration tests. The existing Docker
   image must already contain reviewed dependencies: never install fixture
   requirements on the API host or enable network access for execution. A new
   dependency/image change needs separate review. Current fixtures need none.
7. Confirm baseline failure/counts and real passing targeted/full tests after a
   candidate fix; verify commands, image identity, output completeness, original
   file hashes and container/copy cleanup. Failed or unavailable infrastructure
   is not reproduction evidence. AI output alone never verifies a fix.
8. Regenerate frontend types with `npm.cmd run generate:api` from `apps/web`
   against the updated API, run typecheck/lint/build, and check dynamic selection
   and example text. Update the API/README fixture table and verification record.
   Do not duplicate the allowlist or expected counts in UI source.

Commands from root (Docker Desktop running and trusted image built):

```powershell
.\.venv\Scripts\python.exe -m pytest -q -W error
.\.venv\Scripts\python.exe -c "import os,pytest; os.environ['PATCHPILOT_RUN_DOCKER_TESTS']='1'; os.environ['PATCHPILOT_RUN_GROQ_TESTS']='0'; raise SystemExit(pytest.main(['-q','-W','error','-m','docker']))"
docker ps -a --filter label=patchpilot.reproduction=day2 --format '{{.Names}}'
```

The CI Docker job automatically collects marked integration tests without a Groq
key. Run live Groq checks deliberately and retain actual reports locally; do not
print credentials. Adding a registry entry does not authorize commits, pushes,
pull requests or deployment.
