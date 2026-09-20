"""
AgentGuard Demo Tools — 5 tools for the CustomerCare AI agent.

CRITICAL ARCHITECTURE: Every tool calls the AgentGuard interceptor BEFORE
executing any logic. No tool executes without first getting a decision
from the interceptor. This is the core of AgentGuard's authorization model.

Tool Risk Levels:
1. read_customer_profile  → LOW      → ALLOW immediately
2. create_draft_email     → LOW      → ALLOW immediately
3. send_email             → MEDIUM   → REQUIRE HUMAN APPROVAL
4. issue_refund           → DYNAMIC  → ALLOW (≤₹1K) / APPROVAL (₹1K-10K) / DENY (>₹10K)
5. delete_customer_record → CRITICAL → DENY always
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import boto3
from botocore.exceptions import ClientError

from backend.shared.constants import INTERCEPTOR_FUNCTION_NAME

logger = logging.getLogger("agentguard.tools")
logger.setLevel(logging.INFO)

# Lambda client for calling the interceptor
lambda_client = boto3.client("lambda")


# ============================================================
# INTERCEPTOR CALL — Every tool uses this
# ============================================================

def call_interceptor(
    tool_name: str,
    parameters: dict[str, Any],
    agent_session_id: str = "",
) -> dict[str, Any]:
    """
    Call the AgentGuard interceptor Lambda to get an authorization decision.
    This is the gateway — no tool executes without passing through here.

    Returns: {"decision": "ALLOW|REQUIRE_APPROVAL|DENY", "reason": "...", ...}
    """
    if not agent_session_id:
        agent_session_id = str(uuid.uuid4())

    payload = {
        "tool_name": tool_name,
        "parameters": parameters,
        "agent_session_id": agent_session_id,
    }

    try:
        response = lambda_client.invoke(
            FunctionName=INTERCEPTOR_FUNCTION_NAME,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )
        response_payload = json.loads(response["Payload"].read())

        logger.info(json.dumps({
            "level": "INFO",
            "service": "tools",
            "operation": "interceptor_response",
            "tool_name": tool_name,
            "decision": response_payload.get("decision", "UNKNOWN"),
        }))

        return response_payload

    except ClientError as e:
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "tools",
            "operation": "interceptor_call_failed",
            "tool_name": tool_name,
            "error": str(e),
        }))
        # Fail-safe: deny on interceptor failure
        return {
            "decision": "DENY",
            "reason": f"AgentGuard interceptor unavailable: {str(e)}",
            "risk_level": "HIGH",
        }


# ============================================================
# SIMULATED DATA — For the demo
# ============================================================

DEMO_CUSTOMERS = {
    "C123": {
        "customer_id": "C123",
        "name": "Rahul Sharma",
        "email": "rahul.sharma@example.com",
        "phone": "+91-9876543210",
        "tier": "Gold",
        "total_orders": 47,
        "total_spent": 125000.00,
        "joined": "2023-03-15",
        "address": "42 MG Road, Bengaluru, KA 560001",
        "recent_orders": [
            {"order_id": "ORD-789", "item": "Wireless Headphones", "amount": 3499, "status": "Delivered"},
            {"order_id": "ORD-790", "item": "Laptop Stand", "amount": 2199, "status": "Shipped"},
        ],
    },
    "C456": {
        "customer_id": "C456",
        "name": "Priya Patel",
        "email": "priya.patel@example.com",
        "phone": "+91-9123456789",
        "tier": "Platinum",
        "total_orders": 112,
        "total_spent": 450000.00,
        "joined": "2021-11-01",
        "address": "88 Anna Salai, Chennai, TN 600002",
        "recent_orders": [
            {"order_id": "ORD-991", "item": "Smart Watch Pro", "amount": 15999, "status": "Delivered"},
            {"order_id": "ORD-992", "item": "Running Shoes", "amount": 5499, "status": "Processing"},
        ],
    },
    "C789": {
        "customer_id": "C789",
        "name": "Amit Kumar",
        "email": "amit.kumar@example.com",
        "phone": "+91-9988776655",
        "tier": "Silver",
        "total_orders": 12,
        "total_spent": 28000.00,
        "joined": "2024-06-20",
        "address": "15 Connaught Place, New Delhi, DL 110001",
        "recent_orders": [
            {"order_id": "ORD-445", "item": "Bluetooth Speaker", "amount": 2999, "status": "Returned"},
        ],
    },
    "C999": {
        "customer_id": "C999",
        "name": "Sneha Reddy",
        "email": "sneha.reddy@example.com",
        "phone": "+91-9556677889",
        "tier": "Diamond",
        "total_orders": 234,
        "total_spent": 1250000.00,
        "joined": "2020-01-10",
        "address": "77 Banjara Hills, Hyderabad, TS 500034",
        "recent_orders": [
            {"order_id": "ORD-1100", "item": "4K OLED TV 65\"", "amount": 89999, "status": "Delivered"},
            {"order_id": "ORD-1101", "item": "Home Theater System", "amount": 45999, "status": "Delivered"},
        ],
    },
}


# ============================================================
# TOOL 1: read_customer_profile — LOW risk, ALLOW immediately
# ============================================================

def read_customer_profile(customer_id: str) -> str:
    """
    Look up a customer's profile information.
    Risk Level: LOW — read-only operation, always permitted.

    Args:
        customer_id: The customer ID to look up (e.g., "C123")

    Returns:
        Customer profile data as a formatted string
    """
    # Step 1: Call AgentGuard interceptor
    decision = call_interceptor(
        tool_name="read_customer_profile",
        parameters={"customer_id": customer_id},
    )

    # Step 2: Handle decision
    if decision.get("decision") == "ALLOW":
        # Execute the actual tool logic
        customer = DEMO_CUSTOMERS.get(customer_id)
        if customer:
            profile_lines = [
                f"📋 Customer Profile — {customer['name']}",
                f"   ID: {customer['customer_id']}",
                f"   Email: {customer['email']}",
                f"   Phone: {customer['phone']}",
                f"   Tier: {customer['tier']}",
                f"   Total Orders: {customer['total_orders']}",
                f"   Total Spent: ₹{customer['total_spent']:,.2f}",
                f"   Member Since: {customer['joined']}",
                f"   Address: {customer['address']}",
                f"   Recent Orders:",
            ]
            for order in customer.get("recent_orders", []):
                profile_lines.append(
                    f"     • {order['order_id']}: {order['item']} — "
                    f"₹{order['amount']:,} ({order['status']})"
                )
            return "\n".join(profile_lines)
        else:
            return f"Customer {customer_id} not found in the system."

    elif decision.get("decision") == "REQUIRE_APPROVAL":
        return f"Reading customer profile requires approval. Request ID: {decision.get('approval_id')}. The operation is paused."

    elif decision.get("decision") == "DENY":
        return f"Action blocked by AgentGuard policy: {decision.get('reason', 'Access denied')}"

    return f"Unexpected response from AgentGuard: {json.dumps(decision)}"


# ============================================================
# TOOL 2: create_draft_email — LOW risk, ALLOW immediately
# ============================================================

def create_draft_email(to: str, subject: str, body: str) -> str:
    """
    Create a draft email (does not send).
    Risk Level: LOW — no external side effects, always permitted.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content

    Returns:
        Confirmation with draft details
    """
    decision = call_interceptor(
        tool_name="create_draft_email",
        parameters={"to": to, "subject": subject, "body": body},
    )

    if decision.get("decision") == "ALLOW":
        draft_id = f"DRF-{uuid.uuid4().hex[:8].upper()}"
        return (
            f"✉️ Draft email created successfully!\n"
            f"   Draft ID: {draft_id}\n"
            f"   To: {to}\n"
            f"   Subject: {subject}\n"
            f"   Body: {body[:100]}{'...' if len(body) > 100 else ''}\n"
            f"   Status: DRAFT (not sent)"
        )

    elif decision.get("decision") == "REQUIRE_APPROVAL":
        return f"Creating draft email requires approval. Request ID: {decision.get('approval_id')}. The operation is paused."

    elif decision.get("decision") == "DENY":
        return f"Action blocked by AgentGuard policy: {decision.get('reason', 'Access denied')}"

    return f"Unexpected response from AgentGuard: {json.dumps(decision)}"


# ============================================================
# TOOL 3: send_email — MEDIUM risk, REQUIRE HUMAN APPROVAL
# ============================================================

def send_email(to: str, subject: str, body: str) -> str:
    """
    Send an email to a customer (simulated).
    Risk Level: MEDIUM — external communication requires human approval.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content

    Returns:
        Status message (pending approval or result)
    """
    decision = call_interceptor(
        tool_name="send_email",
        parameters={"to": to, "subject": subject, "body": body},
    )

    if decision.get("decision") == "ALLOW":
        msg_id = f"MSG-{uuid.uuid4().hex[:8].upper()}"
        return (
            f"📧 Email sent successfully!\n"
            f"   Message ID: {msg_id}\n"
            f"   To: {to}\n"
            f"   Subject: {subject}\n"
            f"   Status: DELIVERED (simulated)"
        )

    elif decision.get("decision") == "REQUIRE_APPROVAL":
        return (
            f"⏳ This email requires human approval before sending.\n"
            f"   Approval ID: {decision.get('approval_id')}\n"
            f"   To: {to}\n"
            f"   Subject: {subject}\n"
            f"   Reason: {decision.get('reason', 'Email sending requires approval')}\n"
            f"   Status: PENDING — waiting for a human reviewer to approve or deny this action."
        )

    elif decision.get("decision") == "DENY":
        return f"🚫 Action blocked by AgentGuard policy: {decision.get('reason', 'Access denied')}"

    return f"Unexpected response from AgentGuard: {json.dumps(decision)}"


# ============================================================
# TOOL 4: issue_refund — DYNAMIC risk based on amount
# ============================================================

def issue_refund(customer_id: str, amount: float, reason: str) -> str:
    """
    Issue a refund to a customer account (simulated).
    Risk Level: DYNAMIC
      - amount ≤ ₹1,000: LOW → ALLOW immediately
      - ₹1,000 < amount ≤ ₹10,000: MEDIUM → REQUIRE APPROVAL
      - amount > ₹10,000: HIGH → DENY immediately

    Args:
        customer_id: Customer to refund
        amount: Refund amount in INR
        reason: Reason for the refund

    Returns:
        Status message based on Cedar policy decision
    """
    decision = call_interceptor(
        tool_name="issue_refund",
        parameters={"customer_id": customer_id, "amount": amount, "reason": reason},
    )

    if decision.get("decision") == "ALLOW":
        txn_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
        return (
            f"💰 Refund processed successfully!\n"
            f"   Transaction ID: {txn_id}\n"
            f"   Customer: {customer_id}\n"
            f"   Amount: ₹{amount:,.2f}\n"
            f"   Reason: {reason}\n"
            f"   Status: COMPLETED"
        )

    elif decision.get("decision") == "REQUIRE_APPROVAL":
        return (
            f"⏳ This refund of ₹{amount:,.2f} requires human approval.\n"
            f"   Approval ID: {decision.get('approval_id')}\n"
            f"   Customer: {customer_id}\n"
            f"   Amount: ₹{amount:,.2f}\n"
            f"   Reason: {reason}\n"
            f"   Policy: {decision.get('reason', 'Amount exceeds automatic threshold')}\n"
            f"   Status: PENDING — waiting for a human reviewer."
        )

    elif decision.get("decision") == "DENY":
        return (
            f"🚫 Refund of ₹{amount:,.2f} BLOCKED by AgentGuard policy.\n"
            f"   Customer: {customer_id}\n"
            f"   Reason: {decision.get('reason', 'Amount exceeds maximum threshold')}\n"
            f"   This action cannot be approved or overridden."
        )

    return f"Unexpected response from AgentGuard: {json.dumps(decision)}"


# ============================================================
# TOOL 5: delete_customer_record — CRITICAL, DENY always
# ============================================================

def delete_customer_record(customer_id: str) -> str:
    """
    Permanently delete a customer record.
    Risk Level: CRITICAL — always blocked, no exceptions.

    Args:
        customer_id: Customer record to delete

    Returns:
        Block message (this tool never executes)
    """
    decision = call_interceptor(
        tool_name="delete_customer_record",
        parameters={"customer_id": customer_id},
    )

    if decision.get("decision") == "ALLOW":
        # This should NEVER happen — but handle it defensively
        return f"⚠️ Unexpected: delete_customer_record was allowed. Customer {customer_id} would be deleted."

    elif decision.get("decision") == "REQUIRE_APPROVAL":
        return f"⏳ Deletion requires approval. Request ID: {decision.get('approval_id')}."

    elif decision.get("decision") == "DENY":
        return (
            f"🛡️ Action BLOCKED by AgentGuard.\n"
            f"   Tool: delete_customer_record\n"
            f"   Customer: {customer_id}\n"
            f"   Policy: {decision.get('reason', 'This action is permanently restricted')}\n"
            f"   This action is permanently restricted by policy — no approval can override this."
        )

    return f"Unexpected response from AgentGuard: {json.dumps(decision)}"


# ============================================================
# TOOL DEFINITIONS — For Strands Agent registration
# ============================================================

TOOL_DEFINITIONS = [
    {
        "name": "read_customer_profile",
        "description": "Look up a customer's profile information including name, email, order history, and account details.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "The customer ID to look up (e.g., 'C123')",
                },
            },
            "required": ["customer_id"],
        },
        "function": read_customer_profile,
    },
    {
        "name": "create_draft_email",
        "description": "Create a draft email without sending it. Good for composing messages that need review.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body content"},
            },
            "required": ["to", "subject", "body"],
        },
        "function": create_draft_email,
    },
    {
        "name": "send_email",
        "description": "Send an email to a customer. This action requires human approval before the email is sent.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body content"},
            },
            "required": ["to", "subject", "body"],
        },
        "function": send_email,
    },
    {
        "name": "issue_refund",
        "description": "Issue a monetary refund to a customer's account. Small refunds are auto-approved, larger ones may need human approval or be blocked.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer to refund"},
                "amount": {"type": "number", "description": "Refund amount in INR (₹)"},
                "reason": {"type": "string", "description": "Reason for the refund"},
            },
            "required": ["customer_id", "amount", "reason"],
        },
        "function": issue_refund,
    },
    {
        "name": "delete_customer_record",
        "description": "Permanently delete a customer record from the system. WARNING: This action is always blocked by policy.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer record to delete"},
            },
            "required": ["customer_id"],
        },
        "function": delete_customer_record,
    },
]
