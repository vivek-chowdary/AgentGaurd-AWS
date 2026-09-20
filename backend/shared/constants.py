"""
AgentGuard Constants — All configuration values loaded from environment variables.
No hardcoded ARNs, table names, or model IDs anywhere in the codebase.
"""

import os
from enum import Enum


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

def get_env(name: str, default: str = "") -> str:
    """Get environment variable with optional default."""
    return os.environ.get(name, default)


# DynamoDB Table Names
AUDIT_TABLE_NAME = get_env("AUDIT_TABLE_NAME", "agentguard-audit-log")
APPROVALS_TABLE_NAME = get_env("APPROVALS_TABLE_NAME", "agentguard-pending-approvals")

# Step Functions
APPROVAL_WORKFLOW_ARN = get_env("APPROVAL_WORKFLOW_ARN")

# SNS
SNS_TOPIC_ARN = get_env("SNS_TOPIC_ARN")

# EventBridge
EVENT_BUS_NAME = get_env("EVENT_BUS_NAME", "agentguard-events")

# Bedrock
BEDROCK_MODEL_ID = get_env("BEDROCK_MODEL_ID", "us.amazon.nova-2-lite-v1:0")

# Lambda Function Names (for inter-Lambda invocation)
INTERCEPTOR_FUNCTION_NAME = get_env("INTERCEPTOR_FUNCTION_NAME", "agentguard-interceptor")
EXECUTE_TOOL_FUNCTION_NAME = get_env("EXECUTE_TOOL_FUNCTION_NAME", "agentguard-execute-tool")

# AWS
AWS_REGION = get_env("AWS_REGION", get_env("AWS_DEFAULT_REGION", "us-east-1"))

# ============================================================
# ENUMS
# ============================================================

class RiskLevel(str, Enum):
    """Risk classification for tool operations."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CedarDecisionType(str, Enum):
    """Possible Cedar policy evaluation outcomes."""
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"


class ActionStatus(str, Enum):
    """Final status of an agent action."""
    ALLOWED = "ALLOWED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    BLOCKED = "BLOCKED"
    EXPIRED = "EXPIRED"
    EXECUTED = "EXECUTED"


class ApprovalStatus(str, Enum):
    """Status of a pending approval."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"


# ============================================================
# TOOL RISK MAPPINGS
# ============================================================

TOOL_RISK_MAP: dict[str, RiskLevel] = {
    "read_customer_profile": RiskLevel.LOW,
    "create_draft_email": RiskLevel.LOW,
    "send_email": RiskLevel.MEDIUM,
    "issue_refund": RiskLevel.MEDIUM,       # Base risk; actual risk depends on amount
    "delete_customer_record": RiskLevel.CRITICAL,
}

# ============================================================
# APPROVAL SETTINGS
# ============================================================

APPROVAL_TIMEOUT_SECONDS = 900   # 15 minutes
APPROVAL_TIMEOUT_MINUTES = 15

# ============================================================
# DynamoDB INDEX NAMES
# ============================================================

AUDIT_STATUS_INDEX = "status-index"
APPROVALS_STATUS_INDEX = "status-index"

# ============================================================
# CORS HEADERS (for Lambda proxy responses)
# ============================================================

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}
