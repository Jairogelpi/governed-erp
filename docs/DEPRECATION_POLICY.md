# Deprecation policy

The repository is migrating incrementally. Existing routes, modules and documents are not removed merely because a new boundary is planned.

- New public entry points must be documented in the canonical public documentation.
- Historical sprint and release-candidate documents are legacy records and must not be presented as current product claims.
- A legacy route or module may be removed only after two consecutive phases no longer depend on it, compatibility coverage exists, and an ADR or migration note records the replacement.
- Compatibility links and imports may remain during migration.
- ERPGuard remains the mandatory safety kernel for every future effectful execution.
- No deprecation may authorize raw ERP execution or expose credentials.

