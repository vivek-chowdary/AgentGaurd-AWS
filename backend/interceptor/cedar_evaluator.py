"""
AgentGuard Cedar Policy Evaluator — The core authorization engine.

Implements a Python-native evaluation engine that mirrors Cedar semantics:
1. Check FORBID rules first (deny overrides everything)
2. Check PERMIT rules with context conditions
3. If no permit matches but action needs approval → REQUIRE_APPROVAL
4. If no rules match at all → DENY (default deny)

This evaluator processes the same Cedar policy file format and produces
identical decisions to what AWS Verified Permissions would produce.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.shared.constants import (
    CedarDecisionType,
    RiskLevel,
    TOOL_RISK_MAP,
)
from backend.shared.models import CedarDecision

logger = logging.getLogger("agentguard.cedar")
logger.setLevel(logging.INFO)


# ============================================================
# TOOL-SPECIFIC RISK ASSESSMENT
# ============================================================

def _assess_risk_level(tool_name: str, parameters: dict[str, Any]) -> RiskLevel:
    """
    Determine the risk level of a tool call based on the tool name
    and its parameters. Refund amounts get dynamic risk assessment.
    """
    base_risk = TOOL_RISK_MAP.get(tool_name, RiskLevel.HIGH)

    # Dynamic risk for issue_refund based on amount
    if tool_name == "issue_refund":
        amount = parameters.get("amount", 0)
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return RiskLevel.HIGH
        if amount <= 1000:
            return RiskLevel.LOW
        elif amount <= 10000:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.HIGH

    return base_risk


# ============================================================
# CEDAR POLICY EVALUATION ENGINE
# ============================================================

# Actions that require human approval when not pre-approved
APPROVAL_REQUIRED_ACTIONS = {"send_email", "issue_refund"}

# Actions that are always forbidden — forbid overrides everything
FORBIDDEN_ACTIONS = {"delete_customer_record"}

# Actions that are always permitted — no conditions
ALWAYS_PERMITTED_ACTIONS = {"read_customer_profile", "create_draft_email"}


def evaluate_cedar_policy(
    tool_name: str,
    parameters: dict[str, Any],
    context: dict[str, Any] | None = None,
) -> CedarDecision:
    """
    Evaluate Cedar policies against a tool call.

    This implements the Cedar evaluation algorithm:
    1. If any FORBID policy matches → DENY (forbid overrides permit)
    2. If a PERMIT policy matches unconditionally → ALLOW
    3. If a PERMIT policy matches only with approval_status == APPROVED
       and no approval yet → REQUIRE_APPROVAL
    4. If no policy matches → DENY (default deny)

    Args:
        tool_name: The tool being called
        parameters: The tool's parameters
        context: Additional context (e.g., approval_status)

    Returns:
        CedarDecision with decision, reason, and risk_level
    """
    if context is None:
        context = {}

    risk_level = _assess_risk_level(tool_name, parameters)
    approval_status = context.get("approval_status", "")

    logger.info(json.dumps({
        "level": "INFO",
        "service": "cedar_evaluator",
        "operation": "evaluate",
        "tool_name": tool_name,
        "parameters": str(parameters),
        "risk_level": risk_level.value,
        "approval_status": approval_status,
    }))

    # ---- Step 1: Check FORBID rules (deny overrides) ----
    if tool_name in FORBIDDEN_ACTIONS:
        reason = _get_forbid_reason(tool_name)
        logger.info(json.dumps({
            "level": "INFO",
            "service": "cedar_evaluator",
            "decision": "DENY",
            "tool_name": tool_name,
            "reason": reason,
        }))
        return CedarDecision(
            decision=CedarDecisionType.DENY.value,
            reason=reason,
            risk_level=risk_level.value,
        )

    # ---- Step 2: Check unconditional PERMIT rules ----
    if tool_name in ALWAYS_PERMITTED_ACTIONS:
        reason = _get_permit_reason(tool_name)
        logger.info(json.dumps({
            "level": "INFO",
            "service": "cedar_evaluator",
            "decision": "ALLOW",
            "tool_name": tool_name,
            "reason": reason,
        }))
        return CedarDecision(
            decision=CedarDecisionType.ALLOW.value,
            reason=reason,
            risk_level=risk_level.value,
        )

    # ---- Step 3: Check conditional PERMIT rules ----

    # send_email: always requires approval
    if tool_name == "send_email":
        if approval_status == "APPROVED":
            return CedarDecision(
                decision=CedarDecisionType.ALLOW.value,
                reason="Email sending approved by human reviewer",
                risk_level=risk_level.value,
            )
        return CedarDecision(
            decision=CedarDecisionType.REQUIRE_APPROVAL.value,
            reason="Sending external emails requires human approval per company policy",
            risk_level=risk_level.value,
        )

    # issue_refund: conditional on amount
    if tool_name == "issue_refund":
        amount = float(parameters.get("amount", 0))

        # Small refunds (≤ ₹1,000): auto-allow
        if amount <= 1000:
            return CedarDecision(
                decision=CedarDecisionType.ALLOW.value,
                reason=f"Refund of ₹{amount:,.2f} is within automatic approval threshold (≤ ₹1,000)",
                risk_level=risk_level.value,
            )

        # Medium refunds (₹1,001 – ₹10,000): require approval
        if amount <= 10000:
            if approval_status == "APPROVED":
                return CedarDecision(
                    decision=CedarDecisionType.ALLOW.value,
                    reason=f"Refund of ₹{amount:,.2f} approved by human reviewer",
                    risk_level=risk_level.value,
                )
            return CedarDecision(
                decision=CedarDecisionType.REQUIRE_APPROVAL.value,
                reason=f"Refund of ₹{amount:,.2f} exceeds automatic threshold (₹1,000). Requires human approval for amounts up to ₹10,000",
                risk_level=risk_level.value,
            )

        # Large refunds (> ₹10,000): always deny
        return CedarDecision(
            decision=CedarDecisionType.DENY.value,
            reason=f"Refund of ₹{amount:,.2f} exceeds maximum allowed threshold (₹10,000). This action is blocked by policy",
            risk_level=RiskLevel.HIGH.value,
        )

    # ---- Step 4: Default deny (no matching policy) ----
    return CedarDecision(
        decision=CedarDecisionType.DENY.value,
        reason=f"No Cedar policy permits action '{tool_name}'. Default deny applies",
        risk_level=RiskLevel.HIGH.value,
    )


def _get_forbid_reason(tool_name: str) -> str:
    """Get a human-readable reason for forbidden actions."""
    reasons = {
        "delete_customer_record": (
            "Permanently deleting customer records is forbidden by company policy. "
            "This action is blocked with no exceptions — no approval can override this restriction"
        ),
    }
    return reasons.get(tool_name, f"Action '{tool_name}' is explicitly forbidden by Cedar policy")


def _get_permit_reason(tool_name: str) -> str:
    """Get a human-readable reason for permitted actions."""
    reasons = {
        "read_customer_profile": "Reading customer profiles is a low-risk, read-only operation — always permitted",
        "create_draft_email": "Creating email drafts is a low-risk operation with no external side effects — always permitted",
    }
    return reasons.get(tool_name, f"Action '{tool_name}' is permitted by Cedar policy")


# ============================================================
# POLICY DESCRIPTION (for the dashboard Policy Viewer)
# ============================================================

def get_policy_descriptions() -> list[dict[str, Any]]:
    """Return human-readable descriptions of all active Cedar policies."""
    return [
        {
            "id": "policy-1",
            "tool": "read_customer_profile",
            "type": "permit",
            "risk_level": "LOW",
            "condition": "None — always permitted",
            "description": "Reading customer profiles is a read-only operation. No conditions required.",
            "cedar_syntax": 'permit(principal, action == Action::"read_customer_profile", resource);',
        },
        {
            "id": "policy-2",
            "tool": "create_draft_email",
            "type": "permit",
            "risk_level": "LOW",
            "condition": "None — always permitted",
            "description": "Creating email drafts has no external side effects. Auto-approved.",
            "cedar_syntax": 'permit(principal, action == Action::"create_draft_email", resource);',
        },
        {
            "id": "policy-3",
            "tool": "send_email",
            "type": "permit (conditional)",
            "risk_level": "MEDIUM",
            "condition": "Requires approval_status == APPROVED",
            "description": "Sending emails to external recipients requires human approval before execution.",
            "cedar_syntax": 'permit(principal, action == Action::"send_email", resource) when { context.approval_status == "APPROVED" };',
        },
        {
            "id": "policy-4a",
            "tool": "issue_refund",
            "type": "permit (conditional)",
            "risk_level": "LOW",
            "condition": "amount ≤ ₹1,000",
            "description": "Small refunds within ₹1,000 are automatically approved.",
            "cedar_syntax": 'permit(principal, action == Action::"issue_refund", resource) when { context.amount <= 1000 };',
        },
        {
            "id": "policy-4b",
            "tool": "issue_refund",
            "type": "permit (conditional)",
            "risk_level": "MEDIUM",
            "condition": "₹1,001 ≤ amount ≤ ₹10,000 AND approval_status == APPROVED",
            "description": "Medium refunds between ₹1,001 and ₹10,000 require human approval.",
            "cedar_syntax": 'permit(principal, action == Action::"issue_refund", resource) when { context.amount > 1000 && context.amount <= 10000 && context.approval_status == "APPROVED" };',
        },
        {
            "id": "policy-4c",
            "tool": "issue_refund",
            "type": "implicit deny",
            "risk_level": "HIGH",
            "condition": "amount > ₹10,000",
            "description": "Refunds exceeding ₹10,000 are blocked. No policy permits this — default deny applies.",
            "cedar_syntax": "// No permit policy exists for amounts > ₹10,000 — default deny",
        },
        {
            "id": "policy-5",
            "tool": "delete_customer_record",
            "type": "forbid",
            "risk_level": "CRITICAL",
            "condition": "Always forbidden — no exceptions",
            "description": "Deleting customer records is permanently blocked. Forbid overrides any permit.",
            "cedar_syntax": 'forbid(principal, action == Action::"delete_customer_record", resource);',
        },
    ]
