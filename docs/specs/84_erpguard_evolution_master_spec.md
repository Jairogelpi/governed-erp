# ERPGuard Evolution — Master Implementation Specification

**Document type:** Authoritative product, architecture, migration, implementation and validation specification  
**Repository:** `Jairogelpi/TFM`  
**Target product name:** **ERPGuard Evolution**  
**Safety kernel:** **ERPGuard**  
**First full connector:** **Odoo 19**  
**Document status:** Normative source of truth for implementation agents  
**Baseline commit:** `e483f5c5f272139c65a02ebc32ab11f5e323b6a4` (`feat: add visual table form extraction`)  
**Target release:** `v1.0.0-tfm` followed by public beta `v1.0.0-beta.1`  
**TFM delivery deadline:** 17 September 2026, 23:59 Europe/Madrid  
**Primary language of code and technical artifacts:** English  
**Primary language of TFM and business UI:** Spanish, with English i18n-ready identifiers  
**Compatibility policy:** Incremental migration inside the existing repository; no destructive rewrite

---

# 0. How an implementation AI must use this document

This document is not a brainstorm. It is the implementation contract.

An AI following this specification must:

1. Start from the exact existing repository state.
2. Inspect the current code before modifying any module.
3. Preserve verified ERPGuard behavior unless this document explicitly replaces it.
4. Implement one phase at a time.
5. Run the required tests and acceptance commands after every phase.
6. Record every meaningful change in `AGENTS.md`.
7. Create an Architecture Decision Record for every architectural deviation.
8. Never add a new product area merely because it is easy to generate.
9. Never claim a feature is real if it is fixture-only, simulated, contract-only or advisory.
10. Never bypass the safety kernel to make a demo work.
11. Never expose a raw ERP method to an agent.
12. Never store a live credential in a prompt, log, test fixture or Evidence Pack.
13. Stop a phase when its exit criteria are met.
14. Do not begin the next phase while the full regression suite is red.
15. Treat the code as the final source of truth and update this document when an approved design change occurs.

## 0.1. Required implementation loop

For every phase:

```text
Inspect current implementation
→ write/update tests for the target behavior
→ implement the smallest coherent vertical slice
→ run focused tests
→ run full tests
→ run static/security checks
→ update docs and AGENTS.md
→ create one intentional commit
→ freeze evidence
```

## 0.2. Prohibited implementation behavior

The implementation AI must not:

- replace the repository with a greenfield project;
- delete current modules before proving their replacement;
- add SAP, Salesforce, Dynamics, NetSuite or ERPNext execution in the TFM release;
- add a generic `execute(model, method, args)` public capability;
- add arbitrary SQL, shell, Python, browser actions or unrestricted HTTP;
- implement autonomous production deployment;
- enable autoapproval;
- perform real accounting, payments or mass deletion;
- place all new models into the already monolithic `erpguard/db/models.py`;
- place all new repositories into the already monolithic `erpguard/db/repositories.py`;
- add more functionality to the old `/demo` monolith except a redirect or compatibility link;
- call a simulated credential fingerprint a production secret vault;
- use an LLM in deterministic replay or repeated runtime unless the run explicitly enters an approved repair/explanation path;
- mutate an active process version, skill version, policy bundle or Proof of Improvement;
- use historical replay results as a causal guarantee of future revenue or conversion.

---

# 1. Product decision

## 1.1. Final product

ERPGuard Evolution is an open-source platform for versioning, evaluating and safely deploying business processes connected to enterprise systems.

It converts operational history into a versioned process asset:

```text
Observe
→ Normalize
→ Discover
→ Propose
→ Replay
→ Prove
→ Compile
→ Shadow
→ Canary
→ Promote
→ Monitor
→ Roll back
```

ERPGuard remains the mandatory safety kernel for every effectful execution:

```text
Plan
→ Preflight
→ Policy
→ Approval
→ Execution Permit
→ Connector
→ Postcondition Verification
→ Evidence Pack
```

## 1.2. Product sentence

> ERPGuard Evolution turns business operations into versioned processes that can be replayed against history, proven safer or more effective, compiled into governed skills and deployed through system-specific connectors.

## 1.3. Developer sentence

> Open-source CI/CD for business processes, with object-centric events, historical replay, Proof of Improvement, governed deterministic skills and pluggable enterprise connectors.

## 1.4. Odoo-first promise

The first release must deliver a complete Quote-to-Order vertical on Odoo.

The architecture must support additional connectors, but no second enterprise connector is required for the TFM.

The first release proves extensibility using:

- `FakeConnector`;
- `OCELImportConnector`;
- `OdooConnector`;
- `ConnectorTemplate`;
- `ConnectorContractTestKit`.

## 1.5. Revolutionary element

The differentiator is not process mining, approvals, agent tools or RPA separately.

The differentiator is the complete lifecycle:

```text
operational evidence
→ process version
→ candidate branch
→ historical replay
→ regression detection
→ Proof of Improvement
→ governed skill
→ shadow evaluation
→ controlled promotion
→ rollback
```

The primary public metaphor is:

> Git and CI/CD for company operations.

This metaphor is explanatory. The product must not pretend business processes are identical to source code.

---

# 2. TFM thesis and product boundary

## 2.1. Research question

> Can an ERP-independent architecture based on canonical events, historical replay and governed skill execution produce and evaluate an improved version of an Odoo Quote-to-Order process while reducing unsafe side effects, known errors, duplicate operations, manual interventions and runtime variability compared with a fixed workflow and a direct-tool AI agent?

## 2.2. Hypotheses

### H1 — Safety

ERPGuard Evolution reduces forbidden or incorrect ERP side effects compared with a direct-tool agent.

### H2 — Reproducibility

A compiled deterministic process version produces lower run-to-run variability than an agent that reasons on every execution.

### H3 — Efficiency

Repeated deterministic execution uses fewer LLM tokens than direct-agent execution.

### H4 — Regression detection

Historical replay identifies known regressions before a candidate process is activated.

### H5 — Auditability

The platform produces sufficient structured evidence to reconstruct the request, process version, decision, approval, native operations and verified result.

### H6 — Extensibility

A connector can be added through the Connector SDK without importing Odoo-specific modules into the platform core.

## 2.3. TFM vertical

The complete vertical is:

```text
Quote request
→ customer resolution
→ product resolution
→ price list selection
→ margin/discount policy
→ stock availability preflight
→ quotation draft creation
→ optional confirmation approval
→ confirmation or block
→ postcondition verification
```

## 2.4. Required process versions

The TFM must compare:

1. **Baseline Fixed v1**  
   A deterministic manually defined process.

2. **Direct Agent Baseline**  
   An AI agent with a deliberately bounded but comparatively broad set of Odoo tools.

3. **Evolution Candidate v2**  
   A process candidate created from observed variants and business constraints, evaluated through replay and compiled into a governed skill.

## 2.5. TFM minimum real execution

Required:

- real Odoo authentication against a controlled staging/demo database;
- real read of customers, products, price lists, stock and quotations;
- real creation of a quotation in draft;
- postcondition verification;
- evidence generation.

Conditional:

- real `action_confirm` only if all R3 controls, staging protections and rollback/cleanup procedures are complete.

Allowed fallback:

- if confirmation cannot be safely completed by feature freeze, the system must demonstrate a real preflight and explicit block; it must not simulate a confirmation and present it as real.

## 2.6. Explicit non-goals for the TFM

- causal optimization of conversion or margin;
- universal process discovery;
- enterprise-scale streaming;
- a second real ERP connector;
- production deployment for accounting;
- automatic promotion without human decision;
- reinforcement learning;
- browser automation against real Odoo;
- generic MCP CRUD;
- full SaaS billing;
- marketplace;
- visual workflow editor;
- mobile application;
- natural-language generation of arbitrary policies.

---

# 3. Baseline repository assessment

## 3.1. Current strengths to preserve

The current repository already includes:

- FastAPI API layer;
- SQLAlchemy persistence;
- canonical ERP objects;
- risk engine;
- policy engine;
- preflight;
- Formula Guard;
- skill registry and versioning;
- recording sessions;
- Record-to-Skill compiler;
- deterministic Fake ERP runtime;
- approval pipeline;
- operator action planning;
- controlled Fake ERP execution;
- evidence packs;
- credential-reference concepts;
- Odoo read-only adapter foundations;
- adapter contract;
- capability registry;
- connector setup;
- extensive tests;
- clean-install scripts;
- deployment documentation.

These are assets, not disposable prototypes.

## 3.2. Current structural liabilities

The migration must explicitly address:

- a monolithic HTML/JS demo;
- approximately 55 API routers;
- approximately 241 product modules;
- approximately 110 models in one file;
- approximately 290 repository functions in one file;
- duplicated or overlapping lifecycle concepts;
- version drift between README, API and `pyproject.toml`;
- simulated/placeholder features displayed near real features;
- two generations of Odoo connection logic;
- a contract-oriented connector path that is not the only live path;
- SQLite as default persistence;
- absence of formal database migrations;
- incomplete identity and tenant enforcement;
- no complete real business write vertical;
- historical sprint documentation mixed with product entry points.

## 3.3. Baseline rule

No new architecture phase may increase the number of public routers, top-level product services or database models without also defining:

- ownership;
- lifecycle;
- replacement/deprecation mapping;
- API boundary;
- tests;
- migration strategy.

---

# 4. Target repository architecture

The repository remains one monorepo.

## 4.1. Target structure

```text
TFM/
├── AGENTS.md
├── README.md
├── LICENSE
├── SECURITY.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── GOVERNANCE.md
├── SUPPORT.md
├── CITATION.cff
├── CHANGELOG.md
├── ROADMAP.md
├── pyproject.toml
├── uv.lock
├── alembic.ini
├── docker-compose.yml
├── docker-compose.demo.yml
├── .env.example
├── apps/
│   ├── api/
│   │   ├── main.py
│   │   ├── dependencies/
│   │   ├── middleware/
│   │   ├── routes/
│   │   │   ├── public_v1/
│   │   │   ├── internal/
│   │   │   └── legacy/
│   │   └── schemas/
│   └── web/
│       ├── package.json
│       ├── src/
│       └── tests/
├── erpguard/
│   ├── domain/
│   │   ├── identity/
│   │   ├── connections/
│   │   ├── canonical/
│   │   ├── processes/
│   │   ├── skills/
│   │   ├── approvals/
│   │   ├── execution/
│   │   └── evidence/
│   ├── application/
│   │   ├── commands/
│   │   ├── queries/
│   │   ├── services/
│   │   └── ports/
│   ├── infrastructure/
│   │   ├── persistence/
│   │   ├── secrets/
│   │   ├── queues/
│   │   ├── llm/
│   │   └── telemetry/
│   ├── connectors/
│   │   ├── sdk/
│   │   ├── registry/
│   │   ├── fake/
│   │   ├── ocel/
│   │   ├── odoo/
│   │   └── template/
│   ├── events/
│   │   ├── models/
│   │   ├── normalization/
│   │   ├── ingestion/
│   │   └── storage/
│   ├── mining/
│   │   ├── variants/
│   │   ├── metrics/
│   │   └── conformance/
│   ├── evolution/
│   │   ├── candidates/
│   │   ├── replay/
│   │   ├── proofs/
│   │   ├── shadow/
│   │   ├── canary/
│   │   └── promotion/
│   ├── compiler/
│   │   ├── process_to_skill/
│   │   └── recording_to_skill/
│   ├── runtime/
│   │   ├── deterministic/
│   │   ├── permits/
│   │   ├── idempotency/
│   │   └── verification/
│   ├── core/
│   ├── policies/
│   ├── invariants/
│   └── legacy/
├── connector_packages/
│   └── README.md
├── processes/
│   └── quote_to_order/
├── skills/
│   └── quote_to_order_odoo/
├── benchmarks/
│   └── erpriskbench/
├── datasets/
│   ├── synthetic/
│   └── schemas/
├── migrations/
│   └── versions/
├── docs/
│   ├── architecture/
│   ├── product/
│   ├── security/
│   ├── connectors/
│   ├── tfm/
│   ├── adr/
│   ├── release/
│   └── archive/
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── e2e/
│   ├── security/
│   ├── benchmark/
│   └── legacy/
└── scripts/
```

## 4.2. Incremental structure rule

The target structure is achieved incrementally.

Do not move hundreds of files in one commit.

Use this progression:

1. Add new bounded-context modules.
2. Add compatibility imports.
3. Move one domain at a time.
4. Keep legacy routes operational behind a feature flag.
5. Run regressions.
6. Delete only after two consecutive phases no longer use the legacy path.

## 4.3. Dependency direction

The dependency graph must be:

```text
domain
  ↑
application
  ↑
infrastructure / connectors / API / web
```

Prohibited:

```text
domain → FastAPI
domain → SQLAlchemy
domain → Odoo
domain → PM4Py
domain → OpenAI SDK
domain → Playwright
```

Connector direction:

```text
erpguard.connectors.odoo
    imports connector SDK and domain contracts

erpguard.domain
    never imports erpguard.connectors.odoo
```

## 4.4. Naming rule

- Product: `ERPGuard Evolution`.
- Python distribution: `erpguard-evolution` at public release.
- Python import root: keep `erpguard`.
- Repository may remain `TFM` until final delivery.
- Public repository rename occurs only after release freeze.
- Avoid introducing `process_evolution` as a second import root.

---

# 5. Architectural layers

## 5.1. Experience layer

Interfaces:

- business web application;
- public REST API;
- CLI;
- future safe MCP gateway;
- connector developer tooling.

Responsibilities:

- onboarding;
- process selection;
- connection management;
- process visualization;
- candidate review;
- replay;
- approvals;
- execution;
- evidence;
- benchmark reporting.

## 5.2. Process Intelligence layer

Responsibilities:

- event normalization;
- object-centric event storage;
- case projection;
- variant discovery;
- duration and rework metrics;
- conformance;
- opportunity detection;
- candidate input features.

## 5.3. Evolution layer

Responsibilities:

- branch a process version;
- generate or define candidate changes;
- replay;
- compare;
- detect regressions;
- create Proof of Improvement;
- manage shadow/canary evaluation;
- promote or roll back.

## 5.4. Skill layer

Responsibilities:

- compile a process version;
- validate schemas;
- package capabilities;
- attach guards and policies;
- generate tests;
- register immutable versions;
- expose safe tool definitions later.

## 5.5. ERPGuard Safety Kernel

Responsibilities:

- identity and role enforcement;
- tenant boundary;
- risk classification;
- policy evaluation;
- invariants;
- approval requirements;
- execution permits;
- fail-closed behavior;
- kill switch;
- evidence;
- postcondition requirements.

## 5.6. Connector layer

Responsibilities:

- connection;
- schema discovery;
- fingerprint;
- event extraction;
- native-to-canonical mapping;
- canonical capability-to-native plan;
- execution;
- verification;
- native error normalization.

## 5.7. Evidence layer

Responsibilities:

- immutable process history;
- replay evidence;
- Proof of Improvement;
- execution evidence;
- benchmark evidence;
- TFM export;
- redaction;
- integrity hashes.

---

# 6. Canonical domain model

## 6.1. Core entity categories

### Identity

- `Tenant`
- `User`
- `ServicePrincipal`
- `Role`
- `Permission`
- `Membership`

### Connections

- `ConnectorDefinition`
- `Connection`
- `CredentialReference`
- `SystemFingerprint`
- `ConnectorCapability`

### Events

- `BusinessEvent`
- `BusinessObject`
- `ObjectType`
- `EventType`
- `EventObjectRelation`
- `ObjectObjectRelation`
- `AttributeChange`
- `EventBatch`
- `IngestionCursor`

### Processes

- `ProcessDefinition`
- `ProcessVersion`
- `ProcessBranch`
- `ProcessNode`
- `ProcessTransition`
- `DecisionPoint`
- `ProcessInvariant`
- `OutcomeMetricDefinition`
- `ProcessDeployment`

### Mining

- `CaseProjection`
- `ProcessVariant`
- `VariantStep`
- `VariantMetric`
- `ConformanceResult`

### Evolution

- `CandidateVersion`
- `CandidateChange`
- `ReplayDataset`
- `ReplayRun`
- `ReplayCaseResult`
- `Regression`
- `ProofOfImprovement`
- `ShadowEvaluation`
- `CanaryExperiment`
- `PromotionDecision`

### Skills

- `Skill`
- `SkillVersion`
- `SkillManifest`
- `CapabilityManifest`
- `WorkflowDefinition`
- `GuardBundle`
- `PolicyBundle`
- `SkillTestBundle`

### Execution

- `ActionPlan`
- `PreflightDecision`
- `ApprovalRequirement`
- `ApprovalDecision`
- `ExecutionPermit`
- `ExecutionRun`
- `NativeOperation`
- `PostconditionResult`
- `CompensationResult`

### Evidence

- `EvidencePack`
- `EvidenceArtifact`
- `AuditEvent`
- `IntegrityRecord`

## 6.2. Canonical business objects for v1

Only these are first-class in v1:

- `Customer`
- `Product`
- `PriceList`
- `Quote`
- `QuoteLine`
- `SalesOrder`
- `InventoryPosition`
- `Approval`
- `Company`

Other object types may be represented as `CustomBusinessObject` without write capabilities.

## 6.3. Canonical capabilities for v1

```text
system.connection.test
system.schema.discover
system.fingerprint.generate
events.pull

customer.resolve
customer.read

product.resolve
product.read

pricing.pricelist.resolve
pricing.quote.calculate

inventory.availability.check

sales.quote.read
sales.quote.create_draft
sales.quote.update_draft
sales.order.confirm

approval.request
approval.read
```

## 6.4. Capability naming

Format:

```text
<domain>.<resource>.<verb>
```

Examples:

```text
sales.quote.create_draft
inventory.availability.check
customer.resolve
```

Prohibited public names:

```text
odoo.execute_kw
odoo.sale_order_create
model.write
call_method
raw_http
```

## 6.5. Canonical operation contract

```python
class CanonicalOperation(BaseModel):
    operation_id: str
    tenant_id: str
    connection_id: str
    capability: str
    capability_version: str
    actor_id: str
    process_version_id: str | None
    skill_version_id: str | None
    input: dict[str, Any]
    object_refs: list[CanonicalObjectRef]
    idempotency_key: str | None
    requested_at: datetime
```

## 6.6. Canonical result contract

```python
class CanonicalOperationResult(BaseModel):
    operation_id: str
    status: Literal[
        "completed",
        "blocked",
        "needs_clarification",
        "needs_approval",
        "failed",
        "unknown"
    ]
    outputs: dict[str, Any]
    object_refs: list[CanonicalObjectRef]
    native_operation_refs: list[str]
    postconditions: list[PostconditionResult]
    evidence_pack_id: str
```

---

# 7. Object-centric event model

## 7.1. Standard alignment

The internal event model must be compatible with OCEL 2.0 concepts:

- events;
- objects;
- event-object relationships;
- object-object relationships;
- event attributes;
- object attributes that change over time;
- typed relations.

The database schema does not have to be a direct copy of the OCEL SQLite schema.

Required:

- import OCEL 2.0 JSON;
- export the v1 dataset as OCEL 2.0 JSON;
- preserve stable event and object identity;
- document any ERPGuard-specific extension.

## 7.2. `BusinessEvent`

```python
class BusinessEvent(BaseModel):
    event_id: str
    tenant_id: str
    connection_id: str
    event_type: str
    occurred_at: datetime
    ingested_at: datetime
    actor_ref: ActorRef | None
    object_relations: list[EventObjectRelation]
    attributes: dict[str, JSONValue]
    source_ref: NativeSourceRef
    correlation_id: str | None
    causation_id: str | None
    process_hint: str | None
    schema_version: str = "1.0"
```

## 7.3. Native source reference

```python
class NativeSourceRef(BaseModel):
    connector_id: str
    connector_version: str
    native_event_id: str | None
    native_model: str | None
    native_record_id: str | None
    extraction_mode: Literal[
        "api",
        "bridge_webhook",
        "polling",
        "import",
        "fixture",
        "derived"
    ]
```

## 7.4. Quote-to-Order v1 events

Required canonical event types:

```text
quote.requested
customer.resolution.started
customer.resolved
customer.resolution.ambiguous
product.resolved
product.resolution.failed
pricelist.resolved
inventory.checked
margin.validated
approval.requested
approval.approved
approval.rejected
quote.created
quote.updated
quote.sent
order.confirmation.requested
order.confirmed
order.confirmation.blocked
order.cancelled
execution.failed
execution.compensated
```

## 7.5. Event immutability

A stored event is immutable.

Corrections use:

- superseding events;
- redaction metadata;
- tombstone metadata for legal deletion;
- no silent update.

## 7.6. Event ingestion idempotency

Natural key:

```text
tenant_id
+ connection_id
+ connector_id
+ native_event_id
+ event_type
```

If a native event ID is unavailable:

```text
stable hash(
  source model,
  source record,
  event type,
  source write timestamp,
  relevant attributes
)
```

## 7.7. Projection

The mining engine must not assume a single case ID.

For v1 it may create a Quote-to-Order projection keyed primarily by quote/order object, while preserving links to customer, product and approval objects.

---

# 8. Connector SDK v2

## 8.1. Connector plugin contract

```python
class ConnectorPlugin(Protocol):
    metadata: ConnectorMetadata

    def auth_schemas(self) -> list[AuthSchema]: ...
    def capability_definitions(self) -> list[CapabilityDefinition]: ...

    async def test_connection(
        self,
        context: ConnectorContext
    ) -> ConnectionTestResult: ...

    async def discover_schema(
        self,
        context: ConnectorContext
    ) -> DiscoveredSystemSchema: ...

    async def fingerprint(
        self,
        context: ConnectorContext
    ) -> SystemFingerprint: ...

    async def pull_events(
        self,
        context: ConnectorContext,
        cursor: IngestionCursor | None,
        request: PullEventsRequest
    ) -> EventBatch: ...

    async def read_objects(
        self,
        context: ConnectorContext,
        request: ReadObjectsRequest
    ) -> ReadObjectsResult: ...

    async def plan_capability(
        self,
        context: ConnectorContext,
        operation: CanonicalOperation
    ) -> NativeExecutionPlan: ...

    async def execute_capability(
        self,
        context: ConnectorContext,
        plan: NativeExecutionPlan,
        permit: ExecutionPermit
    ) -> NativeExecutionResult: ...

    async def verify_execution(
        self,
        context: ConnectorContext,
        operation: CanonicalOperation,
        result: NativeExecutionResult
    ) -> VerificationResult: ...
```

## 8.2. Optional interfaces

```python
class SupportsWebhooks(Protocol): ...
class SupportsChangeDataCapture(Protocol): ...
class SupportsCompensation(Protocol): ...
class SupportsNativeTransactions(Protocol): ...
class SupportsSchemaDiff(Protocol): ...
```

## 8.3. Connector metadata

```python
class ConnectorMetadata(BaseModel):
    connector_id: str
    package_name: str
    version: str
    display_name: str
    vendor: str
    system_types: list[str]
    supported_versions: list[str]
    plugin_api_version: str
    features: ConnectorFeatures
```

## 8.4. Connector features

```python
class ConnectorFeatures(BaseModel):
    event_source: bool
    object_read: bool
    schema_discovery: bool
    permission_inspection: bool
    fingerprint: bool
    controlled_write: bool
    verification: bool
    compensation: bool
    webhooks: bool
```

## 8.5. Plugin discovery

Use Python entry points.

```toml
[project.entry-points."erpguard.connectors"]
odoo = "erpguard.connectors.odoo.plugin:OdooConnectorPlugin"
fake = "erpguard.connectors.fake.plugin:FakeConnectorPlugin"
ocel = "erpguard.connectors.ocel.plugin:OCELConnectorPlugin"
```

Discovery:

```python
from importlib.metadata import entry_points

plugins = entry_points(group="erpguard.connectors")
```

## 8.6. Connector package separation

During TFM all connectors may live in the monorepo.

The SDK must nevertheless support future independent packages:

```text
erpguard-connector-odoo
erpguard-connector-salesforce
erpguard-connector-shopify
```

## 8.7. Contract Test Kit

Every connector must pass:

- metadata validation;
- plugin API compatibility;
- authentication schema validation;
- no-secret serialization;
- connection test behavior;
- stable fingerprint generation;
- event normalization;
- ingestion cursor idempotency;
- object identity stability;
- declared capability completeness;
- plan/execute separation;
- permit enforcement;
- unknown capability block;
- native error normalization;
- postcondition verification;
- tenant isolation;
- idempotent retry behavior;
- no raw credential in evidence.

Command:

```bash
pytest tests/contract/connectors -q
```

## 8.8. Legacy adapter compatibility

The current `ERPAdapterContract` is not deleted immediately.

Create:

```text
erpguard/connectors/sdk/legacy_adapter_shim.py
```

It maps legacy read-only operations into Connector SDK v2.

Rules:

- legacy generic write operations remain blocked;
- the shim is read-only;
- new writes must use semantic capabilities;
- mark shim deprecated after Odoo Connector v2 passes E2E.

---

# 9. Odoo connector

## 9.1. Transport strategy

For Odoo 19:

1. Prefer External JSON-2 for external model API access.
2. Use a custom `erpguard_bridge` Odoo addon for atomic domain capabilities and clean event emission.
3. Keep legacy XML-RPC support behind an explicit compatibility mode for existing staging environments.
4. Do not allow the core to depend on a transport.

Deployment note:

- Odoo's documented external model APIs are plan/deployment dependent.
- The onboarding UI must detect and explain when external API access is unavailable.
- The bridge addon is the preferred path for controlled self-hosted/Odoo.sh staging deployments because it can expose narrow atomic capabilities without publishing a generic external model tool.
- The connector must never assume that every Odoo 19 database exposes the same models, methods, fields or permissions; discovery and fingerprinting are mandatory.

## 9.2. Reason for the bridge addon

Multiple external API calls may not share one transaction.

Critical compound operations should be exposed as atomic business methods in Odoo:

```text
erpguard.bridge.create_quotation_draft
erpguard.bridge.confirm_sales_order
erpguard.bridge.get_quote_to_order_events
erpguard.bridge.fingerprint
```

The bridge must:

- enforce the Odoo user’s native permissions;
- validate allowed fields;
- validate company;
- accept correlation ID;
- accept idempotency key;
- emit canonical-ready event payloads;
- return postcondition-relevant data;
- avoid generic model/method passthrough.

## 9.3. Odoo addon structure

```text
odoo_addons/
└── erpguard_bridge/
    ├── __init__.py
    ├── __manifest__.py
    ├── controllers/
    │   └── webhook.py
    ├── models/
    │   ├── erpguard_event.py
    │   ├── sale_order.py
    │   └── res_config_settings.py
    ├── security/
    │   ├── ir.model.access.csv
    │   └── security.xml
    ├── data/
    │   └── cron.xml
    ├── views/
    │   └── settings_views.xml
    └── tests/
```

## 9.4. Odoo connection modes

```text
json2_external
bridge
legacy_xmlrpc
fixture
```

The connection fingerprint records the selected mode.

## 9.5. Odoo authentication

Supported in v1:

- Odoo API key;
- database header where required;
- bridge webhook signing secret;
- separate service user.

Prohibited:

- username/password stored as default;
- admin account requirement;
- credentials sent to LLM;
- API key in query string;
- plaintext credential in database.

## 9.6. Odoo schema discovery

Required objects:

- `res.partner`;
- `product.product`;
- `product.template`;
- `product.pricelist`;
- `sale.order`;
- `sale.order.line`;
- `stock.quant` or a bridge-level availability method;
- `res.company`;
- relevant custom fields.

Fingerprint includes:

- Odoo version;
- installed bridge version;
- company IDs;
- required model existence;
- required field names and types;
- custom mapping values;
- capabilities;
- user groups or derived permissions;
- connector version.

## 9.7. Odoo mappings

Mapping files:

```text
erpguard/connectors/odoo/mappings/
├── odoo19_core.yaml
├── quote_to_order.yaml
└── custom_mapping.schema.json
```

Example:

```yaml
canonical_object: Customer
native_model: res.partner
identity:
  native_id: id
fields:
  name: name
  tax_id: vat
  email: email
  active: active
```

## 9.8. Odoo Quote-to-Order capabilities

### `customer.resolve`

Reads:

- `res.partner`.

Resolution order:

1. exact tax ID;
2. exact external reference;
3. exact email where unique;
4. exact normalized name;
5. fuzzy name candidates.

A fuzzy match never authorizes a write automatically.

### `product.resolve`

Resolution order:

1. exact `default_code`;
2. exact barcode;
3. exact active name;
4. candidate list.

Variant ambiguity must be explicit.

### `pricing.pricelist.resolve`

Uses:

- partner property;
- company;
- currency;
- applicable price rules.

### `inventory.availability.check`

Returns:

- product;
- requested quantity;
- available quantity;
- forecast quantity where available;
- location/company context;
- timestamp.

### `sales.quote.create_draft`

Input:

```json
{
  "customer_ref": "...",
  "lines": [
    {
      "product_ref": "...",
      "quantity": 20
    }
  ],
  "client_reference": "...",
  "company_ref": "...",
  "currency": "EUR"
}
```

Allowed outcome:

- one `sale.order` in draft/sent quotation state;
- expected lines;
- no confirmation;
- no invoice;
- no delivery validation.

### `sales.order.confirm`

Risk R3.

Required:

- explicit approver;
- unexpired permit;
- unchanged critical state;
- staging environment;
- amount below configured TFM ceiling;
- no forbidden product/test marker;
- no active global kill switch.

## 9.9. Odoo postconditions

For quotation creation:

- quote exists;
- correct tenant/connection;
- correct Odoo company;
- correct customer;
- correct line count;
- correct products;
- correct quantities;
- expected currency;
- expected price list;
- totals are internally consistent;
- state is quotation/draft;
- no invoice created;
- no confirmed picking created;
- idempotency reference stored.

## 9.10. Odoo event extraction

Preferred:

- bridge event table + incremental cursor.

Fallback:

- polling `write_date` and deriving events.

Derived events must declare:

```text
source.extraction_mode = derived
```

Do not pretend derived historical events are native audit events.

---

# 10. Connection and secret architecture

## 10.1. Unified connection path

The repository must end with one public connection service.

Public API:

```text
POST /v1/connections
POST /v1/connections/{id}/test
POST /v1/connections/{id}/discover
POST /v1/connections/{id}/fingerprint
POST /v1/connections/{id}/rotate
POST /v1/connections/{id}/revoke
GET  /v1/connections/{id}
```

## 10.2. Secret provider interface

```python
class SecretProvider(Protocol):
    async def put(self, secret: SecretValue, metadata: SecretMetadata) -> SecretReference: ...
    async def get(self, reference: SecretReference, purpose: SecretAccessPurpose) -> SecretValue: ...
    async def rotate(self, reference: SecretReference, new_secret: SecretValue) -> SecretReference: ...
    async def revoke(self, reference: SecretReference) -> None: ...
```

Implementations:

- `EncryptedDatabaseSecretProvider` for local beta;
- `EnvironmentSecretProvider` for demo/dev;
- future `VaultSecretProvider`.

## 10.3. Local encryption

Use authenticated encryption.

The master key:

- comes from environment or external KMS;
- is never stored in the database;
- has version identifier;
- can be rotated.

## 10.4. Secret access

Only connector execution infrastructure may resolve a secret reference.

The resolved secret must never enter:

- domain objects;
- audit event attributes;
- Evidence Pack;
- LLM prompt;
- API response;
- exception message.

---

# 11. Identity, tenancy and authorization

## 11.1. Identity source

TFM minimum:

- local authentication with securely hashed passwords or an OIDC development provider;
- signed access tokens;
- server-side current user dependency.

Production roadmap:

- OIDC;
- SAML;
- SCIM.

## 11.2. Tenant rule

`tenant_id` is derived from authenticated membership.

Never accept authoritative `tenant_id` or `actor_id` from request JSON.

## 11.3. Roles

- `owner`;
- `admin`;
- `process_designer`;
- `operator`;
- `approver`;
- `auditor`;
- `connector_developer`;
- `service_agent`.

## 11.4. Permissions

Examples:

```text
connection.create
connection.read
connection.rotate
connection.revoke

event.ingest
event.export

process.create
process.branch
process.replay
process.approve
process.promote
process.rollback

skill.compile
skill.approve
skill.activate
skill.run

run.approve_r2
run.approve_r3
evidence.read
evidence.export
kill_switch.manage
```

## 11.5. Segregation of duties

For R3:

- requester cannot be sole approver;
- approval is bound to exact process/skill version, operation hash and expiry;
- approval cannot be reused.

---

# 12. Process definition and version control

## 12.1. Process definition

A process is a semantic graph, not a UI recording.

```python
class ProcessDefinition(BaseModel):
    process_id: str
    key: str
    name: str
    domain: str
    primary_object_type: str
    objective: str
    owner_role: str
```

## 12.2. Process version

```python
class ProcessVersion(BaseModel):
    process_version_id: str
    process_id: str
    semantic_version: str
    parent_version_id: str | None
    branch_name: str
    status: Literal[
        "draft",
        "candidate",
        "replay_validated",
        "shadow",
        "canary",
        "active",
        "rejected",
        "rolled_back",
        "deprecated"
    ]
    definition_hash: str
    created_by: str
    created_at: datetime
```

## 12.3. Process package

```text
processes/quote_to_order/
├── process.yaml
├── objects.yaml
├── events.yaml
├── decisions.yaml
├── invariants.yaml
├── metrics.yaml
├── policies.yaml
├── mappings/
│   └── odoo.yaml
├── fixtures/
└── tests/
```

## 12.4. `process.yaml`

```yaml
id: quote_to_order
version: 1.0.0
primary_object: Quote

start:
  event: quote.requested

nodes:
  - id: resolve_customer
    capability: customer.resolve
  - id: resolve_products
    capability: product.resolve
  - id: resolve_pricelist
    capability: pricing.pricelist.resolve
  - id: check_stock
    capability: inventory.availability.check
  - id: validate_margin
    decision: margin_policy
  - id: create_quote
    capability: sales.quote.create_draft
  - id: confirm_order
    capability: sales.order.confirm
```

## 12.5. Branching

A candidate begins as an immutable child of a baseline:

```text
quote_to_order@1.0.0
└── candidate/reduce-manual-review@2.0.0-rc1
```

## 12.6. Diff

Process diff must show:

- nodes added/removed;
- transition changes;
- policy changes;
- capability changes;
- risk changes;
- approval changes;
- input/output schema changes;
- metrics changes;
- tests changed;
- mapping changes.

---

# 13. Variant discovery

## 13.1. Purpose

Discover recurring execution paths from canonical events.

## 13.2. TFM algorithm

The TFM does not require a novel mining algorithm.

Implement:

1. Quote-to-Order case projection.
2. Ordered activity sequence per case.
3. Variant grouping by normalized sequence.
4. Count, frequency and duration.
5. Rework detection.
6. exception markers;
7. outcome statistics.
8. optional PM4Py-backed visualization.

## 13.3. Normalization

Normalize:

- repeated non-business UI events;
- duplicate ingestion;
- technical polling events;
- retry events;
- aliases.

Do not erase:

- approval loops;
- rejected decisions;
- corrections;
- cancellation;
- compensation;
- failures.

## 13.4. Variant model

```python
class ProcessVariant(BaseModel):
    variant_id: str
    process_id: str
    activity_sequence: list[str]
    case_count: int
    frequency: float
    median_duration_seconds: float
    rework_rate: float
    failure_rate: float
    manual_intervention_rate: float
    outcome_metrics: dict[str, float | None]
```

## 13.5. UI output

```text
7 variants discovered

Variant A — 48%
Resolve customer → Resolve products → Create quote
Median: 11m
Rework: 8.2%

Variant B — 31%
Resolve customer → Check history → Resolve products
→ Check stock → Create quote
Median: 8m
Rework: 2.1%
```

## 13.6. Candidate generation boundary

Variant discovery may suggest evidence.

It does not automatically decide that the most frequent or fastest variant is best.

---

# 14. Candidate generation

## 14.1. Candidate sources

- manually designed change;
- variant-derived recommendation;
- repeated correction pattern;
- new invariant;
- policy threshold adjustment;
- Record-to-Skill observation;
- LLM proposal grounded in structured evidence.

## 14.2. LLM boundary

The LLM receives:

- current process definition;
- variant summaries;
- selected examples;
- invariants;
- allowed capabilities;
- policy schema;
- target metrics.

The LLM does not receive:

- credentials;
- arbitrary native methods;
- permission to activate;
- full raw database;
- hidden system configuration.

## 14.3. Candidate output

Strict schema:

```python
class CandidateProposal(BaseModel):
    title: str
    rationale: list[EvidenceReference]
    changes: list[CandidateChange]
    expected_metric_effects: list[ExpectedMetricEffect]
    risks: list[CandidateRisk]
    required_tests: list[TestCaseDefinition]
    unresolved_questions: list[ClarificationQuestion]
```

## 14.4. Candidate activation

Candidate generation creates only:

```text
status = draft
```

It cannot:

- replay itself;
- approve itself;
- compile itself;
- activate itself.

---

# 15. Historical replay engine

## 15.1. Definition

Replay executes a process version over immutable historical case fixtures without writing to the source system.

## 15.2. Replay modes

- `recorded_state`: use only state captured at the historical point;
- `fixture_state`: use synthetic fixture snapshots;
- `current_readonly`: optional diagnostic, not valid as historical truth.

TFM evidence must use `recorded_state` or versioned fixtures.

## 15.3. Replay input

```python
class ReplayCase(BaseModel):
    case_id: str
    initial_state: dict[str, Any]
    events: list[BusinessEvent]
    expected_allowed_effects: list[ExpectedEffect]
    forbidden_effects: list[ExpectedEffect]
    expected_outcome: dict[str, Any]
    labels: list[str]
```

## 15.4. Replay execution

For each case:

1. load immutable candidate;
2. load fixture;
3. execute deterministic workflow;
4. replace connector writes with simulation;
5. evaluate decisions;
6. compare predicted effects;
7. evaluate invariants;
8. produce case result;
9. record trace hash.

## 15.5. Replay result

```python
class ReplayCaseResult(BaseModel):
    case_id: str
    status: str
    decision_trace: list[DecisionTrace]
    predicted_effects: list[PredictedEffect]
    safety_violations: list[Violation]
    regressions: list[Regression]
    metrics: dict[str, float | int | None]
    deterministic_trace_hash: str
```

## 15.6. Determinism

Same:

- process version;
- fixture;
- policy version;
- connector simulator version;

must produce the same trace hash.

## 15.7. No LLM runtime

Historical replay cannot invoke the LLM.

If a case requires ambiguity resolution not represented in the fixture, result:

```text
needs_clarification
```

## 15.8. Replay API

```text
POST /v1/processes/{process_id}/versions/{version_id}/replays
GET  /v1/replays/{replay_id}
GET  /v1/replays/{replay_id}/cases
GET  /v1/replays/{replay_id}/comparison
POST /v1/replays/{replay_id}/freeze
```

---

# 16. Regression detection

## 16.1. Regression categories

- new unsafe effect;
- newly incorrect entity resolution;
- duplicate creation;
- false block;
- missing approval;
- additional approval;
- postcondition failure;
- incompatible fingerprint;
- latency threshold breach;
- token increase;
- evidence incompleteness.

## 16.2. Severity

```text
critical
high
medium
low
informational
```

Critical examples:

- effect forbidden by policy;
- cross-tenant object;
- payment/accounting effect;
- confirmation without required approval;
- duplicate write.

## 16.3. Promotion blocker

Any unresolved critical regression blocks Proof of Improvement status `eligible`.

---

# 17. Proof of Improvement

## 17.1. Purpose

A candidate cannot advance because it “looks better”.

It must carry a structured Proof of Improvement.

## 17.2. Model

```python
class ProofOfImprovement(BaseModel):
    proof_id: str
    baseline_process_version_id: str
    candidate_process_version_id: str
    replay_run_id: str
    dataset_version: str
    benchmark_version: str
    metric_comparisons: list[MetricComparison]
    regressions: list[RegressionSummary]
    safety_summary: SafetySummary
    reproducibility_summary: ReproducibilitySummary
    evidence_refs: list[str]
    recommendation: Literal[
        "reject",
        "needs_changes",
        "eligible_for_shadow",
        "eligible_for_canary",
        "eligible_for_promotion"
    ]
    recommendation_basis: list[str]
    limitations: list[str]
    generated_at: datetime
    content_hash: str
```

## 17.3. Proof rules

TFM minimum eligibility for shadow:

- no unresolved critical regression;
- no increase in forbidden side effects;
- duplicate prevention rate meets threshold;
- evidence completeness meets threshold;
- deterministic replay repeatability passes;
- all required tests pass;
- human reviewer accepts limitations.

## 17.4. Proof immutability

A Proof of Improvement is immutable.

New data creates a new proof.

## 17.5. Proof UI

Show:

- baseline vs candidate;
- changed decisions;
- improvements;
- regressions;
- safety;
- dataset;
- limitations;
- recommendation;
- approve/reject.

---

# 18. Skill compiler v2

## 18.1. Input

- immutable process version;
- approved Proof of Improvement;
- connector capability definitions;
- fingerprint constraints;
- mappings;
- policies;
- invariants;
- tests.

## 18.2. Output package

```text
skills/quote_to_order_odoo/
├── skill.yaml
├── process_ref.yaml
├── workflow.yaml
├── capability_manifest.yaml
├── policy_bundle.yaml
├── guards.yaml
├── invariants.yaml
├── permissions.yaml
├── fingerprint_requirements.yaml
├── postconditions.yaml
├── compensation.yaml
├── input_schema.json
├── output_schema.json
├── proof_of_improvement.json
├── audit_config.yaml
├── examples/
└── tests/
```

## 18.3. Compilation validation

- all capabilities exist;
- connector supports required features;
- schemas validate;
- no raw native method;
- no arbitrary code;
- policy references resolve;
- postconditions exist for writes;
- idempotency strategy exists for writes;
- fingerprint requirements exist;
- proof is acceptable;
- tests pass;
- package hash is generated.

## 18.4. Skill lifecycle v2

```text
draft
→ compiled
→ validated
→ replay_proven
→ approved
→ shadow
→ canary
→ active
→ rolled_back
→ deprecated
```

## 18.5. Legacy skill mapping

Current skills may remain `legacy`.

They cannot enter shadow/canary without recompilation into v2.

---

# 19. ERPGuard execution runtime v2

## 19.1. Execution sequence

```text
Authenticated request
→ resolve active process/skill
→ validate input
→ build ActionPlan
→ resolve entities
→ read current state
→ preflight
→ risk classification
→ approval check
→ issue ExecutionPermit
→ connector plans native operations
→ connector verifies permit independently
→ connector executes
→ postcondition verification
→ Evidence Pack
```

## 19.2. ActionPlan

Must include:

- actor;
- process version;
- skill version;
- connector;
- exact canonical capabilities;
- resolved objects;
- predicted effects;
- ambiguities;
- risk;
- approvals;
- idempotency;
- snapshot hash.

## 19.3. Execution Permit

Required fields:

```python
class ExecutionPermit(BaseModel):
    permit_id: str
    tenant_id: str
    actor_id: str
    connection_id: str
    connector_id: str
    process_version_id: str
    skill_version_id: str
    operation_hash: str
    native_plan_hash: str
    state_snapshot_hash: str
    capability_allowlist: list[str]
    approval_ids: list[str]
    idempotency_key: str
    issued_at: datetime
    expires_at: datetime
    single_use: bool = True
    signature: str
```

## 19.4. Permit verification

Connector execution rejects:

- wrong tenant;
- wrong connection;
- wrong capability;
- altered plan;
- altered state;
- expired permit;
- reused permit;
- revoked permit;
- inactive skill;
- kill switch;
- missing approval;
- unsupported fingerprint.

## 19.5. Idempotency

For quote creation:

```text
tenant
+ connection
+ skill version
+ normalized customer
+ normalized lines
+ client reference
+ request correlation
```

## 19.6. Unknown state

A timeout after write returns:

```text
status = unknown
```

Then verification runs.

Never retry a write blindly.

## 19.7. Compensation

For a draft quotation:

- cancel or delete only if still draft and unchanged;
- preserve evidence;
- never claim universal rollback.

---

# 20. Shadow mode

## 20.1. Definition

Shadow mode receives live requests/events but does not produce source-system effects.

It compares:

- active process decision;
- candidate process decision;
- actual observed outcome where available.

## 20.2. TFM implementation

Required:

- shadow evaluation on staged or replayed incoming cases;
- no production routing required;
- at least one live/staging demonstration.

## 20.3. Shadow result

```python
class ShadowCaseResult(BaseModel):
    case_id: str
    active_decision: dict[str, Any]
    candidate_decision: dict[str, Any]
    agreement: bool
    difference_categories: list[str]
    actual_outcome: dict[str, Any] | None
    reviewer_label: str | None
```

## 20.4. Promotion threshold

Configurable, not hard-coded globally.

---

# 21. Canary and promotion

## 21.1. Canary scope

Possible selectors:

- percentage;
- company;
- user;
- customer segment;
- amount ceiling;
- product category;
- explicit allowlist.

## 21.2. TFM boundary

Canary may be implemented as a staging experiment.

No requirement to route real production orders.

## 21.3. Promotion

Requires:

- acceptable Proof of Improvement;
- shadow/canary evidence where required;
- human approval;
- no active critical regression;
- compatible fingerprint;
- rollback target.

## 21.4. Rollback

Rollback changes the active process pointer.

It does not delete the failed version.

---

# 22. Web application

## 22.1. Technology

Recommended:

- React;
- TypeScript;
- Vite;
- generated API client;
- component tests;
- no mandatory heavy design system.

Alternative frameworks require ADR.

## 22.2. Primary navigation

```text
Overview
Connections
Processes
Replays
Deployments
Runs
Evidence
Benchmarks
Settings
```

## 22.3. Required screens

### Onboarding

- create organization;
- connect Odoo;
- test;
- fingerprint;
- install Quote-to-Order pack.

### Process Overview

- current version;
- branch graph;
- event volume;
- variants;
- current deployment;
- key metrics.

### Variant Explorer

- variants;
- counts;
- durations;
- rework;
- failure;
- selected case trace.

### Candidate Builder

- baseline;
- proposed changes;
- evidence;
- risk;
- unresolved questions;
- generated tests.

### Replay

- dataset selector;
- run progress;
- baseline/candidate comparison;
- case-level differences;
- regressions.

### Proof of Improvement

- summary;
- safety;
- metrics;
- regressions;
- limitations;
- eligibility;
- reviewer decision.

### Skill Package

- compiled artifacts;
- capabilities;
- reads/writes;
- approvals;
- postconditions;
- fingerprint constraints.

### Run

- request;
- action plan;
- preview;
- approval;
- result;
- Odoo link/reference.

### Evidence

- timeline;
- actor;
- process/skill;
- permit;
- native operations;
- verification;
- export.

## 22.4. Old dashboard

`GET /demo` becomes:

- a legacy route;
- clearly labeled;
- excluded from public screenshots;
- eventually redirect to `/legacy/demo`.

---

# 23. Public API v1

Keep the public API compact.

## 23.1. Identity

```text
GET /v1/me
GET /v1/organizations/current
GET /v1/permissions
```

## 23.2. Connectors

```text
GET /v1/connector-definitions
GET /v1/connector-definitions/{connector_id}
POST /v1/connections
POST /v1/connections/{connection_id}/test
POST /v1/connections/{connection_id}/discover
POST /v1/connections/{connection_id}/fingerprint
POST /v1/connections/{connection_id}/rotate
POST /v1/connections/{connection_id}/revoke
```

## 23.3. Events

```text
POST /v1/connections/{connection_id}/ingestions
GET /v1/ingestions/{ingestion_id}
GET /v1/events
POST /v1/events/import/ocel
GET /v1/events/export/ocel
```

## 23.4. Processes

```text
GET /v1/processes
POST /v1/processes
GET /v1/processes/{process_id}
POST /v1/processes/{process_id}/versions
GET /v1/processes/{process_id}/versions/{version_id}
GET /v1/processes/{process_id}/versions/{version_id}/diff
POST /v1/processes/{process_id}/discover-variants
```

## 23.5. Candidates and replay

```text
POST /v1/processes/{process_id}/candidates
POST /v1/processes/{process_id}/candidates/{candidate_id}/replays
GET /v1/replays/{replay_id}
GET /v1/replays/{replay_id}/comparison
POST /v1/replays/{replay_id}/proofs
GET /v1/proofs/{proof_id}
```

## 23.6. Compilation and deployment

```text
POST /v1/candidates/{candidate_id}/compile
GET /v1/skills/{skill_id}/versions/{version_id}
POST /v1/skills/{skill_id}/versions/{version_id}/approve
POST /v1/deployments/shadow
POST /v1/deployments/canary
POST /v1/deployments/{deployment_id}/promote
POST /v1/deployments/{deployment_id}/rollback
```

## 23.7. Runs

```text
POST /v1/runs/plan
GET /v1/runs/{run_id}
POST /v1/runs/{run_id}/approve
POST /v1/runs/{run_id}/execute
GET /v1/runs/{run_id}/evidence
POST /v1/runs/{run_id}/compensate
```

## 23.8. Benchmarks

```text
POST /v1/benchmarks/runs
GET /v1/benchmarks/runs/{run_id}
GET /v1/benchmarks/runs/{run_id}/report
```

## 23.9. API deprecation

Legacy APIs:

- remain available under `/legacy` or feature flag;
- return deprecation headers;
- are not documented as primary API;
- cannot gain new features.

---

# 24. Persistence and migrations

## 24.1. Database

- PostgreSQL for application/demo deployment.
- SQLite only for unit tests and minimal local compatibility.
- Alembic for all new schema changes.

## 24.2. Split models

New models must be grouped:

```text
erpguard/infrastructure/persistence/models/
├── identity.py
├── connections.py
├── events.py
├── processes.py
├── mining.py
├── evolution.py
├── skills.py
├── execution.py
└── evidence.py
```

`erpguard/db/models.py` becomes a compatibility import aggregator before eventual archival.

## 24.3. Repository pattern

Prefer explicit repositories per aggregate or SQLAlchemy services.

No new functions in `erpguard/db/repositories.py` unless required for legacy compatibility.

## 24.4. Migrations

Every phase that changes persistence must:

- generate migration;
- test upgrade from baseline fixture;
- test downgrade where practical;
- test clean database;
- update schema diagram.

---

# 25. Queues, concurrency and workers

## 25.1. Synchronous operations

- connection test;
- simple reads;
- plan;
- approval;
- small execution.

## 25.2. Background jobs

- event ingestion;
- variant discovery;
- replay;
- benchmark;
- export;
- large evidence pack creation.

Use a worker abstraction.

TFM implementation may use:

- Redis + RQ/Celery/Arq;
- or a database-backed worker with an ADR.

## 25.3. Locks

Required locks:

- ingestion cursor;
- process promotion;
- permit consumption;
- idempotency key;
- compensation.

---

# 26. Security model

## 26.1. Threats

- direct prompt injection;
- indirect prompt injection in ERP data;
- raw tool escalation;
- cross-tenant access;
- entity confusion;
- stale approval;
- permit reuse;
- replay dataset poisoning;
- event tampering;
- process version tampering;
- connector package compromise;
- credential exposure;
- TOCTOU;
- duplicate writes;
- evidence redaction failure;
- malicious process candidate;
- unsafe LLM-generated rule;
- dependency compromise.

## 26.2. Mandatory controls

- server-derived identity;
- RBAC;
- tenant filters;
- secret provider;
- strict schemas;
- allowlisted capabilities;
- signed single-use permits;
- immutable versions;
- approval binding;
- idempotency;
- current-state revalidation;
- kill switch;
- package hashing;
- evidence integrity;
- dependency lock;
- secret scanning;
- SAST;
- connector contract tests;
- no arbitrary expression evaluation;
- untrusted-data boundary for ERP text.

## 26.3. LLM prompt boundary

The prompt must delimit:

```text
SYSTEM POLICY
PROCESS DEFINITION
TRUSTED BUSINESS RULES
UNTRUSTED ERP DATA
USER REQUEST
```

ERP data never becomes system instruction.

## 26.4. Data protection

TFM datasets:

- synthetic or anonymized;
- documented generation;
- no real names, emails, tax IDs or addresses;
- no live credentials;
- redacted Evidence Packs.

---

# 27. LLM architecture

## 27.1. Allowed LLM uses

- candidate proposal;
- process explanation;
- clarification generation;
- mapping suggestion;
- test suggestion;
- repair proposal;
- evidence summary.

## 27.2. Prohibited LLM uses

- connector secret access;
- raw native method selection;
- runtime approval;
- permit signing;
- direct execution;
- silent policy mutation;
- replay decision generation;
- active version mutation.

## 27.3. Provider abstraction

```python
class StructuredLLM(Protocol):
    async def generate(
        self,
        *,
        task: str,
        schema: type[BaseModel],
        context: StructuredContext
    ) -> BaseModel: ...
```

## 27.4. Reproducibility metadata

Store:

- provider;
- model;
- model version where available;
- prompt template version;
- temperature;
- token usage;
- timestamp;
- schema version.

Never store secrets or unnecessary personal data.

---

# 28. ERPRiskBench Evolution Edition

## 28.1. Benchmark configurations

- fixed workflow;
- direct-tool agent;
- ERPGuard Evolution candidate.

## 28.2. Minimum cases

120 cases:

```text
30 valid complete
15 incomplete
15 ambiguous
10 missing entities
10 duplicate/retry
10 policy violations
10 high-risk actions
10 indirect prompt injections
5 state drift
5 identity/cross-tenant
```

## 28.3. Metrics

- task success;
- unsafe side-effect rate;
- correct block rate;
- false block rate;
- entity resolution accuracy;
- duplicate prevention;
- postcondition coverage;
- evidence completeness;
- deterministic repeatability;
- latency;
- token cost;
- human review load;
- regressions introduced;
- regressions prevented.

## 28.4. Benchmark invariants

- immutable dataset version;
- same initial state per comparison;
- same allowed tools documented;
- no intentionally broken baseline;
- all exclusions documented;
- raw results retained;
- report generated from data, not edited manually.

---

# 29. Synthetic Quote-to-Order dataset

## 29.1. Required fields

- request text;
- customer candidates;
- customer identity;
- products;
- product ambiguity;
- quantities;
- price list;
- discount;
- margin;
- stock;
- company;
- expected approvals;
- expected final state;
- known error labels;
- expected allowed effects;
- forbidden effects;
- event trace;
- outcome metrics.

## 29.2. Dataset generator

Create:

```text
scripts/generate_quote_to_order_dataset.py
```

Inputs:

- seed;
- case count;
- scenario distribution;
- currency;
- company count.

Output:

- versioned JSONL;
- OCEL JSON export;
- fixture snapshots;
- manifest with hash.

## 29.3. No fabricated claims

Synthetic outcomes may validate logic.

They cannot prove actual commercial conversion improvements.

---

# 30. Observability and evidence

## 30.1. Correlation

Every flow uses:

- `trace_id`;
- `correlation_id`;
- `causation_id`;
- `run_id`.

## 30.2. Structured logs

Required fields:

- timestamp;
- level;
- service;
- tenant hash/reference;
- actor reference;
- run;
- process version;
- skill version;
- connector;
- capability;
- status;
- duration;
- no secret.

## 30.3. Metrics

- ingested events;
- ingestion lag;
- variants discovered;
- replay throughput;
- regression count;
- Proof eligibility;
- shadow disagreement;
- canary outcomes;
- run latency;
- blocked operations;
- postcondition failures;
- connector errors.

## 30.4. Evidence Pack v2

Includes:

- request;
- actor;
- process version;
- Proof of Improvement;
- skill version;
- action plan;
- state snapshot hash;
- policies;
- approvals;
- permit;
- native operations redacted;
- postconditions;
- result;
- integrity record.

---

# 31. Installation

## 31.1. Demo

```bash
git clone <repository>
cd TFM
cp .env.example .env
docker compose -f docker-compose.demo.yml up --build
```

Must provide:

- web;
- API;
- worker;
- PostgreSQL;
- Fake ERP;
- seeded dataset;
- sample process;
- sample replay;
- no external credentials.

## 31.2. Odoo staging

```bash
docker compose up --build
python scripts/create_admin.py
python scripts/install_odoo_connector.py
```

Then:

1. install `erpguard_bridge` in Odoo staging;
2. create Odoo service user;
3. create API key;
4. connect;
5. test;
6. fingerprint;
7. ingest;
8. run read-only smoke;
9. enable quotation draft capability.

## 31.3. Clean-install acceptance

From an empty machine:

```bash
docker compose -f docker-compose.demo.yml up --build
python scripts/validate_demo_install.py
```

Target:

- application healthy;
- demo seeded;
- variant discovery works;
- replay works;
- Proof generated;
- skill compiled;
- Fake execution works.

---

# 32. CI/CD

## 32.1. Pull request pipeline

- formatting;
- lint;
- type check;
- unit tests;
- contract tests;
- integration tests;
- security tests;
- secret scan;
- dependency scan;
- migration test;
- build Python package;
- build web;
- build containers;
- benchmark smoke;
- docs link check.

## 32.2. Nightly

- full benchmark;
- Odoo staging E2E;
- deterministic replay repeat;
- connector contract suite;
- backup/restore;
- migration from release baseline;
- container scan.

## 32.3. Release gate

Block release if:

- version mismatch;
- red CI;
- no benchmark artifact;
- no SBOM;
- secret found;
- clean install fails;
- demo path fails;
- current/simulated matrix missing;
- unresolved critical regression.

---

# 33. Current-to-target migration map

## 33.1. Preserve directly

| Current area | Target |
|---|---|
| `erpguard/core/preflight.py` | ERPGuard preflight service |
| `erpguard/core/risk_engine.py` | risk engine |
| `erpguard/policies/` | policy bundles |
| `erpguard/invariants/` | invariant library |
| canonical objects | canonical domain seed |
| Skill Registry | Skill Registry v2 |
| recording sessions | evidence source / Record-to-Skill |
| Fake ERP | FakeConnector and deterministic test system |
| evidence packs | Evidence Pack v2 |
| approval pipeline | unified approvals |
| kill switches | runtime safety |

## 33.2. Wrap then replace

| Current area | Migration |
|---|---|
| `erpguard/product/erp_adapter_contract.py` | Connector SDK legacy shim, then deprecate |
| `erpguard/adapters/odoo/readonly_client.py` | Odoo transport compatibility implementation |
| connection APIs | unified Connection service |
| agent candidate pipeline | Candidate application services |
| operator action plans | ActionPlan v2 |
| step tokens | signed ExecutionPermit |
| Fake ERP execution | deterministic runtime v2 |
| semantic discovery | skill/process discovery after v1 |

## 33.3. Archive

| Current area | Action |
|---|---|
| sprint-by-sprint specs | `docs/archive/sprints/` |
| old release evidence | keep under versioned archive |
| monolithic demo | legacy route |
| placeholder connector catalog | replace with real plugin registry |
| placeholder OAuth simulations | archive or clearly label fixture |
| visual Sprint 80–83 experiments | retain as research archive; not core TFM path |

## 33.4. Do not delete before replacement

- database model classes used by current tests;
- old APIs used by clean-install validator;
- Fake ERP recording flows;
- evidence artifacts;
- Odoo read-only path.

---

# 34. Implementation phases

Every phase is independently releasable.

## Phase 0 — Baseline freeze

### Goal

Create a reproducible baseline before migration.

### Work

- tag baseline commit;
- record actual full test results;
- record skipped tests;
- create architecture inventory;
- create public/simulated/real capability matrix;
- add this spec to `docs/specs/84_erpguard_evolution_master_spec.md`;
- create ADR-0001.

### Files

```text
docs/specs/84_erpguard_evolution_master_spec.md
docs/architecture/current_inventory.md
docs/architecture/capability_reality_matrix.md
docs/adr/0001-erpguard-evolution.md
```

### Exit criteria

- clean install succeeds;
- baseline tests documented;
- no runtime behavior changed.

---

## Phase 1 — Project hygiene and version convergence

### Goal

Make versions, packaging and quality gates truthful.

### Work

- choose one version;
- add `uv.lock`;
- add formatting/lint/type tooling;
- add CI;
- add license/community files;
- create deprecation policy;
- separate public and legacy docs.

### Exit criteria

- version matches API, package and README;
- CI green;
- editable and Docker installs work.

---

## Phase 2 — Database migrations and bounded persistence

### Goal

Introduce Alembic and stop expanding monoliths.

### Work

- add Alembic;
- create baseline migration;
- create new model packages;
- add compatibility imports;
- implement migration tests.

### Exit criteria

- existing database upgrades;
- clean PostgreSQL starts;
- full tests pass;
- no new model placed directly in old monolith.

---

## Phase 3 — Identity and tenant enforcement

### Goal

Make actor and tenant trustworthy.

### Work

- users, memberships, roles;
- authentication;
- current-user dependency;
- tenant filters;
- server-derived actor;
- RBAC;
- security tests.

### Exit criteria

- cross-tenant tests pass;
- unauthenticated mutations fail;
- request-supplied actor/tenant cannot override identity.

---

## Phase 4 — Unified connections and real secret provider

### Goal

Replace duplicated connection paths.

### Work

- Connection aggregate;
- SecretProvider;
- encrypted local provider;
- unified API;
- migration from current connection records;
- credential redaction tests.

### Exit criteria

- one public connection API;
- real Odoo connection test;
- no plaintext secret;
- old path flagged deprecated.

---

## Phase 5 — Connector SDK v2

### Goal

Make Odoo a plugin, not the core.

### Work

- ConnectorPlugin protocol;
- metadata;
- capabilities;
- plugin registry;
- entry point discovery;
- contract test kit;
- legacy adapter shim;
- FakeConnector;
- ConnectorTemplate.

### Exit criteria

- FakeConnector discovered via entry point;
- contract tests pass;
- domain imports no Odoo module.

---

## Phase 6 — Canonical events and OCEL import/export

### Goal

Create the operational data substrate.

### Work

- event/object models;
- ingestion cursor;
- idempotent storage;
- OCEL JSON import;
- OCEL JSON export;
- Fake event generator;
- event API.

### Exit criteria

- same batch imported twice creates no duplicate;
- export/import round trip passes;
- tenant isolation passes.

---

## Phase 7 — Odoo Connector v2 read path

### Goal

Deliver real Odoo discovery, fingerprint and reads.

### Work

- JSON-2 transport;
- legacy compatibility transport;
- schema discovery;
- permissions/capabilities;
- fingerprint;
- customer/product/quote reads;
- contract tests;
- Odoo staging integration.

### Exit criteria

- live read-only smoke;
- fingerprint stable;
- credentials redacted;
- no write capability yet.

---

## Phase 8 — Odoo bridge and event ingestion

### Goal

Generate clean Quote-to-Order events.

### Work

- bridge addon;
- event table/webhook/polling;
- correlation IDs;
- event normalization;
- ingestion cursor;
- historical/synthetic labeling.

### Exit criteria

- Odoo events appear canonically;
- no duplicate on retry;
- bridge tests pass.

---

## Phase 9 — Quote-to-Order process package

### Goal

Define baseline process v1.

### Work

- process YAML;
- objects/events/decisions;
- metrics;
- policies;
- fixtures;
- validation;
- process registry/versioning.

### Exit criteria

- immutable v1 stored;
- process diff works;
- invalid definitions blocked.

---

## Phase 10 — Variant discovery

### Goal

Show actual process variants.

### Work

- case projection;
- sequence normalization;
- variant grouping;
- metrics;
- API;
- first web visualization.

### Exit criteria

- known fixture variants discovered exactly;
- counts/durations correct;
- selected case trace inspectable.

---

## Phase 11 — Candidate branching

### Goal

Create process candidate v2.

### Work

- branch model;
- candidate changes;
- manual builder;
- structured optional LLM proposal;
- process diff;
- candidate tests.

### Exit criteria

- candidate immutable after submission;
- evidence references valid;
- no activation path.

---

## Phase 12 — Historical replay

### Goal

Execute baseline and candidate against the same dataset.

### Work

- replay dataset;
- deterministic engine;
- simulated connector effects;
- trace hashes;
- comparison;
- APIs;
- UI.

### Exit criteria

- repeatability passes;
- no LLM used;
- no source ERP write;
- case-level results available.

---

## Phase 13 — Regression engine and Proof of Improvement

### Goal

Turn replay into a reviewable gate.

### Work

- regression categories;
- severity;
- metric comparisons;
- Proof model;
- eligibility rules;
- integrity hash;
- reviewer decision.

### Exit criteria

- critical regression blocks;
- proof references exact replay/dataset;
- proof immutable.

---

## Phase 14 — Process-to-Skill compiler v2

### Goal

Compile proven candidate into governed skill.

### Work

- skill package v2;
- capability manifest;
- fingerprint requirements;
- postconditions;
- compensation;
- proof attachment;
- compilation tests.

### Exit criteria

- raw native methods rejected;
- missing proof rejected;
- package hash reproducible;
- skill stored immutable.

---

## Phase 15 — Execution Permit runtime

### Goal

Replace weak confirmation tokens with enforceable permits.

### Work

- ActionPlan v2;
- snapshot hash;
- signed permit;
- one-use store;
- expiry;
- approval binding;
- kill switch;
- connector verification.

### Exit criteria

- altered, expired and reused permits fail;
- approval reuse fails;
- FakeConnector E2E passes.

---

## Phase 16 — Real quotation draft

### Goal

Close the first real business write.

### Work

- `sales.quote.create_draft`;
- atomic bridge method;
- idempotency;
- preflight;
- permit;
- real staging write;
- postconditions;
- compensation;
- Evidence Pack.

### Exit criteria

- one request creates one draft;
- retry creates no duplicate;
- no invoice/picking/confirmation;
- postconditions pass;
- evidence complete.

---

## Phase 17 — Governed confirmation

### Goal

Demonstrate R3 governance.

### Work

- confirm capability;
- independent approval;
- state revalidation;
- staging ceiling;
- permit;
- verification;
- cleanup.

### Exit criteria

Either:

- safe staging confirmation works;

or:

- explicit correct block is documented.

No fake success.

---

## Phase 18 — Shadow mode

### Goal

Compare candidate decisions without effects.

### Work

- shadow deployment;
- incoming case evaluation;
- decision comparison;
- reviewer labels;
- dashboard.

### Exit criteria

- candidate never writes;
- differences stored;
- selected example demonstrated.

---

## Phase 19 — Canary/promotion/rollback

### Goal

Complete process version CI/CD lifecycle.

### Work

- scoped deployment;
- metrics;
- promotion decision;
- active pointer;
- rollback;
- audit.

### TFM minimum

Staging-only canary is acceptable.

### Exit criteria

- promotion needs approval;
- rollback restores previous active version;
- all versions retained.

---

## Phase 20 — ERPRiskBench and experiments

### Goal

Generate TFM evidence.

### Work

- frozen dataset;
- three configurations;
- repeated runs;
- metrics;
- raw results;
- plots;
- statistical summaries;
- limitations.

### Exit criteria

- benchmark reproducible from command;
- report generated automatically;
- no manual result editing.

---

## Phase 21 — Product web experience

### Goal

Replace the engineering demo with a business narrative.

### Work

- onboarding;
- process overview;
- variants;
- replay;
- proof;
- run;
- evidence;
- responsive layout;
- Spanish copy.

### Exit criteria

A new user can:

```text
connect
→ ingest
→ inspect variants
→ replay candidate
→ inspect proof
→ compile
→ execute
```

without touching YAML or IDs.

---

## Phase 22 — TFM and public release freeze

### Goal

Produce immutable delivery.

### Work

- final tag;
- memory;
- annexes;
- 5-minute video;
- 90-second public demo;
- README;
- security docs;
- release notes;
- ZIP;
- permission verification.

### Exit criteria

- no feature work after freeze;
- links tested;
- repository access tested;
- submission package verified.

---

# 35. Test strategy

## 35.1. Unit

- domain validation;
- risk;
- policies;
- event normalization;
- variants;
- replay;
- regressions;
- proofs;
- permit signing;
- idempotency.

## 35.2. Contract

- connectors;
- process packages;
- skill packages;
- public API schemas.

## 35.3. Integration

- PostgreSQL;
- secret provider;
- connector registry;
- Odoo staging;
- worker;
- migrations.

## 35.4. E2E

### Demo E2E

```text
seed events
→ discover variants
→ create candidate
→ replay
→ generate proof
→ compile
→ run FakeConnector
```

### Odoo E2E

```text
connect
→ fingerprint
→ resolve entities
→ create quote draft
→ verify
→ evidence
→ retry
```

## 35.5. Security

- cross-tenant;
- actor spoofing;
- prompt injection;
- permit tampering;
- permit reuse;
- approval reuse;
- secret leakage;
- kill switch;
- state drift;
- malicious connector metadata;
- arbitrary capability.

## 35.6. Golden fixtures

Keep versioned golden outputs for:

- event normalization;
- variant discovery;
- replay comparison;
- Proof of Improvement;
- skill compilation;
- Evidence Pack.

Updates require explicit review.

---

# 36. Feature flags

```text
ERPGUARD_LEGACY_API_ENABLED=true
ERPGUARD_NEW_WEB_ENABLED=false
ERPGUARD_CONNECTOR_SDK_V2_ENABLED=false
ERPGUARD_EVENT_INGESTION_ENABLED=false
ERPGUARD_REPLAY_ENABLED=false
ERPGUARD_REAL_ODOO_READS_ENABLED=false
ERPGUARD_REAL_ODOO_QUOTE_DRAFT_ENABLED=false
ERPGUARD_REAL_ODOO_CONFIRM_ENABLED=false
ERPGUARD_SHADOW_ENABLED=false
ERPGUARD_CANARY_ENABLED=false
```

Defaults:

- real writes false;
- confirmation false;
- production mode false.

Flags are removed only after stable replacement.

---

# 37. Documentation

Required:

```text
docs/product/vision.md
docs/product/user_journeys.md
docs/architecture/overview.md
docs/architecture/current_inventory.md
docs/architecture/data_model.md
docs/architecture/connector_sdk.md
docs/architecture/event_model.md
docs/architecture/replay.md
docs/security/threat_model.md
docs/security/secrets.md
docs/connectors/odoo.md
docs/connectors/build_a_connector.md
docs/tfm/research_protocol.md
docs/tfm/dataset_card.md
docs/tfm/results.md
docs/tfm/limitations.md
```

## 37.1. Reality labels

Every documented capability has one:

- `real`;
- `staging_only`;
- `fixture`;
- `simulated`;
- `advisory`;
- `planned`;
- `blocked`.

---

# 38. README final structure

1. Product sentence.
2. Hero GIF.
3. The problem.
4. 90-second flow.
5. Measured benchmark.
6. Quickstart.
7. How it works.
8. Odoo connector.
9. Connector SDK.
10. Process package.
11. Proof of Improvement.
12. Security.
13. TFM/research.
14. Roadmap.
15. Contributing.
16. Citation.
17. License.

Prohibited:

- starting README with historical release candidates;
- test count as primary value;
- 80 endpoint list;
- unsupported “first/only” claims;
- simulated features presented as product.

---

# 39. TFM deliverables

## 39.1. Memory

Maximum 20 pages excluding cover, index and annexes.

Recommended allocation:

```text
1.0  Executive summary
1.5  Problem and objectives
2.0  State of the art
2.0  Research design
3.0  Architecture
2.5  Implementation
4.0  Experiment and results
1.5  Security and interpretability
1.0  Product value
1.0  Limitations and conclusions
0.5  Bibliography
```

## 39.2. Annexes

- full spec;
- schemas;
- connector SDK;
- process package;
- benchmark;
- raw results;
- prompts;
- Evidence Packs;
- threat model;
- installation;
- code/repository;
- data rights;
- GDPR analysis;
- test reports.

## 39.3. Five-minute video

```text
0:00–0:30 Problem
0:30–1:00 Thesis
1:00–1:25 Architecture
1:25–3:20 Demo
3:20–4:20 Results
4:20–5:00 Conclusions and limitations
```

## 39.4. Demo sequence

1. Connect Odoo.
2. Import/seed process history.
3. Show variants.
4. Compare baseline and candidate.
5. Run replay.
6. Show Proof of Improvement.
7. Compile skill.
8. Create real Odoo draft.
9. Show block/approval for confirmation.
10. Show Evidence Pack and duplicate prevention.

---

# 40. Release versions

```text
v0.13.0-rc1        historical ERPGuard candidate
v0.14.0            migration foundation
v0.15.0            Connector SDK + events
v0.16.0            process/version/mining
v0.17.0            replay/proof
v0.18.0            compiler/runtime v2
v0.19.0            Odoo quote vertical
v0.20.0            shadow/canary + benchmark
v1.0.0-tfm         immutable TFM release
v1.0.0-beta.1      public beta presentation
```

Versions may be consolidated, but must be consistent.

---

# 40.1. Delivery priority and calendar

The full architecture is the target product. The TFM critical path is narrower.

## P0 — Required before TFM submission

- Phase 0 baseline freeze.
- Phase 1 version/package truthfulness.
- Minimal Phase 2 migrations for new domains.
- Phase 3 identity/tenant minimum.
- Phase 4 unified connection and real secrets.
- Phase 5 Connector SDK v2.
- Phase 6 event model and OCEL import/export.
- Phase 7 Odoo read connector.
- Phase 9 Quote-to-Order package.
- Phase 10 variant discovery.
- Phase 11 candidate branch.
- Phase 12 replay.
- Phase 13 Proof of Improvement.
- Phase 14 process-to-skill compiler.
- Phase 15 permits.
- Phase 16 quotation draft.
- Phase 20 benchmark.
- Phase 21 minimal polished web journey.
- Phase 22 delivery.

## P1 — Complete only if P0 is stable

- Odoo bridge event emission.
- governed real confirmation;
- shadow evaluation;
- staging canary;
- rollback UI;
- advanced process mining visualizations.

## P2 — Post-TFM product roadmap

- production canary routing;
- hosted SaaS;
- independent connector packages;
- safe MCP gateway;
- additional business processes;
- second real enterprise connector;
- marketplace;
- enterprise SSO/SCIM;
- advanced causal/process simulation.

## Recommended calendar

### 27 July–2 August

- freeze baseline;
- add master spec;
- version/CI cleanup;
- create migration branch and issue set;
- define P0 dataset and process package.

### 3–9 August

- PostgreSQL/Alembic minimum;
- authentication/tenant enforcement;
- unified secrets and connections;
- Connector SDK v2 and FakeConnector.

### 10–16 August

- canonical event model;
- OCEL import/export;
- Odoo v2 read connector;
- Quote-to-Order process package.

### 17–23 August

- event fixtures/history;
- variant discovery;
- candidate branch;
- replay engine.

### 24–30 August

- regressions;
- Proof of Improvement;
- compiler v2;
- permit runtime;
- **feature freeze on 30 August**.

### 31 August–6 September

- real Odoo quotation draft;
- postconditions;
- idempotency;
- benchmark execution;
- fix only P0 defects.

### 7–13 September

- product UI;
- clean-install rehearsal;
- memory;
- annexes;
- video;
- public demo assets.

### 14–17 September

- final repeat of experiments;
- validate every number;
- tag release;
- export deliverables;
- verify repository permissions;
- submit before 17 September 2026 at 23:59.

## Scope fallback rule

If schedule pressure occurs, remove in this order:

1. real confirmation;
2. staging canary;
3. live bridge event streaming;
4. LLM candidate generation;
5. advanced frontend visualization.

Never remove:

- replay;
- Proof of Improvement;
- connector abstraction;
- real Odoo read;
- real quotation draft or an honestly documented failure;
- safety runtime;
- benchmark;
- evidence.

---

# 41. Definition of Done — TFM

- [ ] Baseline frozen.
- [ ] Full tests reproducible.
- [ ] PostgreSQL and migrations work.
- [ ] Authentication and tenant enforcement exist.
- [ ] Real secret provider exists.
- [ ] Connector SDK v2 exists.
- [ ] Fake, OCEL, Template and Odoo plugins exist.
- [ ] OCEL import/export works.
- [ ] Odoo read path works.
- [ ] Quote-to-Order process package exists.
- [ ] Variants are discovered.
- [ ] Candidate v2 exists.
- [ ] Historical replay is deterministic.
- [ ] Regressions are detected.
- [ ] Proof of Improvement is generated.
- [ ] Process-to-Skill compiler v2 works.
- [ ] Signed single-use permits work.
- [ ] Real Odoo quotation draft works in staging.
- [ ] Retry creates no duplicate.
- [ ] Postconditions are verified.
- [ ] Confirmation is safely executed or correctly blocked.
- [ ] Shadow mode is demonstrated.
- [ ] Benchmark compares three configurations.
- [ ] Raw results are stored.
- [ ] New web journey works.
- [ ] Clean install works.
- [ ] Memory is within 20 pages.
- [ ] Video is within 5 minutes.
- [ ] Annexes and repository permissions are correct.
- [ ] Tag `v1.0.0-tfm` exists.

---

# 42. Definition of Done — public beta

- [ ] Public-safe history scan completed.
- [ ] No secret in git history.
- [ ] Apache-2.0 or approved license.
- [ ] README hero demo.
- [ ] Docker demo works.
- [ ] Benchmark report shown.
- [ ] Connector template works.
- [ ] `good first issue` set exists.
- [ ] Security policy exists.
- [ ] SBOM exists.
- [ ] Release artifact exists.
- [ ] No unsupported uniqueness claim.
- [ ] Odoo limitations clearly stated.
- [ ] Telemetry is absent or opt-in.
- [ ] Repository renamed only after TFM delivery if desired.

---

# 43. AI completion protocol

When an implementation AI receives this spec, its first response must not begin coding immediately.

It must produce:

1. detected baseline commit;
2. current test result;
3. files relevant to Phase 0;
4. planned changes;
5. risks;
6. explicit non-goals;
7. verification commands.

After that it implements only the active phase.

## 43.1. Phase prompt template

```text
Implement Phase <N> from
docs/specs/84_erpguard_evolution_master_spec.md.

Rules:
- Inspect the current repository first.
- Do not implement later phases.
- Preserve existing behavior.
- Add tests before or with implementation.
- Do not add raw ERP execution.
- Run focused and full tests.
- Update AGENTS.md.
- Return changed files, test results, remaining limitations and exact next phase.
```

## 43.2. Completion report template

```text
Phase:
Commit/base:
Implemented:
Not implemented:
Files changed:
Migrations:
Tests:
Security checks:
Manual verification:
Reality labels:
Known limitations:
Next allowed phase:
```

---

# 44. First implementation epic

## Title

Converge current ERPGuard into ERPGuard Evolution without a rewrite.

## Outcome

A clean installation can:

```text
load canonical Quote-to-Order events
→ discover variants
→ branch a candidate
→ replay baseline and candidate
→ generate Proof of Improvement
→ compile a governed skill
→ create one real Odoo quotation draft
→ verify it
→ export evidence
```

## Explicit no-goals

- second enterprise connector;
- production accounting;
- unrestricted browser runtime;
- marketplace;
- generic MCP;
- autonomous promotion.

---

# 45. Final architectural invariant

> Odoo is the first deep connector, not the platform core.

> Process intelligence proposes changes, but evidence and humans govern promotion.

> The LLM may design, explain or repair; deterministic runtime executes repeated work.

> No side effect is authorized by a prompt. It is authorized by an immutable skill version, policy decision, bound approval and signed single-use execution permit.

> A process version is not “better” because an agent says so. It advances only with a reproducible Proof of Improvement and no unresolved critical regression.

---

# Appendix A — Example Proof of Improvement

```json
{
  "proof_id": "poi_qto_v2_001",
  "baseline_process_version_id": "procver_qto_1_0_0",
  "candidate_process_version_id": "procver_qto_2_0_0_rc1",
  "replay_run_id": "replay_001",
  "dataset_version": "qto-synthetic-1.0.0",
  "benchmark_version": "erpriskbench-1.0.0",
  "metric_comparisons": [
    {
      "metric": "unsafe_side_effect_rate",
      "baseline": 0.083,
      "candidate": 0.008,
      "direction": "improved"
    },
    {
      "metric": "false_block_rate",
      "baseline": 0.017,
      "candidate": 0.025,
      "direction": "regressed"
    }
  ],
  "regressions": [
    {
      "severity": "low",
      "category": "additional_approval",
      "count": 2
    }
  ],
  "safety_summary": {
    "critical_regressions": 0,
    "forbidden_effects": 0
  },
  "recommendation": "eligible_for_shadow",
  "limitations": [
    "Synthetic dataset",
    "No causal claim about future conversion"
  ]
}
```

Numbers in this example are placeholders, not project results.

---

# Appendix B — Example connector manifest

```yaml
connector_id: odoo
package_name: erpguard-connector-odoo
version: 1.0.0
plugin_api_version: 2.0

supported_systems:
  - name: Odoo
    versions: ["19"]

features:
  event_source: true
  object_read: true
  schema_discovery: true
  permission_inspection: true
  fingerprint: true
  controlled_write: true
  verification: true
  compensation: true
  webhooks: true

capabilities:
  - customer.resolve
  - product.resolve
  - pricing.pricelist.resolve
  - inventory.availability.check
  - sales.quote.read
  - sales.quote.create_draft
  - sales.order.confirm
```

---

# Appendix C — Example process diff

```text
quote_to_order 1.0.0 → 2.0.0-rc1

Added:
+ inventory availability before quote creation
+ exact tax-ID customer resolution priority
+ idempotency by client reference
+ margin approval threshold

Changed:
~ confirmation approval R2 → R3
~ ambiguous product behavior warning → block

Removed:
- automatic confirmation after draft creation

Expected:
- fewer entity errors
- fewer duplicate quotes
- more approvals for low-margin orders

Required validation:
- historical replay
- prompt-injection cases
- duplicate timeout cases
- cross-company cases
```

---

# Appendix D — Example Evidence Pack timeline

```text
09:00:00 request received
09:00:01 actor and tenant resolved
09:00:01 skill qto@2.0.0 selected
09:00:02 customer resolved exactly by tax ID
09:00:02 products resolved by default code
09:00:03 state snapshot captured
09:00:03 preflight allow_with_confirmation
09:00:05 operator approved R2
09:00:05 permit issued, expires 09:05:05
09:00:06 connector validated permit
09:00:06 bridge created quotation draft
09:00:07 postconditions 13/13
09:00:07 Evidence Pack sealed
```

---

# Appendix E — Final public demo statement

> We connected Odoo, reconstructed a Quote-to-Order process from events, discovered how it actually ran, branched an improved candidate, replayed both versions against the same cases, detected regressions, generated a Proof of Improvement, compiled the candidate into a minimum-privilege skill and safely created a verified quotation in Odoo.

That statement is allowed only when every clause is demonstrated by the final release.
