# Unified connections — Phase 4

Reality label: `implemented locally; staging-only secret provider`.

The canonical public API is `/v1/unified/connections`. It is tenant-scoped by
the Phase 3 bearer identity boundary and stores credentials as Fernet-encrypted
ciphertext in `encrypted_secrets`. API responses expose only a reference and a
short fingerprint; they never expose the secret or ciphertext.

The existing `/v1/connections` API is a compatibility path and now returns
`Deprecation: true` with a successor link. Existing legacy rows can be moved by
calling `migrate_legacy_connections` with the configured local provider; the
legacy JSON secret is replaced with a redaction marker after encrypted storage
is created. The old Odoo read-only connection test remains the controlled
real-connection validation path. No ERP write or raw ERP execution is added.

The local provider is appropriate for a single-node/staging deployment. A
managed external secret provider and connector-consumption unification remain
later work.
