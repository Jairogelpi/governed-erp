# Quote-to-Order process package — Phase 9

Reality label: `implemented locally; baseline definition fixture`.

The baseline process is stored in
`policies/processes/quote_to_order_v1.yaml`. It declares objects, canonical
events, decisions, metrics, blocking policies and a happy-path fixture. The
validator rejects missing references, duplicate names, invalid YAML and
inconsistent fixture references.

`ProcessRegistry` stores immutable `(process_key, version)` rows in the
existing versioned persistence boundary. Re-registering identical content is
idempotent; changing an existing version is rejected. The protected API is:

- `POST /v1/processes` for admin registration;
- `GET /v1/processes/{process_key}/versions/{version}` for viewer retrieval;
- `GET /v1/processes/{process_key}/diff` for version comparison.

No process variant discovery, replay, candidate branching, skill compilation
or ERP execution is included in Phase 9.
