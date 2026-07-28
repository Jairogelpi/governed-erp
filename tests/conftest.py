"""Test-only compatibility harness for pre-C1 route tests.

Historical tests import ``apps.api.main:app`` and exercise routes that are now
available only through the explicit legacy composition. Production defaults
remain public-only; the composition tests construct the public app directly.
This harness is temporary migration support for the later C6/C7 test waves.
"""

import os


os.environ.setdefault("ERPGUARD_LEGACY_API_ENABLED", "true")
