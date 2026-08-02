"""Small production composition root."""

from apps.api.app_factory import create_app

# Serves web/dist when ERPGUARD_SERVE_FRONTEND=true and it has been built
# (`npm run build`); off by default, same opt-in posture as
# ERPGUARD_INTERNAL_SURFACES, so importing this module (as several tests
# do) never depends on incidental local build artifacts.
app = create_app()
