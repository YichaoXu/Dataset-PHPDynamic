---
globs: **/todo.md
alwaysApply: false
---
# Task Management Standards

## Required TODO Structure
The following content MAY appear in todo.md. Do not include internal rules here.

### Task Item Format
- Title: `[state] <action verb> <object> <detail>`
- Metadata (indented):
  - `Depends on: <task ids>`
  - `Acceptance: <criteria>`
  - `Notes: <note>`
- Subtasks (indented checkboxes): `- [ ] <subtask>`

### Phase Completion Checklist
Every task phase MUST end with these subtasks:
- `- [ ] Run code quality checks (linting, formatting)`
- `- [ ] Fix all linting errors above threshold`
- `- [ ] Ensure consistent code formatting`
- `- [ ] Write unit tests for new public methods/functions`
- `- [ ] Test normal, error, and edge cases`
- `- [ ] Verify all tests pass`
- `- [ ] Update documentation if needed`

### Scope Rules
- Each task completable in single session
- Include implementation details only
- List explicit dependencies
- Reference existing interfaces from design documents

### Example
```
[ ] Implement StaticAnalyzer selection
  Depends on: Modeling design ready
  Acceptance: Semgrep analyzer returns candidates for 2 variables
  - [ ] Add SemgrepAnalyzer class wiring
  - [ ] Validate supported languages via LanguageSupport
  - [ ] Run code quality checks (linting, formatting)
  - [ ] Fix all linting errors above threshold
  - [ ] Ensure consistent code formatting
  - [ ] Write unit tests for new public methods/functions
  - [ ] Test normal, error, and edge cases
  - [ ] Verify all tests pass
  - [ ] Update documentation if needed
```

---

## AI Authoring Guidelines (Internal Use Only)

### Task Writing Rules
- Use action verb + object + detail
- Specify expected behavior for operations
- Include acceptance criteria when verifiable
- Do not introduce new design content in TODO files
- Reference only interfaces defined in design documents

### Task Scope & Breakdown
- Ensure task completable in one development session
- Break complex work into smaller tasks
- Specify dependencies and prerequisites explicitly

### Phase Completion Enforcement
- Every task phase MUST include the Phase Completion Checklist as subtasks
- These subtasks are mandatory and cannot be omitted
- They ensure consistent quality and testing across all phases

### Status Management
- Update task state immediately after change
- Mark dependent tasks when prerequisites complete
- Record completion criteria succinctly

### File Organization
- Keep one todo.md per phase when needed
- Use sequential numbering when multiple files are required (1.todo.md, 2.todo.md)
- Group related tasks together

### Templates
- Feature:
```
[ ] Implement <FeatureName>
  Acceptance: <criteria>
  - [ ] <subtask>
  - [ ] Run code quality checks (linting, formatting)
  - [ ] Fix all linting errors above threshold
  - [ ] Ensure consistent code formatting
  - [ ] Write unit tests for new public methods/functions
  - [ ] Test normal, error, and edge cases
  - [ ] Verify all tests pass
  - [ ] Update documentation if needed
```
- Bug Fix:
```
[ ] Fix <BugDescription>
  Acceptance: <repro no longer fails>
  - [ ] Reproduce
  - [ ] Root cause
  - [ ] Implement fix
  - [ ] Regression test
  - [ ] Run code quality checks (linting, formatting)
  - [ ] Fix all linting errors above threshold
  - [ ] Ensure consistent code formatting
  - [ ] Write unit tests for new public methods/functions
  - [ ] Test normal, error, and edge cases
  - [ ] Verify all tests pass
  - [ ] Update documentation if needed
```
- Refactor:
```
[ ] Refactor <Component>
  Acceptance: <no behavior change, tests pass>
  - [ ] Analyze
  - [ ] Implement
  - [ ] Update tests
  - [ ] Run code quality checks (linting, formatting)
  - [ ] Fix all linting errors above threshold
  - [ ] Ensure consistent code formatting
  - [ ] Write unit tests for new public methods/functions
  - [ ] Test normal, error, and edge cases
  - [ ] Verify all tests pass
  - [ ] Update documentation if needed
```