# Decision-to-Outcome Flow (Spec 92)

Diagrams for the governed decision-to-outcome lifecycle added in
`docs/specs/92_governed_decision_to_outcome_backend_rc.md`. Each diagram
names the actual model/service that implements it — none of this is
aspirational.

## 1. Decision-to-outcome lifecycle

```mermaid
flowchart TD
    A[AnalyticalSnapshot] --> B[MarginAnalysis]
    B --> C[MarginOpportunity]
    C --> D[GovernedRecommendation]
    D -->|independent approval| E[GovernedActionDraft]
    E -->|validate| F[ExecutionRun via canary router]
    F -->|signed permit + execute| G[Postcondition verified]
    G --> H[OutcomeMeasurementPlan]
    H --> I[Follow-up OutcomeObservation]
    I --> J[RealizedOutcomeReport]
    J --> K[DecisionOutcomeEvidenceBundle: sealed]
    D -.-> K
    E -.-> K
    F -.-> K
    G -.-> K
```

## 2. Recommendation state machine

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> submitted: submit (freezes content)
    submitted --> approved: independent approval, exact content-hash scope
    approved --> converted: action draft -> ExecutionRun
    draft --> rejected
    submitted --> rejected
    draft --> expired
    submitted --> expired
    approved --> expired
    rejected --> [*]
    expired --> [*]
    converted --> [*]
```

## 3. Action-draft state machine

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> awaiting_inputs
    awaiting_inputs --> validated
    draft --> validated: content freezes here
    validated --> ready_for_run
    ready_for_run --> converted: idempotent ExecutionRun creation
    draft --> invalidated
    awaiting_inputs --> invalidated
    validated --> invalidated
    ready_for_run --> invalidated
    converted --> [*]
    invalidated --> [*]
```

## 4. Canary policy state machine

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> approved: independent approval, content freezes
    approved --> active: one active policy per process (enforced)
    active --> paused: safety threshold or critical incident
    paused --> active: manual resume
    active --> completed
    active --> aborted
    paused --> aborted
    completed --> [*]
    aborted --> [*]
```

## 5. Canary routing sequence

```mermaid
sequenceDiagram
    participant Caller
    participant PermitService
    participant CanaryRouterService
    participant KillSwitch
    participant DB as CanaryRoutingDecision (append-only)

    Caller->>PermitService: plan(process_key, routing_context)
    PermitService->>CanaryRouterService: route(tenant, process_key, business_object_key, capability, amount)
    CanaryRouterService->>KillSwitch: is_active(tenant)?
    alt kill switch active
        CanaryRouterService-->>DB: persist decision (lane=blocked)
        CanaryRouterService-->>PermitService: blocked
        PermitService-->>Caller: KillSwitchActive
    else no active policy / out of scope / limits reached
        CanaryRouterService-->>DB: persist decision (lane=stable, reason)
        CanaryRouterService-->>PermitService: stable package
    else in scope
        CanaryRouterService->>CanaryRouterService: bucket = sha256(tenant, policy, process_key, object_key) mod 10000
        CanaryRouterService->>CanaryRouterService: lane = canary if bucket < percentage_basis_points else stable
        CanaryRouterService-->>DB: persist decision (lane, bucket, reason)
        CanaryRouterService-->>PermitService: selected package
    end
    PermitService-->>Caller: ExecutionRun (skill_package_id, deployment_lane recorded)
```

## 6. Outcome measurement sequence

```mermaid
sequenceDiagram
    participant Operator
    participant OutcomeService
    participant Gates as Comparison gates

    Operator->>OutcomeService: create_plan(recommendation, baseline snapshot, comparison_method)
    Operator->>OutcomeService: approve_plan(independent approval)
    Operator->>OutcomeService: start(plan)
    Operator->>OutcomeService: capture_followup(live_odoo_read | fixture | manual_import)
    Operator->>OutcomeService: evaluate(plan)
    OutcomeService->>Gates: metric version matches? currency comparable? cost coverage sufficient? baseline/follow-up unblocked?
    alt any gate fails
        Gates-->>OutcomeService: block reason
        OutcomeService-->>Operator: RealizedOutcomeReport(result_classification=blocked, realized_value=null)
    else all gates pass
        Gates-->>OutcomeService: comparable
        OutcomeService-->>Operator: RealizedOutcomeReport(observed_*, result_classification, no causal claim)
    end
```

## 7. Evidence hash chain

```mermaid
flowchart LR
    subgraph Manifest [Ordered ResourceReference list]
        R1[analytical_snapshot]
        R2[margin_analysis]
        R3[governed_recommendation]
        R4[execution_run]
        R5[realized_outcome_report]
    end
    R1 -->|"chain = sha256(previous='', R1)"| C1[chain_1]
    C1 -->|"chain = sha256(previous=chain_1, R2)"| C2[chain_2]
    C2 -->|"..."| C3[chain_3]
    C3 -->|"..."| C4[chain_4]
    C4 -->|"chain = sha256(previous=chain_4, R5)"| C5[chain_hash]
    C5 --> Seal[DecisionOutcomeEvidenceBundle.chain_hash]

    style Seal fill:#2d6,stroke:#141,color:#fff
```

Any change to `R1`..`R4` invalidates `chain_hash` even if `R5` and the
final link are untouched — the chain, not just each individual hash, is
what `verify()` and the sealed-immutability listener protect.

## 8. Odoo pricing-scenario capability boundary

```mermaid
flowchart TD
    subgraph Allowed["sales.quote.create_pricing_scenario_draft"]
        direction TB
        Pre[Preflight: staging-only, customer active, products active/saleable, no forbidden marker]
        Create["create ONE sale.order, state=draft, client_order_ref set"]
        Idem["find_by_client_reference: retry returns existing draft"]
        Post["Postcondition: state==draft, lines/prices/margin match, zero invoice/picking/PO/MO"]
        Pre --> Create --> Idem
        Create --> Post
    end
    subgraph Forbidden["Never reachable from this capability"]
        direction TB
        F1[action_confirm]
        F2[invoice creation]
        F3[payment]
        F4[delivery / stock.picking validation]
        F5[purchase / manufacturing order]
        F6[generic model/method/execute_raw]
        F7[price-list activation]
        F8[modifying an existing order]
    end
    Allowed -.->|structurally impossible, not just policy-blocked| Forbidden
```

`OdooConnectorPlugin` has no `model`, `method`, or `execute_raw` attribute
at all (`tests/test_phase16_7_pricing_scenario_draft.py::test_no_generic_write_method_exists`
and the identical check in `test_backend_rc_end_to_end.py` assert this
structurally, not just by convention).
