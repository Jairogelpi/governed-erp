# Candidate branching — Phase 11

Reality label: `implemented locally; manual/structured proposal only`.

Process candidates are created against an existing immutable process version.
Each draft carries explicit changes and evidence references (`evt:`, `case:`
or `variant:`). Submission changes the candidate to an immutable `submitted`
state; later mutation is blocked. A structured proposal can be attached as
data, but no LLM is invoked.

The protected API supports draft creation, explicit submission and retrieval.
There is deliberately no activation or promotion endpoint. Candidate evidence
is required before submission, and missing base process versions are rejected.

No historical replay, candidate execution, ERP write or automatic activation
is included in Phase 11.
