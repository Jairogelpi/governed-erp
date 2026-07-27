# Contributing

1. Read `AGENTS.md` and the relevant master-spec phase before changing code.
2. Keep changes incremental and preserve verified behavior.
3. Add or update tests with every implementation change.
4. Run focused tests, the full suite, `ruff`, `mypy` and `git diff --check`.
5. Do not add raw ERP execution, credentials, unrestricted HTTP, shell or browser actions.
6. Label capabilities as `real`, `staging_only`, `fixture`, `simulated`, `advisory`, `planned` or `blocked`.

Pull requests should state the phase, changed files, verification results, limitations and exact next allowed phase.

