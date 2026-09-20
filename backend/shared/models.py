"""
AgentGuard Pydantic Models — Strict input validation for all data types.
Every API endpoint validates input through these models before processing.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


def now_iso() -> str:
    """Return current UTC time in ISO8601 format."""
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# REQUEST MODELS
# ============================================================

class ToolCallRequest(BaseModel):
    """Incoming tool call to be evaluated by the interceptor."""
    tool_name: str = Field(..., description="Name of the tool being called")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Tool call parameters")
    agent_session_id: str = Field(default_factory=generate_uuid, description="Agent session ID")

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        valid_tools = {
            "read_customer_profile",
            "create_draft_email",
            "send_email",
            "issue_refund",
            "delete_customer_record",
        }
        if v not in valid_tools:
            raise ValueError(f"Unknown tool: {v}. Valid tools: {valid_tools}")
        return v


class AgentRequest(BaseModel):
    """Request to run the Strands agent."""
    user_message: str = Field(..., min_length=1, description="User's message to the agent")
    session_id: str = Field(default_factory=generate_uuid, description="Session ID")


class ApprovalActionRequest(BaseModel):
    """Request to approve or deny a pending action."""
    approved_by: str = Field(default="dashboard_user", description="Who is approving/denying")
    reason: Optional[str] = Field(default=None, description="Optional reason for decision")


# ============================================================
# DECISION MODELS
# ============================================================

class CedarDecision(BaseModel):
    """Result of Cedar policy evaluation."""
    decision: str = Field(..., description="ALLOW, REQUIRE_APPROVAL, or DENY")
    reason: str = Field(default="", description="Human-readable explanation")
    risk_level: str = Field(default="LOW", description="Risk level of the action")
    approval_id: Optional[str] = Field(default=None, description="Approval ID if REQUIRE_APPROVAL")


# ============================================================
# DATABASE MODELS
# ============================================================

class AuditLogEntry(BaseModel):
    """A record in the agentguard-audit-log DynamoDB table."""
    action_id: str = Field(default_factory=generate_uuid)
    timestamp: str = Field(default_factory=now_iso)
    tool_name: str
    tool_parameters: dict[str, Any] = Field(default_factory=dict)
    agent_session_id: str = Field(default_factory=generate_uuid)
    cedar_decision: str = Field(default="")
    cedar_reason: str = Field(default="")
    risk_level: str = Field(default="LOW")
    final_status: str = Field(default="ALLOWED")
    approved_by: Optional[str] = None
    approval_timestamp: Optional[str] = None
    execution_result: Optional[dict[str, Any]] = None

    def to_dynamo_item(self) -> dict[str, Any]:
        """Convert to DynamoDB-compatible dict (no None values)."""
        item = self.model_dump()
        # DynamoDB doesn't accept None — remove null fields
        return {k: v for k, v in item.items() if v is not None}


class PendingApproval(BaseModel):
    """A record in the agentguard-pending-approvals DynamoDB table."""
    approval_id: str = Field(default_factory=generate_uuid)
    action_id: str = Field(default_factory=generate_uuid)
    tool_name: str
    tool_parameters: dict[str, Any] = Field(default_factory=dict)
    step_functions_task_token: str = Field(default="")
    step_functions_execution_arn: str = Field(default="")
    status: str = Field(default="PENDING")
    created_at: str = Field(default_factory=now_iso)
    expires_at: str = Field(default="")
    risk_level: str = Field(default="MEDIUM")
    cedar_reason: str = Field(default="")
    agent_session_id: str = Field(default_factory=generate_uuid)

    def to_dynamo_item(self) -> dict[str, Any]:
        """Convert to DynamoDB-compatible dict (no None values)."""
        item = self.model_dump()
        return {k: v for k, v in item.items() if v is not None}


# ============================================================
# RESPONSE MODELS
# ============================================================

class AgentResponse(BaseModel):
    """Response from the Strands agent."""
    response: str = Field(default="", description="Agent's text response")
    session_id: str = Field(default="", description="Session ID")
    actions: list[dict[str, Any]] = Field(default_factory=list, description="Actions taken")


class InterceptorResponse(BaseModel):
    """Response from the interceptor Lambda."""
    decision: str
    reason: str = ""
    action_id: str = ""
    approval_id: Optional[str] = None
    risk_level: str = "LOW"


class ApiResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    data: Any = None
    error: Optional[str] = None
    message: str = ""
