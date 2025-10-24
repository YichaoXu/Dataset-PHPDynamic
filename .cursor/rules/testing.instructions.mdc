---

description: apply only when modifying any files about testing

alwaysApply: false

---

# Testing Standards

## 1. Layout
- Select ONE layout profile and apply repo-wide.
- Profile A: `tests/` root; files `<component>.test.<ext>`
- Profile B: `tests/` root; files `test_<component>.<ext>`
- Profile C: co-located near source; files `*_test.<ext>`
- Profile D: dedicated tree `src/test/<lang>/`; mirror packages/namespaces
- Profile E: inline unit in source; integration in `tests/`

## 2. Types
- Unit: isolated from external systems; single unit per test file where feasible.
- Integration: cross-module or external interaction; run separately from unit.

## 3. Structure
- Use Arrange → Act → Assert.
- One behavior per test case.
- Name cases: `test_<component>_<condition>_<expected>` (adapt to framework idioms).
- Group cases in suites/classes only if the framework requires classes.

## 4. Naming & Location
- Mirror source module/component layout under the selected profile.
- Use one of: `test_<component>.<ext>` | `<component>.test.<ext>` | `*_test.<ext>`.

## 5. Fixtures & Data
- Centralize reusable setup via fixtures/factories.
- Provide scenario-specific fixtures per test when needed.
- Use temporary resources for file/network/process interactions; auto-clean after tests.

## 6. Assertions
- Prefer one focused assertion per test; add more only when verifying a single behavior.
- Use specific assertion forms (equality, errors, ranges) over generic boolean checks.
- Assert negative paths and error conditions explicitly.

## 7. Mocking
- Mock only at system boundaries of the unit under test.
- Prefer dependency injection to enable mocking.
- Use test doubles (mocks/stubs/fakes) with verified critical interactions.
- Do not over-mock; prefer real behavior for internal collaborators.

## 8. Configuration
- Declare framework, discovery rules, markers/tags, and strict/fail-fast options in the repo config.
- Keep environment setup deterministic (fixed seeds, stable paths, isolated temp dirs).

## 9. Execution
- Default command runs unit tests only; provide a separate command/marker for integration.
- Enable parallel execution when the framework supports it.
- Use concise tracebacks; stop-on-first-failure mode for debugging.

## 10. Coverage
- Target coverage ≥ 90% for statements/branches on changed modules.
- Measure coverage for `src` (or equivalent) only; exclude generated code and vendor deps.
- Report missing lines; fail CI below threshold.

## 11. Maintenance
- Add tests alongside new/changed code in the same change set.
- Keep tests independent; no shared mutable state across tests.
- Refactor tests to remove duplication (helpers, fixtures, factories).

## 12. Agent Outputs (when generating human docs)
- Produce a minimal runnable example per public API in the requirements doc.
- Include test snippets demonstrating Arrange–Act–Assert for typical and error cases.
- Document how to run unit vs integration tests for the selected layout profile.