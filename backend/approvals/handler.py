"""
AgentGuard Approvals Lambda Handler — Dashboard approve/deny endpoint.

Handles three routes:
- GET  /approvals/pending      → List all pending approvals
- POST /approvals/{id}/approve → Approve a pending action (idempotent)
- POST /approvals/{id}/deny    → Deny a pending action (idempotent)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from backend.approvals.workflow import send_task_success
from backend.shared.constants import (
    ActionStatus,
    ApprovalStatus,
    CORS_HEADERS,
)
from backend.shared.dynamodb import get_dynamodb_client
from backend.shared.models import (
    ApprovalActionRequest,
    AuditLogEntry,
    now_iso,
)

logger = logging.getLogger("agentguard.approvals")
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route requests to the appropriate approval handler."""
    try:
        http_method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        path_params = event.get("pathParameters") or {}

        logger.info(json.dumps({
            "level": "INFO",
            "service": "approvals",
            "operation": "request",
            "method": http_method,
            "path": path,
        }))

        # Handle OPTIONS (CORS preflight)
        if http_method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": "",
            }

        # GET /approvals/pending
        if http_method == "GET" and "pending" in path:
            return _handle_get_pending()

        # POST /approvals/{id}/approve
        if http_method == "POST" and "approve" in path:
            approval_id = path_params.get("id", "")
            if not approval_id:
                return _error_response(400, "Missing approval ID")
            body = json.loads(event.get("body", "{}") or "{}")
            return _handle_approve(approval_id, body)

        # POST /approvals/{id}/deny
        if http_method == "POST" and "deny" in path:
            approval_id = path_params.get("id", "")
            if not approval_id:
                return _error_response(400, "Missing approval ID")
            body = json.loads(event.get("body", "{}") or "{}")
            return _handle_deny(approval_id, body)

        return _error_response(404, f"Route not found: {http_method} {path}")

    except Exception as e:
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "approvals",
            "operation": "internal_error",
            "error": str(e),
        }))
        return _error_response(500, f"Internal error: {str(e)}")


def _handle_get_pending() -> dict[str, Any]:
    """Return all pending approvals."""
    db = get_dynamodb_client()
    pending = db.get_pending_approvals()

    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({
            "success": True,
            "data": pending,
            "count": len(pending),
        }),
    }


def _handle_approve(approval_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """
    Approve a pending action. Idempotent — approving twice returns existing result.

    1. Validate the approval exists and is PENDING
    2. Update DynamoDB status to APPROVED
    3. Send task success to Step Functions (if task token exists)
    4. Write new audit log entry recording the approval
    """
    db = get_dynamodb_client()

    # Fetch the pending approval
    approval = db.get_pending_approval(approval_id)
    if not approval:
        return _error_response(404, f"Approval {approval_id} not found")

    # Idempotency: if already approved, return success
    if approval.get("status") == ApprovalStatus.APPROVED.value:
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "success": True,
                "message": "Action was already approved",
                "data": approval,
            }),
        }

    # Check if expired
    expires_at = approval.get("expires_at", "")
    if expires_at and expires_at < datetime.now(timezone.utc).isoformat():
        db.update_approval_status(approval_id, ApprovalStatus.EXPIRED.value)
        return _error_response(410, "Approval has expired")

    # Parse the request body
    try:
        action_req = ApprovalActionRequest(**body)
    except ValidationError:
        action_req = ApprovalActionRequest()

    # Update DynamoDB
    db.update_approval_status(
        approval_id,
        ApprovalStatus.APPROVED.value,
        approved_by=action_req.approved_by,
    )

    # Send task success to Step Functions
    task_token = approval.get("step_functions_task_token", "")
    if task_token:
        send_task_success(task_token, "APPROVED", action_req.approved_by)

    # Write approval audit log entry (immutable — new record, not modifying original)
    audit_entry = AuditLogEntry(
        action_id=approval.get("action_id", ""),
        timestamp=now_iso(),
        tool_name=approval.get("tool_name", ""),
        tool_parameters=approval.get("tool_parameters", {}),
        agent_session_id=approval.get("agent_session_id", ""),
        cedar_decision="ALLOW",
        cedar_reason="Approved by human reviewer",
        risk_level=approval.get("risk_level", "MEDIUM"),
        final_status=ActionStatus.APPROVED.value,
        approved_by=action_req.approved_by,
        approval_timestamp=now_iso(),
    )
    db.put_audit_log(audit_entry)

    logger.info(json.dumps({
        "level": "INFO",
        "service": "approvals",
        "operation": "approve",
        "approval_id": approval_id,
        "approved_by": action_req.approved_by,
    }))

    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({
            "success": True,
            "message": f"Action approved by {action_req.approved_by}",
            "approval_id": approval_id,
            "action_id": approval.get("action_id", ""),
        }),
    }


def _handle_deny(approval_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """
    Deny a pending action. Idempotent — denying twice returns existing result.

    1. Validate the approval exists and is PENDING
    2. Update DynamoDB status to DENIED
    3. Send task failure to Step Functions (if task token exists)
    4. Write new audit log entry recording the denial
    """
    db = get_dynamodb_client()

    # Fetch the pending approval
    approval = db.get_pending_approval(approval_id)
    if not approval:
        return _error_response(404, f"Approval {approval_id} not found")

    # Idempotency: if already denied, return success
    if approval.get("status") == ApprovalStatus.DENIED.value:
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "success": True,
                "message": "Action was already denied",
                "data": approval,
            }),
        }

    # Parse the request body
    try:
        action_req = ApprovalActionRequest(**body)
    except ValidationError:
        action_req = ApprovalActionRequest()

    # Update DynamoDB
    db.update_approval_status(
        approval_id,
        ApprovalStatus.DENIED.value,
        approved_by=action_req.approved_by,
    )

    # Send task failure to Step Functions
    task_token = approval.get("step_functions_task_token", "")
    if task_token:
        send_task_success(task_token, "DENIED", action_req.approved_by)

    # Write denial audit log entry
    audit_entry = AuditLogEntry(
        action_id=approval.get("action_id", ""),
        timestamp=now_iso(),
        tool_name=approval.get("tool_name", ""),
        tool_parameters=approval.get("tool_parameters", {}),
        agent_session_id=approval.get("agent_session_id", ""),
        cedar_decision="DENY",
        cedar_reason=f"Denied by {action_req.approved_by}: {action_req.reason or 'No reason provided'}",
        risk_level=approval.get("risk_level", "MEDIUM"),
        final_status=ActionStatus.DENIED.value,
        approved_by=action_req.approved_by,
        approval_timestamp=now_iso(),
    )
    db.put_audit_log(audit_entry)

    logger.info(json.dumps({
        "level": "INFO",
        "service": "approvals",
        "operation": "deny",
        "approval_id": approval_id,
        "denied_by": action_req.approved_by,
    }))

    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({
            "success": True,
            "message": f"Action denied by {action_req.approved_by}",
            "approval_id": approval_id,
            "action_id": approval.get("action_id", ""),
        }),
    }


def _error_response(status_code: int, message: str) -> dict[str, Any]:
    """Create a standard error response."""
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps({
            "success": False,
            "error": message,
        }),
    }
