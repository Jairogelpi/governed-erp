# Identity and tenant enforcement

Phase 3 adds a bounded local identity slice without claiming production SSO or changing every legacy route in one migration.

## Contract

- `IdentityUser`, `IdentityRole` and `IdentityMembership` live in `erpguard.db.model_packages.identity`.
- `Authorization: Bearer <signed-token>` establishes a principal only when `ERPGUARD_AUTH_SECRET` is configured.
- The token carries user and tenant claims; the server reloads the active user and membership from the database and derives the role.
- `GET /v1/identity/me` exposes the server-derived principal.
- `POST /v1/identity/tenants/{tenant_id}/members` requires an admin membership in the path tenant.
- Request `actor` and `tenant_id` fields are never trusted. A mismatched tenant is rejected and the response actor is the authenticated user.

## Reality and boundary

`real` for the bounded API contract and local HMAC verification. `staging_only` for deployment because no external identity provider, key rotation service, session revocation store or production SSO integration exists yet.

Legacy routes remain compatibility paths during the incremental migration. Phase 3 security tests cover the new protected boundary; broad legacy-route conversion requires explicit follow-up work and must not weaken the safety kernel.

