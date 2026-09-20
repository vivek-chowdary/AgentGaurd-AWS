"""
AgentGuard Interceptor Lambda Handler — The authorization gateway.

This is the core of AgentGuard. Every tool call from the AI agent passes through
this handler BEFORE execution. It:
1. Validates the incoming tool call request
2. Evaluates Cedar policies to produce a decision
3. Routes based on decision:
   - ALLOW → logs to audit table, returns allow
   - REQUIRE_APPROVAL → starts Step Functions workflow, logs as PENDING
   - DENY → logs as BLOCKED, returns deny with reason
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError

from backend.interceptor.cedar_evaluator import evaluate_cedar_policy
from backend.shared.constants import (
    APPROVAL_TIMEOUT_SECONDS,
    APPROVAL_WORKFLOW_ARN,
    CORS_HEADERS,
    EVENT_BUS_NAME,
    SNS_TOPIC_ARN,
    ActionStatus,
    CedarDecisionType,
)
from backend.shared.dynamodb import get_dynamodb_client
from backend.shared.models import (
    AuditLogEntry,
    CedarDecision,
    PendingApproval,
    ToolCallRequest,
    now_iso,
)

logger = logging.getLogger("agentguard.interceptor")
logger.setLevel(logging.INFO)

# AWS clients (initialized outside handler for Lambda warm starts)
sfn_client = boto3.client("stepfunctions")
events_client = boto3.client("events")
sns_client = boto3.client("sns")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Main interceptor handler. Accepts tool call requests from the agent
    and returns authorization decisions.

    Can be invoked directly (Lambda-to-Lambda) or via API Gateway.
    """
    try:
        # Parse the request — handle both direct invoke and API Gateway
        if "body" in event:
            # API Gateway proxy format
            body = json.loads(event.get("body", "{}"))
        else:
            # Direct Lambda invocation
            body = event

        # Validate input with Pydantic
        request = ToolCallRequest(**body)

        logger.info(json.dumps({
            "level": "INFO",
            "service": "interceptor",
            "operation": "evaluate_request",
            "tool_name": request.tool_name,
            "parameters": str(request.parameters),
            "session_id": request.agent_session_id,
        }))

        # Evaluate Cedar policy
        decision = evaluate_cedar_policy(
            tool_name=request.tool_name,
            parameters=request.parameters,
        )

        # Route based on decision
        if decision.decision == CedarDecisionType.ALLOW.value:
            result = _handle_allow(request, decision)
        elif decision.decision == CedarDecisionType.REQUIRE_APPROVAL.value:
            result = _handle_require_approval(request, decision)
        elif decision.decision == CedarDecisionType.DENY.value:
            result = _handle_deny(request, decision)
        else:
            # Should never happen — default to deny
            result = _handle_deny(request, CedarDecision(
                decision=CedarDecisionType.DENY.value,
                reason=f"Unknown Cedar decision type: {decision.decision}",
                risk_level="HIGH",
            ))

        logger.info(json.dumps({
            "level": "INFO",
            "service": "interceptor",
            "operation": "decision_made",
            "tool_name": request.tool_name,
            "decision": result.get("decision", "UNKNOWN"),
            "action_id": result.get("action_id", ""),
        }))

        # Return response (works for both direct invoke and API Gateway)
        if "body" in event:
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps(result),
            }
        return result

    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "interceptor",
            "operation": "validation_error",
            "error": error_msg,
        }))
        if "body" in event:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": error_msg}),
            }
        return {"error": error_msg, "decision": "DENY"}

    except Exception as e:
        error_msg = f"Internal error: {str(e)}"
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "interceptor",
            "operation": "internal_error",
            "error": error_msg,
        }))
        if "body" in event:
            return {
                "statusCode": 500,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": error_msg}),
            }
        return {"error": error_msg, "decision": "DENY"}


def _handle_allow(request: ToolCallRequest, decision: CedarDecision) -> dict[str, Any]:
    """Handle ALLOW decision: log to audit table and return."""
    db = get_dynamodb_client()
    action_id = str(uuid.uuid4())

    # Write immutable audit record
    audit_entry = AuditLogEntry(
        action_id=action_id,
        timestamp=now_iso(),
        tool_name=request.tool_name,
        tool_parameters=request.parameters,
        agent_session_id=request.agent_session_id,
        cedar_decision=CedarDecisionType.ALLOW.value,
        cedar_reason=decision.reason,
        risk_level=decision.risk_level,
        final_status=ActionStatus.ALLOWED.value,
    )
    db.put_audit_log(audit_entry)

    return {
        "decision": CedarDecisionType.ALLOW.value,
        "reason": decision.reason,
        "action_id": action_id,
        "risk_level": decision.risk_level,
    }


def _handle_require_approval(request: ToolCallRequest, decision: CedarDecision) -> dict[str, Any]:
    """
    Handle REQUIRE_APPROVAL decision:
    1. Create pending approval record
    2. Start Step Functions workflow
    3. Log to audit table as PENDING
    4. Send EventBridge event → SNS notification
    """
    db = get_dynamodb_client()
    action_id = str(uuid.uuid4())
    approval_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(seconds=APPROVAL_TIMEOUT_SECONDS)).isoformat()

    # Start Step Functions execution
    execution_arn = ""
    try:
        workflow_arn = APPROVAL_WORKFLOW_ARN
        if workflow_arn:
            sfn_response = sfn_client.start_execution(
                stateMachineArn=workflow_arn,
                name=f"approval-{approval_id}",
                input=json.dumps({
                    "action_id": action_id,
                    "approval_id": approval_id,
                    "tool_name": request.tool_name,
                    "tool_parameters": request.parameters,
                    "agent_session_id": request.agent_session_id,
                }),
            )
            execution_arn = sfn_response.get("executionArn", "")
            logger.info(json.dumps({
                "level": "INFO",
                "service": "interceptor",
                "operation": "start_workflow",
                "approval_id": approval_id,
                "execution_arn": execution_arn,
            }))
    except ClientError as e:
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "interceptor",
            "operation": "start_workflow_failed",
            "approval_id": approval_id,
            "error": str(e),
        }))
        # Continue without Step Functions — approval still works via DynamoDB

    # Write pending approval record
    pending = PendingApproval(
        approval_id=approval_id,
        action_id=action_id,
        tool_name=request.tool_name,
        tool_parameters=request.parameters,
        step_functions_task_token="",  # Will be set by the WaitForApproval state
        step_functions_execution_arn=execution_arn,
        status="PENDING",
        created_at=now.isoformat(),
        expires_at=expires_at,
        risk_level=decision.risk_level,
        cedar_reason=decision.reason,
        agent_session_id=request.agent_session_id,
    )
    db.put_pending_approval(pending)

    # Write audit log entry as PENDING
    audit_entry = AuditLogEntry(
        action_id=action_id,
        timestamp=now_iso(),
        tool_name=request.tool_name,
        tool_parameters=request.parameters,
        agent_session_id=request.agent_session_id,
        cedar_decision=CedarDecisionType.REQUIRE_APPROVAL.value,
        cedar_reason=decision.reason,
        risk_level=decision.risk_level,
        final_status=ActionStatus.PENDING.value,
    )
    db.put_audit_log(audit_entry)

    # Publish EventBridge event for notifications
    _publish_approval_event(approval_id, action_id, request, decision)

    return {
        "decision": CedarDecisionType.REQUIRE_APPROVAL.value,
        "reason": decision.reason,
        "action_id": action_id,
        "approval_id": approval_id,
        "risk_level": decision.risk_level,
        "expires_at": expires_at,
    }


def _handle_deny(request: ToolCallRequest, decision: CedarDecision) -> dict[str, Any]:
    """Handle DENY decision: log to audit table as BLOCKED and return."""
    db = get_dynamodb_client()
    action_id = str(uuid.uuid4())

    # Write immutable audit record
    audit_entry = AuditLogEntry(
        action_id=action_id,
        timestamp=now_iso(),
        tool_name=request.tool_name,
        tool_parameters=request.parameters,
        agent_session_id=request.agent_session_id,
        cedar_decision=CedarDecisionType.DENY.value,
        cedar_reason=decision.reason,
        risk_level=decision.risk_level,
        final_status=ActionStatus.BLOCKED.value,
    )
    db.put_audit_log(audit_entry)

    return {
        "decision": CedarDecisionType.DENY.value,
        "reason": decision.reason,
        "action_id": action_id,
        "risk_level": decision.risk_level,
    }


def _publish_approval_event(
    approval_id: str,
    action_id: str,
    request: ToolCallRequest,
    decision: CedarDecision,
) -> None:
    """Publish an EventBridge event for the approval requirement. Sends SNS notification."""
    try:
        # EventBridge event
        event_bus = EVENT_BUS_NAME
        if event_bus:
            events_client.put_events(
                Entries=[
                    {
                        "Source": "agentguard.interceptor",
                        "DetailType": "ApprovalRequired",
                        "EventBusName": event_bus,
                        "Detail": json.dumps({
                            "approval_id": approval_id,
                            "action_id": action_id,
                            "tool_name": request.tool_name,
                            "tool_parameters": request.parameters,
                            "risk_level": decision.risk_level,
                            "reason": decision.reason,
                        }),
                    }
                ],
            )
            logger.info(json.dumps({
                "level": "INFO",
                "service": "interceptor",
                "operation": "publish_event",
                "approval_id": approval_id,
            }))

        # Direct SNS notification (backup — EventBridge rule also triggers SNS)
        topic_arn = SNS_TOPIC_ARN
        if topic_arn:
            sns_client.publish(
                TopicArn=topic_arn,
                Subject=f"🔔 AgentGuard: Approval Required — {request.tool_name}",
                Message=(
                    f"AgentGuard requires human approval for the following action:\n\n"
                    f"Tool: {request.tool_name}\n"
                    f"Parameters: {json.dumps(request.parameters, indent=2)}\n"
                    f"Risk Level: {decision.risk_level}\n"
                    f"Reason: {decision.reason}\n\n"
                    f"Approval ID: {approval_id}\n"
                    f"Action ID: {action_id}\n\n"
                    f"Please approve or deny this action in the AgentGuard dashboard."
                ),
            )
    except ClientError as e:
        # Don't fail the request if notification fails
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "interceptor",
            "operation": "publish_event_failed",
            "approval_id": approval_id,
            "error": str(e),
        }))
