"""
AgentGuard Step Functions Workflow — Manages the human approval lifecycle.

Provides functions to:
- Start approval workflows
- Send approval/denial decisions (resume Step Functions)
- Handle expired tokens gracefully
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from backend.shared.constants import APPROVAL_WORKFLOW_ARN

logger = logging.getLogger("agentguard.workflow")
logger.setLevel(logging.INFO)

sfn_client = boto3.client("stepfunctions")


def start_approval_workflow(
    action_id: str,
    approval_id: str,
    tool_name: str,
    tool_parameters: dict[str, Any],
    agent_session_id: str = "",
) -> dict[str, Any]:
    """
    Start a Step Functions execution for the approval workflow.

    Args:
        action_id: The unique action ID
        approval_id: The unique approval ID
        tool_name: The tool that needs approval
        tool_parameters: The tool's parameters
        agent_session_id: The agent's session ID

    Returns:
        Dict with executionArn and startDate
    """
    try:
        workflow_arn = APPROVAL_WORKFLOW_ARN
        if not workflow_arn:
            logger.warning(json.dumps({
                "level": "WARNING",
                "service": "workflow",
                "operation": "start_workflow",
                "message": "No workflow ARN configured — skipping Step Functions",
            }))
            return {"executionArn": "", "status": "SKIPPED"}

        response = sfn_client.start_execution(
            stateMachineArn=workflow_arn,
            name=f"approval-{approval_id}",
            input=json.dumps({
                "action_id": action_id,
                "approval_id": approval_id,
                "tool_name": tool_name,
                "tool_parameters": tool_parameters,
                "agent_session_id": agent_session_id,
            }),
        )

        logger.info(json.dumps({
            "level": "INFO",
            "service": "workflow",
            "operation": "start_workflow",
            "approval_id": approval_id,
            "execution_arn": response["executionArn"],
        }))

        return {
            "executionArn": response["executionArn"],
            "startDate": str(response.get("startDate", "")),
            "status": "STARTED",
        }

    except ClientError as e:
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "workflow",
            "operation": "start_workflow_failed",
            "approval_id": approval_id,
            "error": str(e),
        }))
        raise


def send_task_success(task_token: str, decision: str, approved_by: str) -> dict[str, Any]:
    """
    Send a task success to Step Functions to resume the workflow.
    Used when a human approves an action.

    Args:
        task_token: The Step Functions task token
        decision: "APPROVED" or "DENIED"
        approved_by: Who made the decision

    Returns:
        Success confirmation
    """
    try:
        output = json.dumps({
            "decision": decision,
            "approved_by": approved_by,
        })

        if decision == "APPROVED":
            sfn_client.send_task_success(
                taskToken=task_token,
                output=output,
            )
        else:
            sfn_client.send_task_failure(
                taskToken=task_token,
                error="ActionDenied",
                cause=f"Action denied by {approved_by}",
            )

        logger.info(json.dumps({
            "level": "INFO",
            "service": "workflow",
            "operation": "send_task_result",
            "decision": decision,
            "approved_by": approved_by,
        }))

        return {"status": "SUCCESS", "decision": decision}

    except sfn_client.exceptions.TaskTimedOut:
        logger.warning(json.dumps({
            "level": "WARNING",
            "service": "workflow",
            "operation": "task_timed_out",
            "message": "Task token has expired",
        }))
        return {"status": "EXPIRED", "message": "Approval window has expired"}

    except sfn_client.exceptions.TaskDoesNotExist:
        logger.warning(json.dumps({
            "level": "WARNING",
            "service": "workflow",
            "operation": "task_not_found",
            "message": "Task token not found — may already be completed",
        }))
        return {"status": "NOT_FOUND", "message": "Task not found — may already be completed"}

    except ClientError as e:
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "workflow",
            "operation": "send_task_result_failed",
            "error": str(e),
        }))
        raise


def get_execution_status(execution_arn: str) -> Optional[dict[str, Any]]:
    """Get the current status of a Step Functions execution."""
    try:
        if not execution_arn:
            return None

        response = sfn_client.describe_execution(
            executionArn=execution_arn,
        )

        return {
            "status": response.get("status", "UNKNOWN"),
            "startDate": str(response.get("startDate", "")),
            "stopDate": str(response.get("stopDate", "")),
            "output": response.get("output", ""),
        }

    except ClientError as e:
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "workflow",
            "operation": "get_execution_status",
            "execution_arn": execution_arn,
            "error": str(e),
        }))
        return None
