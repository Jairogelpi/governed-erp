# Code / repository annex (Spec 95 Sec 39.2)

- **Repository**: `Jairogelpi/governed-erp` (public remote); local clone
  path used during development is `Jairogelpi/TFM`.
- **Branch this phase was built on**: `feat/phase22-tfm-delivery-and-release-freeze`,
  merged to `main`.
- **Baseline tag**: `erpguard-evolution-phase0-baseline`
  (`e483f5c5f272139c65a02ebc32ab11f5e323b6a4`).
- **`v1.0.0-tfm` tag**: **not created yet.** Tagging the immutable TFM
  submission is a deliberate, one-way decision about a real academic
  submission and belongs to the thesis author, not to any automated
  process. Everything needed to make it a trivial, verifiable action is
  in place (this annex set, the Definition of Done test, the memory
  draft) -- the tag itself is the one remaining manual step. To cut it
  once ready:

  ```bash
  git tag -a v1.0.0-tfm -m "TFM submission freeze"
  git push origin v1.0.0-tfm
  ```

- **Commit hash for a specific submission**: capture at tagging time with
  `git rev-parse HEAD` and record it here (or let the tag itself serve as
  the pointer -- `git rev-parse v1.0.0-tfm` after pushing).
- **License**: see `LICENSE` at the repository root.
- **CI**: `.github/workflows/ci.yml` -- `quality` (ruff, mypy, pytest,
  alembic upgrade, Python 3.11 + 3.13), `docker` (image build), `postgres-migrations`
  (upgrade + downgrade/upgrade cycle against real PostgreSQL), `frontend`
  (Vitest, `tsc -b`, production build), `secret-scan` (gitleaks), and
  `release-checks` (dependency scan, SBOM, benchmark smoke test, docs
  link check -- Spec 95 additions).
