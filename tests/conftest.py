"""Mount the internal tooling surface by default for the test session.

Production leaves this opt-in (``ERPGUARD_INTERNAL_SURFACES=true``); tests
exercise demo/fake-ERP/record-to-skill tooling directly, so it must be on.
"""

import os


os.environ.setdefault("ERPGUARD_INTERNAL_SURFACES", "true")
