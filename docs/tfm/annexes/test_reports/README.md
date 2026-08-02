# Test reports annex (Spec 95 Sec 39.2)

`latest_pytest_output.txt` in this directory is the raw output of

```bash
python -m pytest
```

captured on 2026-08-02 against this branch. Summary: 990 tests collected,
4 skipped (browser/Chromium-dependent, see `README.md`'s "Quickstart and
focused verification" note), 0 failed.

This is a point-in-time capture, not a live artifact -- regenerate it
before a real submission with:

```bash
python -m pytest -q > docs/tfm/annexes/test_reports/latest_pytest_output.txt 2>&1
```

CI's authoritative, continuously-updated record is the `quality` job
(runs on Python 3.11 and 3.13) in `.github/workflows/ci.yml`, visible at
the repository's Actions tab -- link the specific run ID for the commit
being submitted alongside this file.
