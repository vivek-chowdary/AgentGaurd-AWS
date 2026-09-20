"""
AgentGuard Log Result Handler — Called by Step Functions to log final outcomes.

Handles three scenarios:
1. log_success: Tool was approved and executed successfully
2. log_rejection: Tool was denied by human reviewer
3. log_timeout: Approval window expired
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.shared.constants import ActionStatus, ApprovalStatus
from backend.shared.dynamodb import get_dynamodb_client
from backend.shared.models import AuditLogEntry, now_iso

logger = logging.getLogger("agentguard.log_result")
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route to the appropriate logging handler based on action type."""
    try:
        action = event.get("action", "")
        action_id = event.get("action_id", "")
        tool_name = event.get("tool_name", "")
        approval_id = event.get("approval_id", "")

        logger.info(json.dumps({
            "level": "INFO",
            "service": "log_result",
            "operation": "handler_invoked",
            "action": action,
            "action_id": action_id,
            "tool_name": tool_name,
        }))

        if action == "log_success":
            return _log_success(event)
        elif action == "log_rejection":
            return _log_rejection(event)
        elif action == "log_timeout":
            return _log_timeout(event)
        else:
            logger.warning(json.dumps({
                "level": "WARNING",
                "service": "log_result",
                "operation": "unknown_action",
                "action": action,
            }))
            return {"status": "UNKNOWN_ACTION"}

    except Exception as e:
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "log_result",
            "operation": "handler_error",
            "error": str(e),
        }))
        raise


def _log_success(event: dict[str, Any]) -> dict[str, Any]:
    """Log a successful tool execution after human approval."""
    db = get_dynamodb_client()

    audit_entry = AuditLogEntry(
        action_id=event.get("action_id", ""),
        timestamp=now_iso(),
        tool_name=event.get("tool_name", ""),
        tool_parameters=event.get("tool_parameters", {}),
        cedar_decision="ALLOW",
        cedar_reason="Approved and executed via Step Functions workflow",
        risk_level=event.get("risk_level", "MEDIUM"),
        final_status=ActionStatus.EXECUTED.value,
        approved_by=event.get("approved_by", ""),
        approval_timestamp=now_iso(),
        execution_result=event.get("execution_result", {}),
    )
    db.put_audit_log(audit_entry)

    # Update the approval record
    approval_id = event.get("approval_id", "")
    if approval_id:
        db.update_approval_status(
            approval_id,
            ApprovalStatus.APPROVED.value,
            approved_by=event.get("approved_by", ""),
        )

    return {"status": "LOGGED", "final_status": ActionStatus.EXECUTED.value}


def _log_rejection(event: dict[str, Any]) -> dict[str, Any]:
    """Log a human denial of a pending action."""
    db = get_dynamodb_client()

    audit_entry = AuditLogEntry(
        action_id=event.get("action_id", ""),
        timestamp=now_iso(),
        tool_name=event.get("tool_name", ""),
        cedar_decision="DENY",
        cedar_reason="Denied by human reviewer via dashboard",
        risk_level=event.get("risk_level", "MEDIUM"),
        final_status=ActionStatus.DENIED.value,
        approved_by=event.get("denied_by", "dashboard_user"),
        approval_timestamp=now_iso(),
    )
    db.put_audit_log(audit_entry)

    # Update the approval record
    approval_id = event.get("approval_id", "")
    if approval_id:
        db.update_approval_status(
            approval_id,
            ApprovalStatus.DENIED.value,
            approved_by=event.get("denied_by", "dashboard_user"),
        )

    return {"status": "LOGGED", "final_status": ActionStatus.DENIED.value}


def _log_timeout(event: dict[str, Any]) -> dict[str, Any]:
    """Log an expired approval (15-minute timeout)."""
    db = get_dynamodb_client()

    audit_entry = AuditLogEntry(
        action_id=event.get("action_id", ""),
        timestamp=now_iso(),
        tool_name=event.get("tool_name", ""),
        cedar_decision="DENY",
        cedar_reason="Approval window expired (15-minute timeout)",
        risk_level=event.get("risk_level", "MEDIUM"),
        final_status=ActionStatus.EXPIRED.value,
    )
    db.put_audit_log(audit_entry)

    # Update the approval record
    approval_id = event.get("approval_id", "")
    if approval_id:
        db.update_approval_status(approval_id, ApprovalStatus.EXPIRED.value)

    return {"status": "LOGGED", "final_status": ActionStatus.EXPIRED.value}
