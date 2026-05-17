# 10 TFM Evaluation Plan Spec

**Parent spec references:** Sections 24, 28, 29, 30.

## Research Question

Can a semantic ERP preflight layer detect and prevent critical operational errors before actions execute, while producing better traceability and reducing diagnosis time compared with manual review, ad hoc scripts, native Odoo validation, and direct LLM agents?

## Phase 1 Evaluation Focus

The Phase 1 implementation supports Experiment A: Formula Guard.

## Hypotheses Covered

- **H1:** ERPGuard detects semantic formula errors that simple technical validation misses.
- **H3:** ERPGuard produces more complete traceability than manual or direct-agent execution.

## Dataset

Create representative sales order fixtures:

- valid formula;
- missing formula;
- formula capacity mismatch;
- total formula mismatch;
- product without capacity requirement;
- multiple lines with mixed outcomes.

## Metrics

- detection precision;
- false negatives;
- false positives;
- time to diagnosis;
- explanation completeness;
- audit evidence completeness.

## Baselines

1. Manual review.
2. Python ad hoc validator.
3. Direct LLM agent prompt over exported data.
4. Native Odoo validations.
5. ERPGuard preflight.

## Evaluation Output

Each run should produce:

- input fixture ID;
- expected classification;
- actual decision;
- invariant results;
- explanation/evidence;
- elapsed time;
- notes on missed or ambiguous cases.

## Phase 1 Success Criteria

- Detect all intentionally invalid formula fixtures.
- Produce no false block for valid fixture.
- Include line-level evidence for every block.
- Persist audit data sufficient to reconstruct the decision.
