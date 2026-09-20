"""
AgentGuard Execute Tool Handler — Called by Step Functions after approval.

This Lambda is invoked by the Step Functions state machine in two contexts:
1. WaitForApproval state: Stores the task token and waits
2. ExecuteTool state: Actually executes the approved tool
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from backend.shared.constants import CORS_HEADERS
from backend.shared.dynamodb import get_dynamodb_client

logger = logging.getLogger("agentguard.execute_tool")
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Handle tool execution after Step Functions approval.

    When called from WaitForApproval state, stores the task token in DynamoDB.
    When called from ExecuteTool state, simulates tool execution.
    """
    try:
        action = event.get("action", "")
        task_token = event.get("task_token", "")
        approval_id = event.get("approval_id", "")
        action_id = event.get("action_id", "")
        tool_name = event.get("tool_name", "")
        tool_parameters = event.get("tool_parameters", {})

        logger.info(json.dumps({
            "level": "INFO",
            "service": "execute_tool",
            "operation": "handler_invoked",
            "action": action,
            "approval_id": approval_id,
            "tool_name": tool_name,
        }))

        # WaitForApproval state: store the task token
        if task_token and not action:
            return _store_task_token(approval_id, task_token)

        # ExecuteTool state: execute the approved tool
        if action == "execute":
            return _execute_tool(action_id, tool_name, tool_parameters, event.get("approved_by", ""))

        # Unknown action
        return {"status": "UNKNOWN_ACTION", "action": action}

    except Exception as e:
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "execute_tool",
            "operation": "handler_error",
            "error": str(e),
        }))
        raise


def _store_task_token(approval_id: str, task_token: str) -> dict[str, Any]:
    """Store the Step Functions task token in the pending approval record."""
    db = get_dynamodb_client()

    try:
        from backend.shared.constants import APPROVALS_TABLE_NAME
        import boto3

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(APPROVALS_TABLE_NAME)

        table.update_item(
            Key={"approval_id": approval_id},
            UpdateExpression="SET step_functions_task_token = :token",
            ExpressionAttributeValues={":token": task_token},
        )

        logger.info(json.dumps({
            "level": "INFO",
            "service": "execute_tool",
            "operation": "store_task_token",
            "approval_id": approval_id,
        }))

        return {"status": "TOKEN_STORED", "approval_id": approval_id}

    except Exception as e:
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "execute_tool",
            "operation": "store_task_token_failed",
            "approval_id": approval_id,
            "error": str(e),
        }))
        raise


def _execute_tool(
    action_id: str,
    tool_name: str,
    tool_parameters: dict[str, Any],
    approved_by: str,
) -> dict[str, Any]:
    """
    Execute the approved tool (simulated).
    This is called by Step Functions after human approval.
    """
    execution_id = f"EXE-{uuid.uuid4().hex[:8].upper()}"

    # Simulate tool execution based on tool name
    if tool_name == "send_email":
        result = {
            "status": "SENT",
            "message_id": f"MSG-{uuid.uuid4().hex[:8].upper()}",
            "to": tool_parameters.get("to", ""),
            "subject": tool_parameters.get("subject", ""),
        }
    elif tool_name == "issue_refund":
        result = {
            "status": "COMPLETED",
            "transaction_id": f"TXN-{uuid.uuid4().hex[:8].upper()}",
            "customer_id": tool_parameters.get("customer_id", ""),
            "amount": tool_parameters.get("amount", 0),
        }
    else:
        result = {
            "status": "EXECUTED",
            "tool_name": tool_name,
            "execution_id": execution_id,
        }

    logger.info(json.dumps({
        "level": "INFO",
        "service": "execute_tool",
        "operation": "tool_executed",
        "action_id": action_id,
        "tool_name": tool_name,
        "approved_by": approved_by,
        "execution_id": execution_id,
    }))

    return {
        "status": "EXECUTED",
        "execution_id": execution_id,
        "result": result,
        "action_id": action_id,
        "tool_name": tool_name,
    }
