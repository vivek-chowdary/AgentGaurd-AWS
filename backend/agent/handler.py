"""
AgentGuard Agent Lambda Handler — Runs the CustomerCare AI agent.

This Lambda receives user messages and runs a Strands Agent with Bedrock Claude.
The agent has 5 tools, each gated by the AgentGuard interceptor.

Falls back to direct Bedrock converse API if Strands SDK is unavailable.
"""

from __future__ import annotations

import json
import logging
import traceback
import uuid
from typing import Any

import boto3
from pydantic import ValidationError

from backend.agent.prompts import CUSTOMER_CARE_SYSTEM_PROMPT
from backend.agent.tools import (
    TOOL_DEFINITIONS,
    create_draft_email,
    delete_customer_record,
    issue_refund,
    read_customer_profile,
    send_email,
)
from backend.shared.constants import BEDROCK_MODEL_ID, CORS_HEADERS
from backend.shared.models import AgentRequest

logger = logging.getLogger("agentguard.agent")
logger.setLevel(logging.INFO)

# Try to import Strands, fall back to direct Bedrock if unavailable
try:
    from strands import Agent, tool
    from strands.models.bedrock import BedrockModel
    STRANDS_AVAILABLE = True
    logger.info("Strands Agents SDK loaded successfully")
except ImportError:
    STRANDS_AVAILABLE = False
    logger.info("Strands Agents SDK not available — using direct Bedrock converse API")

bedrock_client = boto3.client("bedrock-runtime")

# Tool function map for the direct Bedrock approach
TOOL_FUNCTION_MAP = {
    "read_customer_profile": read_customer_profile,
    "create_draft_email": create_draft_email,
    "send_email": send_email,
    "issue_refund": issue_refund,
    "delete_customer_record": delete_customer_record,
}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Agent Lambda handler. Receives a user message and returns the agent's response.
    """
    try:
        # Parse the request
        if "body" in event:
            body = json.loads(event.get("body", "{}"))
        else:
            body = event

        request = AgentRequest(**body)

        logger.info(json.dumps({
            "level": "INFO",
            "service": "agent",
            "operation": "run_agent",
            "session_id": request.session_id,
            "message_preview": request.user_message[:100],
        }))

        # Run the agent
        if STRANDS_AVAILABLE:
            result = _run_strands_agent(request)
        else:
            result = _run_bedrock_converse(request)

        response = {
            "success": True,
            "response": result["response"],
            "session_id": request.session_id,
            "actions": result.get("actions", []),
        }

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(response),
        }

    except ValidationError as e:
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "agent",
            "operation": "validation_error",
            "error": str(e),
        }))
        return {
            "statusCode": 400,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "success": False,
                "error": f"Invalid request: {str(e)}",
            }),
        }

    except Exception as e:
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "agent",
            "operation": "internal_error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }))
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "success": False,
                "error": f"Agent error: {str(e)}",
            }),
        }


def _run_strands_agent(request: AgentRequest) -> dict[str, Any]:
    """Run the agent using Strands Agents SDK."""
    # Create Strands tool-decorated functions
    @tool
    def strands_read_customer_profile(customer_id: str) -> str:
        """Look up a customer's profile information."""
        return read_customer_profile(customer_id)

    @tool
    def strands_create_draft_email(to: str, subject: str, body: str) -> str:
        """Create a draft email without sending it."""
        return create_draft_email(to, subject, body)

    @tool
    def strands_send_email(to: str, subject: str, body: str) -> str:
        """Send an email to a customer. Requires human approval."""
        return send_email(to, subject, body)

    @tool
    def strands_issue_refund(customer_id: str, amount: float, reason: str) -> str:
        """Issue a refund to a customer account."""
        return issue_refund(customer_id, amount, reason)

    @tool
    def strands_delete_customer_record(customer_id: str) -> str:
        """Permanently delete a customer record. Always blocked by policy."""
        return delete_customer_record(customer_id)

    model = BedrockModel(
        model_id=BEDROCK_MODEL_ID,
        region_name="ap-south-1",
    )

    agent = Agent(
        model=model,
        system_prompt=CUSTOMER_CARE_SYSTEM_PROMPT,
        tools=[
            strands_read_customer_profile,
            strands_create_draft_email,
            strands_send_email,
            strands_issue_refund,
            strands_delete_customer_record,
        ],
    )

    response = agent(request.user_message)
    return {
        "response": str(response),
        "actions": [],
    }


def _run_bedrock_converse(request: AgentRequest) -> dict[str, Any]:
    """
    Run the agent using direct Bedrock Converse API with tool use.
    This is the fallback when Strands SDK is not available.
    Implements a full tool-use loop.
    """
    # Define tools for Bedrock converse API
    tool_config = {
        "tools": [
            {
                "toolSpec": {
                    "name": td["name"],
                    "description": td["description"],
                    "inputSchema": {"json": td["parameters"]},
                }
            }
            for td in TOOL_DEFINITIONS
        ]
    }

    messages = [
        {
            "role": "user",
            "content": [{"text": request.user_message}],
        }
    ]

    actions_taken: list[dict[str, Any]] = []
    max_iterations = 10  # Safety limit to prevent infinite loops

    for iteration in range(max_iterations):
        # Call Bedrock
        response = bedrock_client.converse(
            modelId=BEDROCK_MODEL_ID,
            system=[{"text": CUSTOMER_CARE_SYSTEM_PROMPT}],
            messages=messages,
            toolConfig=tool_config,
        )

        output = response.get("output", {})
        message = output.get("message", {})
        stop_reason = response.get("stopReason", "")

        # Add assistant message to conversation
        messages.append(message)

        # Check if model wants to use tools
        if stop_reason == "tool_use":
            tool_results = []
            for content_block in message.get("content", []):
                if "toolUse" in content_block:
                    tool_use = content_block["toolUse"]
                    tool_name = tool_use["name"]
                    tool_input = tool_use.get("input", {})
                    tool_use_id = tool_use["toolUseId"]

                    logger.info(json.dumps({
                        "level": "INFO",
                        "service": "agent",
                        "operation": "tool_call",
                        "tool_name": tool_name,
                        "tool_input": str(tool_input),
                        "iteration": iteration,
                    }))

                    # Execute the tool (which calls the interceptor internally)
                    tool_fn = TOOL_FUNCTION_MAP.get(tool_name)
                    if tool_fn:
                        try:
                            result = tool_fn(**tool_input)
                        except Exception as e:
                            result = f"Tool execution error: {str(e)}"
                    else:
                        result = f"Unknown tool: {tool_name}"

                    actions_taken.append({
                        "tool_name": tool_name,
                        "parameters": tool_input,
                        "result_preview": result[:200],
                    })

                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use_id,
                            "content": [{"text": result}],
                        }
                    })

            # Add tool results as a user message
            messages.append({
                "role": "user",
                "content": tool_results,
            })

        elif stop_reason == "end_turn":
            # Model is done — extract final text response
            final_text = ""
            for content_block in message.get("content", []):
                if "text" in content_block:
                    final_text += content_block["text"]

            return {
                "response": final_text,
                "actions": actions_taken,
            }

        else:
            # Unexpected stop reason
            logger.warning(json.dumps({
                "level": "WARNING",
                "service": "agent",
                "operation": "unexpected_stop",
                "stop_reason": stop_reason,
                "iteration": iteration,
            }))
            break

    # If we hit max iterations, return what we have
    return {
        "response": "I apologize, but I wasn't able to complete all the actions. Please try again with a simpler request.",
        "actions": actions_taken,
    }
