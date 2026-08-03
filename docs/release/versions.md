# Release version ladder (Spec 95 Sec 40 / Sec 40.1)

Versions "may be consolidated but must be consistent" per the master
spec -- Spec 92's four workstreams landed inside the `v0.19.0` window
rather than getting their own bump, for example.

| Version | Scope | Git tag status |
| --- | --- | --- |
| `v0.13.0-rc1` | Historical ERPGuard candidate | Not tagged in this history (pre-dates this repo's tag record; see `docs/legacy/releases.md`) |
| `v0.14.0` | Migration foundation | Not separately tagged |
| `v0.15.0` | Connector SDK + events | Not separately tagged |
| `v0.16.0` | Process/version/mining | Not separately tagged |
| `v0.17.0` | Replay/proof | Not separately tagged |
| `v0.18.0` | Compiler/runtime v2 | Not separately tagged |
| `v0.19.0` | Odoo quote vertical + Spec 92 decision-to-outcome backend | Not separately tagged |
| `v0.20.0` | Shadow/canary + benchmark (Phase 20) | Not separately tagged |
| `v1.0.0-tfm` | **Immutable TFM release** | **Created** -- see `docs/tfm/annexes/code_and_repository.md` |
| `v1.0.0-beta.1` | Public beta presentation | Not yet created; explicitly a separate, later release per Sec 40 -- this phase only proves `v1.0.0-tfm` is submittable, not that the beta has shipped |

## Tags that actually exist in this repository today

```text
erpguard-evolution-phase0-baseline  (e483f5c5f272139c65a02ebc32ab11f5e323b6a4)
v1.0.0-tfm
```

This project has, in practice, tracked progress through this session's
Git history and `docs/architecture/capability_reality_matrix.md` rather
than a tag per intermediate version above -- the version numbers in the
table are the master spec's naming scheme for what shipped in each
window, not a claim that a corresponding Git tag exists for each one.

`v1.0.0-tfm` was recreated after PR #57 so the tag, package version,
README header, and this release documentation identify the same frozen
release. It had not been shared or cited anywhere before that move, so
moving it (rather than cutting a `.1` successor) was the correct fix.
`v1.0.0-beta.1` remains a real, expected future tag not yet created.

## Cutting `v1.0.0-tfm`

```bash
git tag -a v1.0.0-tfm -m "TFM submission freeze"
git push origin v1.0.0-tfm
```

Do this only once every Definition of Done item in
`docs/specs/95_phase22_tfm_delivery_and_release_freeze.md` that requires
human judgment (memory readability, video recorded and under 5 minutes,
bibliography complete, repository permissions correct) has actually been
checked by the thesis author -- `tests/test_phase22_definition_of_done.py`
documents which items are mechanically checkable and which aren't.
