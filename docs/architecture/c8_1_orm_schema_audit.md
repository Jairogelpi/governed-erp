# C8.1 - ORM / Schema Audit

Read-only audit of `erpguard/db/models.py` (139 model classes, no code changed). Wave C8.1, run after C5 pruned `erpguard/db/repositories.py` to 90 live functions and C4/C6 relocated everything else out of `erpguard/product` (which now contains only `models.py`).

**Key finding**: there are two parallel persistence systems in this repo. Most of `apps/api/routes/public_v1/*` (connections, connectors, events, processes, variants, candidates, replays, proofs, approvals, executions, evidence) is backed by `erpguard/db/model_packages/*` through the domain/application layers, and never touches `erpguard/db/models.py` or `repositories.py` at all. The **only** public_v1 exception is `apps/api/routes/public_v1/skills.py`, which imports `erpguard.db.repositories` directly. Everything else that still uses `models.py`/`repositories.py` is the internal release-readiness/demo engine (`erpguard/release_ops`, `erpguard/recording_pipeline`) and the internal-only recordings route.

**139 model classes total**: 4 live_public, 36 live_internal, 0 schema_only, 99 drop_candidate.

**No declared FK constraints anywhere**: `erpguard/db/models.py` has zero `ForeignKey()` columns in the whole file — cross-table references are plain `String`/UUID columns by convention, not SQLAlchemy/DB-level foreign keys. That's why `schema_only` is empty: there's no declared-FK mechanism that could hold a dead table hostage. It also means the 99 `drop_candidate` rows below are a name-based reachability check only, not a DB-integrity check — a table could still be referenced by ID from a live table's column without a formal FK we can detect by grep. Treat this list as a strong prior, not a final answer; skim the actual columns of anything you're about to drop for `*_id` fields that plausibly point at another surviving table before writing the drop migration.

Migration `0001_baseline` builds the schema by reading `Base.metadata.sorted_tables` dynamically, so deleting a model class changes what a fresh install creates. Dropping any table below needs a real migration (e.g. `000X_drop_retired_tables.py`), not a plain code edit. This report does not create that migration.

## LIVE_PUBLIC (4)

| Class | Table | Reachable via | Incoming FK from | Outgoing FK to |
|---|---|---|---|---|
| `Skill` | `skills` | public_v1 via: create_skill, get_skill, list_skills; internal via: create_skill; release_ops via: create_skill, get_skill, list_ui_replay_failures; release_ops direct: activation_gate.py, approval_request.py, connection_context.py, dry_run_proof.py, live_read_policy.py, live_read_request.py, operator_orchestrator.py, release_readiness.py, write_readiness_assessment.py | - | - |
| `SkillRun` | `skill_runs` | public_v1 via: create_skill_run, finish_skill_run, get_skill_run, list_skill_runs | - | - |
| `SkillRunStep` | `skill_run_steps` | public_v1 via: create_skill_run_step, list_skill_run_steps | - | - |
| `SkillVersion` | `skill_versions` | public_v1 via: create_skill_version, get_latest_skill_version, get_skill_version; internal via: create_skill_version; release_ops via: create_skill_version, get_latest_skill_version, get_skill_version | - | - |

## LIVE_INTERNAL (36)

| Class | Table | Reachable via | Incoming FK from | Outgoing FK to |
|---|---|---|---|---|
| `AuditEvent` | `audit_events` | release_ops via: create_audit_event | - | - |
| `AutomationDraft` | `automation_drafts` | release_ops via: create_automation_draft, get_automation_draft; release_ops direct: draft_review.py, skill_package_builder.py | - | - |
| `AutomationDraftReview` | `automation_draft_reviews` | release_ops via: create_automation_draft_review, get_automation_draft_review, list_draft_reviews, mark_review_compiled | - | - |
| `BlockedWriteEvidenceRecord` | `blocked_write_evidence` | release_ops via: create_blocked_write_evidence | - | - |
| `BusinessSignal` | `business_signals` | release_ops via: create_business_signal | - | - |
| `BusinessSnapshot` | `business_snapshots` | release_ops via: create_business_snapshot, get_business_snapshot | - | - |
| `Connection` | `connections` | release_ops via: get_connection; release_ops direct: operator_orchestrator.py, services.py | - | - |
| `ExecutionRunStep` | `execution_run_steps` | release_ops via: create_execution_run_step | - | - |
| `IdempotencyKey` | `idempotency_keys` | release_ops via: get_or_create_idempotency_key | - | - |
| `LiveReadEvidence` | `live_read_evidence` | release_ops via: create_live_read_evidence | - | - |
| `LiveReadExecutionRequest` | `live_read_execution_requests` | release_ops via: create_live_read_execution_request, get_live_read_execution_request, list_live_read_execution_requests_for_skill, update_live_read_execution_request_status | - | - |
| `LiveReadRun` | `live_read_runs` | release_ops via: create_live_read_run, get_live_read_run; release_ops direct: release_readiness.py | - | - |
| `OperatorSession` | `operator_sessions` | release_ops via: create_operator_session, get_operator_session, update_operator_session; release_ops direct: release_readiness.py | - | - |
| `OperatorSessionEvent` | `operator_session_events` | release_ops via: create_operator_session_event | - | - |
| `Opportunity` | `opportunities` | release_ops via: create_opportunity, get_opportunity; release_ops direct: operator_orchestrator.py, services.py | - | - |
| `OpportunityScan` | `opportunity_scans` | release_ops via: create_opportunity_scan, get_opportunity_scan | - | - |
| `Policy` | `policies` | release_ops direct: live_read_runtime.py | - | - |
| `R2WritePilotRun` | `r2_write_pilot_runs` | release_ops direct: release_readiness.py | - | - |
| `RecordingEvent` | `recording_events` | internal via: add_recording_event, list_recording_events | - | - |
| `RecordingSession` | `recording_sessions` | internal via: create_recording_session, finish_recording_session, get_recording_session, list_recording_sessions | - | - |
| `SkillActivationGateEvaluation` | `skill_activation_gate_evaluations` | release_ops via: create_activation_gate_evaluation, get_latest_gate_evaluation | - | - |
| `SkillApprovalDecision` | `skill_approval_decisions` | release_ops via: create_skill_approval_decision, list_approval_decisions_for_skill | - | - |
| `SkillApprovalRequest` | `skill_approval_requests` | release_ops via: create_skill_approval_request, get_latest_approval_request_for_skill, update_approval_request_status | - | - |
| `SkillDryRunProof` | `skill_dry_run_proofs` | release_ops via: create_skill_dry_run_proof, get_latest_dry_run_proof_for_skill | - | - |
| `Tenant` | `tenants` | release_ops via: create_tenant, get_tenant, list_tenants, suspend_tenant; release_ops direct: demo_seed.py, operator_orchestrator.py, operator_smoke.py, platform_tenant.py, release_readiness.py | - | - |
| `UICompiledSkill` | `ui_compiled_skills` | release_ops via: create_ui_compiled_skill, get_ui_compiled_skill | - | - |
| `UIRecordingEvent` | `ui_recording_events` | release_ops via: add_ui_recording_event, list_ui_recording_events | - | - |
| `UIRecordingSession` | `ui_recording_sessions` | release_ops via: create_ui_recording_session, finish_ui_recording_session, get_ui_recording_session | - | - |
| `UIReplayFailure` | `ui_replay_failures` | release_ops via: add_ui_replay_failure, list_ui_replay_failures | - | - |
| `UIReplayRun` | `ui_replay_runs` | release_ops via: create_ui_replay_run, finish_ui_replay_run, get_ui_replay_run | - | - |
| `UIReplayStepAudit` | `ui_replay_step_audits` | release_ops via: add_ui_replay_step_audit, list_ui_replay_step_audits | - | - |
| `UIReplayVerification` | `ui_replay_verifications` | release_ops via: add_ui_replay_verification, list_ui_replay_verifications | - | - |
| `UISkillDraft` | `ui_skill_drafts` | release_ops via: create_ui_skill_draft, get_ui_skill_draft | - | - |
| `WritePilotRun` | `write_pilot_runs` | release_ops direct: release_readiness.py | - | - |
| `WriteReadinessAssessment` | `write_readiness_assessments` | release_ops via: create_write_readiness_assessment, get_write_readiness_assessment | - | - |
| `WriteReadinessCertification` | `write_readiness_certifications` | release_ops via: get_latest_write_readiness_certification_for_skill | - | - |

## SCHEMA_ONLY (has incoming FK, cannot drop alone) (0)

| Class | Table | Reachable via | Incoming FK from | Outgoing FK to |
|---|---|---|---|---|

## DROP_CANDIDATE (no code path, no incoming FK) (99)

| Class | Table | Reachable via | Incoming FK from | Outgoing FK to |
|---|---|---|---|---|
| `ActionDispatchEligibilityEvent` | `action_dispatch_eligibility_events` | (none) | - | - |
| `ActionDispatchExecutionAuditEvent` | `action_dispatch_execution_audit_events` | (none) | - | - |
| `ActionDispatchResultRecord` | `action_dispatch_result_records` | (none) | - | - |
| `ActionPlanStepToken` | `action_plan_step_tokens` | (none) | - | - |
| `ActiveSkillRun` | `active_skill_runs` | (none) | - | - |
| `ActiveSkillRunEvent` | `active_skill_run_events` | (none) | - | - |
| `AdvisoryProposal` | `advisory_proposals` | (none) | - | - |
| `AdvisorySession` | `advisory_sessions` | (none) | - | - |
| `AgentBuilderEvent` | `agent_builder_events` | (none) | - | - |
| `AgentBuilderSession` | `agent_builder_sessions` | (none) | - | - |
| `AgentCandidateActivationEvent` | `agent_candidate_activation_events` | (none) | - | - |
| `AgentCandidateActivationRequest` | `agent_candidate_activation_requests` | (none) | - | - |
| `AgentCandidateActivationRequestEvent` | `agent_candidate_activation_request_events` | (none) | - | - |
| `AgentCandidateApprovalEvent` | `agent_candidate_approval_events` | (none) | - | - |
| `AgentCandidateApprovalPacket` | `agent_candidate_approval_packets` | (none) | - | - |
| `AgentCandidateDecision` | `agent_candidate_decisions` | (none) | - | - |
| `AgentCandidateDecisionEvent` | `agent_candidate_decision_events` | (none) | - | - |
| `AgentDraftBridgeEvent` | `agent_draft_bridge_events` | (none) | - | - |
| `AgentDraftHandoffEvent` | `agent_draft_handoff_events` | (none) | - | - |
| `AgentDraftHandoffPacket` | `agent_draft_handoff_packets` | (none) | - | - |
| `AgentHandoffVersionEvent` | `agent_handoff_version_events` | (none) | - | - |
| `AgentHandoffVersionLink` | `agent_handoff_version_links` | (none) | - | - |
| `AgentProposalDraftLink` | `agent_proposal_draft_links` | (none) | - | - |
| `AgentSkillRunPreviewEvent` | `agent_skill_run_preview_events` | (none) | - | - |
| `AuditExport` | `audit_exports` | (none) | - | - |
| `ClarificationAnswer` | `clarification_answers` | (none) | - | - |
| `ClarificationAuditEvent` | `clarification_audit_events` | (none) | - | - |
| `ConnectorAuthProfile` | `connector_auth_profiles` | (none) | - | - |
| `ConnectorCredentialAuditEvent` | `connector_credential_audit_events` | (none) | - | - |
| `ConnectorReadEvidence` | `connector_read_evidence` | (none) | - | - |
| `ConnectorSetupAuditEvent` | `connector_setup_audit_events` | (none) | - | - |
| `ConnectorSetupSession` | `connector_setup_sessions` | (none) | - | - |
| `CredentialVaultAuditEvent` | `credential_vault_audit_events` | (none) | - | - |
| `CredentialVaultEntry` | `credential_vault_entries` | (none) | - | - |
| `ERPFingerprintingAuditEvent` | `erp_fingerprinting_audit_events` | (none) | - | - |
| `ERPFingerprintingPlan` | `erp_fingerprinting_plans` | (none) | - | - |
| `ExecutionRequest` | `execution_requests` | (none) | - | - |
| `ExecutionRun` | `execution_runs` | (none) | - | - |
| `ExternalConnectorAuditEvent` | `external_connector_audit_events` | (none) | - | - |
| `FakeERPExecutionAuditEvent` | `fake_erp_execution_audit_events` | (none) | - | - |
| `FakeERPExecutionEvidence` | `fake_erp_execution_evidence` | (none) | - | - |
| `FakeERPExecutionEvidencePack` | `fake_erp_execution_evidence_packs` | (none) | - | - |
| `FakeERPExecutionRecord` | `fake_erp_execution_records` | (none) | - | - |
| `FakeERPRegressionAuditEvent` | `fake_erp_regression_audit_events` | (none) | - | - |
| `FakeERPRegressionCase` | `fake_erp_regression_cases` | (none) | - | - |
| `FakeERPRegressionRun` | `fake_erp_regression_runs` | (none) | - | - |
| `GeneratedCapabilityAuditEvent` | `generated_capability_audit_events` | (none) | - | - |
| `GeneratedCapabilitySet` | `generated_capability_sets` | (none) | - | - |
| `InvariantResult` | `invariant_results` | (none) | - | - |
| `KillSwitchEvent` | `kill_switch_events` | (none) | - | - |
| `ManualDryRunAuditEvent` | `manual_dry_run_audit_events` | (none) | - | - |
| `ManualDryRunEvidence` | `manual_dry_run_evidence` | (none) | - | - |
| `MappingConfirmation` | `mapping_confirmations` | (none) | - | - |
| `OAuthState` | `oauth_states` | (none) | - | - |
| `OAuthTokenRecord` | `oauth_token_records` | (none) | - | - |
| `OdooConnectionTest` | `odoo_connection_tests` | (none) | - | - |
| `OdooConnectionTestAuditEvent` | `odoo_connection_test_audit_events` | (none) | - | - |
| `OdooReadEvidenceAuditEvent` | `odoo_read_evidence_audit_events` | (none) | - | - |
| `OdooReadEvidencePack` | `odoo_read_evidence_packs` | (none) | - | - |
| `OdooReadMapping` | `odoo_read_mappings` | (none) | - | - |
| `OdooReadMappingAuditEvent` | `odoo_read_mapping_audit_events` | (none) | - | - |
| `OdooReadOnlyAdapterAuditEvent` | `odoo_read_only_adapter_audit_events` | (none) | - | - |
| `OdooReadOnlyAdapterSession` | `odoo_read_only_adapter_sessions` | (none) | - | - |
| `OdooReadOnlyDemoAuditEvent` | `odoo_read_only_demo_audit_events` | (none) | - | - |
| `OdooReadOnlyDemoFlow` | `odoo_read_only_demo_flows` | (none) | - | - |
| `OperatorActionPlanEvent` | `operator_action_plan_events` | (none) | - | - |
| `OperatorConsoleQuery` | `operator_console_queries` | (none) | - | - |
| `OperatorConsoleSession` | `operator_console_sessions` | (none) | - | - |
| `OperatorEvidencePack` | `operator_evidence_packs` | (none) | - | - |
| `PlatformAuditEvent` | `platform_audit_events` | (none) | - | - |
| `PreflightCase` | `preflight_cases` | (none) | - | - |
| `R2EvidenceReview` | `r2_evidence_reviews` | (none) | - | - |
| `R2ExecutionReport` | `r2_execution_reports` | (none) | - | - |
| `R2PromotionGate` | `r2_promotion_gates` | (none) | - | - |
| `R2RollbackRehearsal` | `r2_rollback_rehearsals` | (none) | - | - |
| `R2WritePilotEvidence` | `r2_write_pilot_evidence` | (none) | - | - |
| `R2WritePilotRequest` | `r2_write_pilot_requests` | (none) | - | - |
| `ReadOnlyConnectorActivation` | `read_only_connector_activations` | (none) | - | - |
| `ReadOnlyConnectorActivationAuditEvent` | `read_only_connector_activation_audit_events` | (none) | - | - |
| `ReadOnlyConnectorActivationRequest` | `read_only_connector_activation_requests` | (none) | - | - |
| `SafeDiscoveryAuditEvent` | `safe_discovery_audit_events` | (none) | - | - |
| `SafeDiscoveryPlan` | `safe_discovery_plans` | (none) | - | - |
| `SkillRunQueueEntry` | `skill_run_queue_entries` | (none) | - | - |
| `SkillSchedule` | `skill_schedules` | (none) | - | - |
| `SkillScheduleEvent` | `skill_schedule_events` | (none) | - | - |
| `UISkillVersionLifecycleEvent` | `ui_skill_version_events` | (none) | - | - |
| `UISkillVersionRecord` | `ui_skill_version_records` | (none) | - | - |
| `VisualBrowserSession` | `visual_browser_sessions` | (none) | - | - |
| `VisualBrowserSessionAuditEvent` | `visual_browser_session_audit_events` | (none) | - | - |
| `VisualObservationAuditEvent` | `visual_observation_audit_events` | (none) | - | - |
| `VisualObservationSnapshot` | `visual_observation_snapshots` | (none) | - | - |
| `VisualTableFormExtraction` | `visual_table_form_extractions` | (none) | - | - |
| `VisualTableFormExtractionAuditEvent` | `visual_table_form_extraction_audit_events` | (none) | - | - |
| `VisualWorkflowTrace` | `visual_workflow_traces` | (none) | - | - |
| `VisualWorkflowTraceAuditEvent` | `visual_workflow_trace_audit_events` | (none) | - | - |
| `WriteImpactPreview` | `write_impact_previews` | (none) | - | - |
| `WritePilotEvidence` | `write_pilot_evidence` | (none) | - | - |
| `WritePilotRequest` | `write_pilot_requests` | (none) | - | - |
| `WriteRollbackPlan` | `write_rollback_plans` | (none) | - | - |

## Recommended next migration

**Drop first, no FK entanglement (99 tables):**

- `action_dispatch_eligibility_events` (ActionDispatchEligibilityEvent)
- `action_dispatch_execution_audit_events` (ActionDispatchExecutionAuditEvent)
- `action_dispatch_result_records` (ActionDispatchResultRecord)
- `action_plan_step_tokens` (ActionPlanStepToken)
- `active_skill_runs` (ActiveSkillRun)
- `active_skill_run_events` (ActiveSkillRunEvent)
- `advisory_proposals` (AdvisoryProposal)
- `advisory_sessions` (AdvisorySession)
- `agent_builder_events` (AgentBuilderEvent)
- `agent_builder_sessions` (AgentBuilderSession)
- `agent_candidate_activation_events` (AgentCandidateActivationEvent)
- `agent_candidate_activation_requests` (AgentCandidateActivationRequest)
- `agent_candidate_activation_request_events` (AgentCandidateActivationRequestEvent)
- `agent_candidate_approval_events` (AgentCandidateApprovalEvent)
- `agent_candidate_approval_packets` (AgentCandidateApprovalPacket)
- `agent_candidate_decisions` (AgentCandidateDecision)
- `agent_candidate_decision_events` (AgentCandidateDecisionEvent)
- `agent_draft_bridge_events` (AgentDraftBridgeEvent)
- `agent_draft_handoff_events` (AgentDraftHandoffEvent)
- `agent_draft_handoff_packets` (AgentDraftHandoffPacket)
- `agent_handoff_version_events` (AgentHandoffVersionEvent)
- `agent_handoff_version_links` (AgentHandoffVersionLink)
- `agent_proposal_draft_links` (AgentProposalDraftLink)
- `agent_skill_run_preview_events` (AgentSkillRunPreviewEvent)
- `audit_exports` (AuditExport)
- `clarification_answers` (ClarificationAnswer)
- `clarification_audit_events` (ClarificationAuditEvent)
- `connector_auth_profiles` (ConnectorAuthProfile)
- `connector_credential_audit_events` (ConnectorCredentialAuditEvent)
- `connector_read_evidence` (ConnectorReadEvidence)
- `connector_setup_audit_events` (ConnectorSetupAuditEvent)
- `connector_setup_sessions` (ConnectorSetupSession)
- `credential_vault_audit_events` (CredentialVaultAuditEvent)
- `credential_vault_entries` (CredentialVaultEntry)
- `erp_fingerprinting_audit_events` (ERPFingerprintingAuditEvent)
- `erp_fingerprinting_plans` (ERPFingerprintingPlan)
- `execution_requests` (ExecutionRequest)
- `execution_runs` (ExecutionRun)
- `external_connector_audit_events` (ExternalConnectorAuditEvent)
- `fake_erp_execution_audit_events` (FakeERPExecutionAuditEvent)
- `fake_erp_execution_evidence` (FakeERPExecutionEvidence)
- `fake_erp_execution_evidence_packs` (FakeERPExecutionEvidencePack)
- `fake_erp_execution_records` (FakeERPExecutionRecord)
- `fake_erp_regression_audit_events` (FakeERPRegressionAuditEvent)
- `fake_erp_regression_cases` (FakeERPRegressionCase)
- `fake_erp_regression_runs` (FakeERPRegressionRun)
- `generated_capability_audit_events` (GeneratedCapabilityAuditEvent)
- `generated_capability_sets` (GeneratedCapabilitySet)
- `invariant_results` (InvariantResult)
- `kill_switch_events` (KillSwitchEvent)
- `manual_dry_run_audit_events` (ManualDryRunAuditEvent)
- `manual_dry_run_evidence` (ManualDryRunEvidence)
- `mapping_confirmations` (MappingConfirmation)
- `oauth_states` (OAuthState)
- `oauth_token_records` (OAuthTokenRecord)
- `odoo_connection_tests` (OdooConnectionTest)
- `odoo_connection_test_audit_events` (OdooConnectionTestAuditEvent)
- `odoo_read_evidence_audit_events` (OdooReadEvidenceAuditEvent)
- `odoo_read_evidence_packs` (OdooReadEvidencePack)
- `odoo_read_mappings` (OdooReadMapping)
- `odoo_read_mapping_audit_events` (OdooReadMappingAuditEvent)
- `odoo_read_only_adapter_audit_events` (OdooReadOnlyAdapterAuditEvent)
- `odoo_read_only_adapter_sessions` (OdooReadOnlyAdapterSession)
- `odoo_read_only_demo_audit_events` (OdooReadOnlyDemoAuditEvent)
- `odoo_read_only_demo_flows` (OdooReadOnlyDemoFlow)
- `operator_action_plan_events` (OperatorActionPlanEvent)
- `operator_console_queries` (OperatorConsoleQuery)
- `operator_console_sessions` (OperatorConsoleSession)
- `operator_evidence_packs` (OperatorEvidencePack)
- `platform_audit_events` (PlatformAuditEvent)
- `preflight_cases` (PreflightCase)
- `r2_evidence_reviews` (R2EvidenceReview)
- `r2_execution_reports` (R2ExecutionReport)
- `r2_promotion_gates` (R2PromotionGate)
- `r2_rollback_rehearsals` (R2RollbackRehearsal)
- `r2_write_pilot_evidence` (R2WritePilotEvidence)
- `r2_write_pilot_requests` (R2WritePilotRequest)
- `read_only_connector_activations` (ReadOnlyConnectorActivation)
- `read_only_connector_activation_audit_events` (ReadOnlyConnectorActivationAuditEvent)
- `read_only_connector_activation_requests` (ReadOnlyConnectorActivationRequest)
- `safe_discovery_audit_events` (SafeDiscoveryAuditEvent)
- `safe_discovery_plans` (SafeDiscoveryPlan)
- `skill_run_queue_entries` (SkillRunQueueEntry)
- `skill_schedules` (SkillSchedule)
- `skill_schedule_events` (SkillScheduleEvent)
- `ui_skill_version_events` (UISkillVersionLifecycleEvent)
- `ui_skill_version_records` (UISkillVersionRecord)
- `visual_browser_sessions` (VisualBrowserSession)
- `visual_browser_session_audit_events` (VisualBrowserSessionAuditEvent)
- `visual_observation_audit_events` (VisualObservationAuditEvent)
- `visual_observation_snapshots` (VisualObservationSnapshot)
- `visual_table_form_extractions` (VisualTableFormExtraction)
- `visual_table_form_extraction_audit_events` (VisualTableFormExtractionAuditEvent)
- `visual_workflow_traces` (VisualWorkflowTrace)
- `visual_workflow_trace_audit_events` (VisualWorkflowTraceAuditEvent)
- `write_impact_previews` (WriteImpactPreview)
- `write_pilot_evidence` (WritePilotEvidence)
- `write_pilot_requests` (WritePilotRequest)
- `write_rollback_plans` (WriteRollbackPlan)

**Needs FK cleanup before dropping (0 tables)** - these still have other tables pointing at them via FK. Either drop the whole dependent cluster together, or drop the FK column first in a preceding migration step:


LIVE_PUBLIC and LIVE_INTERNAL tables are out of scope for deletion; they back real code paths.