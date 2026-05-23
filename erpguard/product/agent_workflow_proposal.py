from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field


class WorkflowStep(BaseModel):
    step_id: str
    step_type: str
    label: str
    description: str
    is_read_only: bool = True
    requires_guard: bool = False
    requires_approval: bool = False
    can_execute: bool = False


class WorkflowProposal(BaseModel):
    workflow_id: str
    name: str
    description: str
    trigger_type: str
    steps: list[WorkflowStep] = Field(default_factory=list)
    runtime_mode: str = "advisory_only"
    can_execute: bool = False
    advisory_note: str = (
        "This workflow is a non-executable proposal. "
        "It must be reviewed, compiled, and approved before any automation can run."
    )


_TEMPLATES: dict[str, dict] = {
    "read_sales_order": {
        "name": "Read Sales Order",
        "description": "Read and display sales order details",
        "steps": [
            {"step_id": "s1", "step_type": "load_context", "label": "Load Context",
             "description": "Load connection and user context", "is_read_only": True},
            {"step_id": "s2", "step_type": "read_record", "label": "Read Sales Order",
             "description": "Fetch sales order by reference", "is_read_only": True},
            {"step_id": "s3", "step_type": "produce_output", "label": "Produce Output",
             "description": "Format and return the sales order data", "is_read_only": True},
        ],
    },
    "validate_sales_order": {
        "name": "Validate Sales Order Formula",
        "description": "Preflight formula validation on a sales order before confirm",
        "steps": [
            {"step_id": "s1", "step_type": "load_context", "label": "Load Context",
             "description": "Load connection and user context", "is_read_only": True},
            {"step_id": "s2", "step_type": "read_record", "label": "Read Sales Order",
             "description": "Fetch sales order by reference", "is_read_only": True},
            {"step_id": "s3", "step_type": "run_guard", "label": "Formula Guard",
             "description": "Run Formula Guard preflight check", "is_read_only": True, "requires_guard": True},
            {"step_id": "s4", "step_type": "produce_decision", "label": "Produce Decision",
             "description": "Return allow/block decision with evidence", "is_read_only": True},
        ],
    },
    "confirm_sales_order": {
        "name": "Confirm Sales Order",
        "description": "Validate and confirm a sales order after human approval",
        "steps": [
            {"step_id": "s1", "step_type": "load_context", "label": "Load Context",
             "description": "Load connection and user context", "is_read_only": True},
            {"step_id": "s2", "step_type": "read_record", "label": "Read Sales Order",
             "description": "Fetch and verify sales order exists", "is_read_only": True},
            {"step_id": "s3", "step_type": "run_guard", "label": "Formula Guard",
             "description": "Preflight guard check", "is_read_only": True, "requires_guard": True},
            {"step_id": "s4", "step_type": "request_approval", "label": "Request Human Approval",
             "description": "Block and await human approval before any write",
             "is_read_only": True, "requires_approval": True},
            {"step_id": "s5", "step_type": "produce_decision", "label": "Produce Decision",
             "description": "Conditional: execute confirm only if approved (requires Write Pilot certification)",
             "is_read_only": False, "requires_guard": True, "requires_approval": True},
        ],
    },
    "send_invoice": {
        "name": "Send Invoice by Email",
        "description": "Generate and send invoice email to customer",
        "steps": [
            {"step_id": "s1", "step_type": "load_context", "label": "Load Context",
             "description": "Load connection and user context", "is_read_only": True},
            {"step_id": "s2", "step_type": "read_record", "label": "Read Invoice",
             "description": "Fetch invoice by reference", "is_read_only": True},
            {"step_id": "s3", "step_type": "run_guard", "label": "Send Guard",
             "description": "Verify invoice is in valid state for sending",
             "is_read_only": True, "requires_guard": True},
            {"step_id": "s4", "step_type": "request_approval", "label": "Request Approval",
             "description": "Await human approval before sending",
             "is_read_only": True, "requires_approval": True},
            {"step_id": "s5", "step_type": "produce_decision", "label": "Produce Decision",
             "description": "Conditional: send email if approved", "is_read_only": False,
             "requires_approval": True},
        ],
    },
    "read_invoice": {
        "name": "Read Invoice",
        "description": "Read and display invoice details",
        "steps": [
            {"step_id": "s1", "step_type": "load_context", "label": "Load Context",
             "description": "Load connection context", "is_read_only": True},
            {"step_id": "s2", "step_type": "read_record", "label": "Read Invoice",
             "description": "Fetch invoice by reference", "is_read_only": True},
            {"step_id": "s3", "step_type": "produce_output", "label": "Produce Output",
             "description": "Format and return invoice data", "is_read_only": True},
        ],
    },
    "report_inventory": {
        "name": "Inventory Report",
        "description": "Read and report current inventory levels",
        "steps": [
            {"step_id": "s1", "step_type": "load_context", "label": "Load Context",
             "description": "Load connection context", "is_read_only": True},
            {"step_id": "s2", "step_type": "read_record", "label": "Read Inventory",
             "description": "Fetch stock quantities per location", "is_read_only": True},
            {"step_id": "s3", "step_type": "produce_output", "label": "Produce Report",
             "description": "Format inventory report", "is_read_only": True},
        ],
    },
    "generic_read": {
        "name": "Read ERP Record",
        "description": "Read one or more ERP records",
        "steps": [
            {"step_id": "s1", "step_type": "load_context", "label": "Load Context",
             "description": "Load connection context", "is_read_only": True},
            {"step_id": "s2", "step_type": "read_record", "label": "Read Record",
             "description": "Fetch the target record(s)", "is_read_only": True},
            {"step_id": "s3", "step_type": "produce_output", "label": "Produce Output",
             "description": "Return formatted result", "is_read_only": True},
        ],
    },
    "generic_update": {
        "name": "Update ERP Record",
        "description": "Update one or more ERP records with human approval",
        "steps": [
            {"step_id": "s1", "step_type": "load_context", "label": "Load Context",
             "description": "Load connection context", "is_read_only": True},
            {"step_id": "s2", "step_type": "read_record", "label": "Read Record",
             "description": "Verify record exists before update", "is_read_only": True},
            {"step_id": "s3", "step_type": "run_guard", "label": "Write Guard",
             "description": "Validate write is safe", "is_read_only": True, "requires_guard": True},
            {"step_id": "s4", "step_type": "request_approval", "label": "Request Approval",
             "description": "Block until human approves the write",
             "is_read_only": True, "requires_approval": True},
            {"step_id": "s5", "step_type": "produce_decision", "label": "Produce Decision",
             "description": "Return approval result (write execution requires Write Pilot certification)",
             "is_read_only": True, "requires_approval": True},
        ],
    },
}


def _select_template(action_type: str, target_entity: str) -> dict:
    key = f"{action_type}_{target_entity}"
    if key in _TEMPLATES:
        return _TEMPLATES[key]
    if action_type in ("read", "report"):
        return _TEMPLATES["generic_read"]
    if action_type in ("update", "create", "confirm", "delete"):
        return _TEMPLATES["generic_update"]
    return _TEMPLATES["generic_read"]


def propose_workflow(action_type: str, target_entity: str, trigger_type: str) -> WorkflowProposal:
    template = _select_template(action_type, target_entity)
    steps = [WorkflowStep(**s) for s in template["steps"]]
    return WorkflowProposal(
        workflow_id=f"wf_{uuid4().hex[:12]}",
        name=template["name"],
        description=template["description"],
        trigger_type=trigger_type,
        steps=steps,
        runtime_mode="advisory_only",
        can_execute=False,
    )
