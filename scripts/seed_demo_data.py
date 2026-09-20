#!/usr/bin/env python3
"""
AgentGuard — Seed Demo Data.

Creates a realistic set of audit log entries showing all 5 tool types
with varied statuses, timestamps, and parameters. Perfect for demo
screenshots and dashboard testing.

Usage:
    python scripts/seed_demo_data.py
"""

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import boto3

# Configuration
REGION = os.environ.get("AWS_REGION", "ap-south-1")
AUDIT_TABLE = os.environ.get("AUDIT_TABLE_NAME", "agentguard-audit-log")
APPROVALS_TABLE = os.environ.get("APPROVALS_TABLE_NAME", "agentguard-pending-approvals")

dynamodb = boto3.resource("dynamodb", region_name=REGION)


def convert_floats(obj):
    """Convert float values to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats(item) for item in obj]
    return obj


def generate_demo_entries():
    """Generate a realistic set of audit log entries for demo purposes."""
    base_time = datetime.now(timezone.utc) - timedelta(hours=2)
    session_id = str(uuid.uuid4())

    entries = [
        # Action 1: Read customer profile — ALLOWED
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": (base_time + timedelta(minutes=0)).isoformat(),
            "tool_name": "read_customer_profile",
            "tool_parameters": {"customer_id": "C123"},
            "agent_session_id": session_id,
            "cedar_decision": "ALLOW",
            "cedar_reason": "Reading customer profiles is a low-risk, read-only operation — always permitted",
            "risk_level": "LOW",
            "final_status": "ALLOWED",
        },
        # Action 2: Create draft email — ALLOWED
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": (base_time + timedelta(minutes=2)).isoformat(),
            "tool_name": "create_draft_email",
            "tool_parameters": {
                "to": "rahul.sharma@example.com",
                "subject": "Your Order Update — ShopKart",
                "body": "Dear Rahul, your order #ORD-789 has been shipped and will arrive within 3-5 business days.",
            },
            "agent_session_id": session_id,
            "cedar_decision": "ALLOW",
            "cedar_reason": "Creating email drafts has no external side effects — always permitted",
            "risk_level": "LOW",
            "final_status": "ALLOWED",
        },
        # Action 3: Send email — PENDING (requires approval)
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": (base_time + timedelta(minutes=5)).isoformat(),
            "tool_name": "send_email",
            "tool_parameters": {
                "to": "priya.patel@example.com",
                "subject": "Welcome to ShopKart Premium!",
                "body": "Dear Priya, congratulations on achieving Platinum status! Enjoy exclusive benefits.",
            },
            "agent_session_id": session_id,
            "cedar_decision": "REQUIRE_APPROVAL",
            "cedar_reason": "Sending external emails requires human approval per company policy",
            "risk_level": "MEDIUM",
            "final_status": "PENDING",
        },
        # Action 4: Send email — APPROVED (already approved)
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": (base_time + timedelta(minutes=8)).isoformat(),
            "tool_name": "send_email",
            "tool_parameters": {
                "to": "amit.kumar@example.com",
                "subject": "Return Confirmation — Order #ORD-445",
                "body": "Dear Amit, your return has been processed. Refund will be credited within 5-7 business days.",
            },
            "agent_session_id": session_id,
            "cedar_decision": "ALLOW",
            "cedar_reason": "Approved by human reviewer",
            "risk_level": "MEDIUM",
            "final_status": "APPROVED",
            "approved_by": "admin@shopkart.com",
            "approval_timestamp": (base_time + timedelta(minutes=10)).isoformat(),
        },
        # Action 5: Small refund — ALLOWED
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": (base_time + timedelta(minutes=12)).isoformat(),
            "tool_name": "issue_refund",
            "tool_parameters": {
                "customer_id": "C123",
                "amount": 500.0,
                "reason": "Order cancellation — item out of stock",
            },
            "agent_session_id": session_id,
            "cedar_decision": "ALLOW",
            "cedar_reason": "Refund of ₹500.00 is within automatic approval threshold (≤ ₹1,000)",
            "risk_level": "LOW",
            "final_status": "ALLOWED",
        },
        # Action 6: Medium refund — PENDING
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": (base_time + timedelta(minutes=15)).isoformat(),
            "tool_name": "issue_refund",
            "tool_parameters": {
                "customer_id": "C456",
                "amount": 5000.0,
                "reason": "Defective product — laptop screen flickering",
            },
            "agent_session_id": session_id,
            "cedar_decision": "REQUIRE_APPROVAL",
            "cedar_reason": "Refund of ₹5,000.00 exceeds automatic threshold (₹1,000). Requires human approval",
            "risk_level": "MEDIUM",
            "final_status": "PENDING",
        },
        # Action 7: Large refund — BLOCKED
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": (base_time + timedelta(minutes=18)).isoformat(),
            "tool_name": "issue_refund",
            "tool_parameters": {
                "customer_id": "C999",
                "amount": 75000.0,
                "reason": "Billing error — duplicate charge",
            },
            "agent_session_id": session_id,
            "cedar_decision": "DENY",
            "cedar_reason": "Refund of ₹75,000.00 exceeds maximum allowed threshold (₹10,000). This action is blocked by policy",
            "risk_level": "HIGH",
            "final_status": "BLOCKED",
        },
        # Action 8: Delete customer record — BLOCKED
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": (base_time + timedelta(minutes=20)).isoformat(),
            "tool_name": "delete_customer_record",
            "tool_parameters": {"customer_id": "C789"},
            "agent_session_id": session_id,
            "cedar_decision": "DENY",
            "cedar_reason": "Permanently deleting customer records is forbidden by company policy. No exceptions",
            "risk_level": "CRITICAL",
            "final_status": "BLOCKED",
        },
        # Action 9: Another read — ALLOWED (shows repeated pattern)
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": (base_time + timedelta(minutes=22)).isoformat(),
            "tool_name": "read_customer_profile",
            "tool_parameters": {"customer_id": "C456"},
            "agent_session_id": session_id,
            "cedar_decision": "ALLOW",
            "cedar_reason": "Reading customer profiles is a low-risk, read-only operation — always permitted",
            "risk_level": "LOW",
            "final_status": "ALLOWED",
        },
        # Action 10: Another small refund — ALLOWED
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": (base_time + timedelta(minutes=25)).isoformat(),
            "tool_name": "issue_refund",
            "tool_parameters": {
                "customer_id": "C789",
                "amount": 899.0,
                "reason": "Return — Bluetooth speaker defective",
            },
            "agent_session_id": session_id,
            "cedar_decision": "ALLOW",
            "cedar_reason": "Refund of ₹899.00 is within automatic approval threshold (≤ ₹1,000)",
            "risk_level": "LOW",
            "final_status": "ALLOWED",
        },
        # Action 11: Delete attempt — BLOCKED
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": (base_time + timedelta(minutes=28)).isoformat(),
            "tool_name": "delete_customer_record",
            "tool_parameters": {"customer_id": "C123"},
            "agent_session_id": session_id,
            "cedar_decision": "DENY",
            "cedar_reason": "Permanently deleting customer records is forbidden by company policy. No exceptions",
            "risk_level": "CRITICAL",
            "final_status": "BLOCKED",
        },
        # Action 12: Draft email — ALLOWED
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": (base_time + timedelta(minutes=30)).isoformat(),
            "tool_name": "create_draft_email",
            "tool_parameters": {
                "to": "sneha.reddy@example.com",
                "subject": "Exclusive Diamond Member Offer",
                "body": "Dear Sneha, as our most valued Diamond member, enjoy 30% off on your next purchase!",
            },
            "agent_session_id": session_id,
            "cedar_decision": "ALLOW",
            "cedar_reason": "Creating email drafts has no external side effects — always permitted",
            "risk_level": "LOW",
            "final_status": "ALLOWED",
        },
    ]

    return entries


def generate_pending_approvals():
    """Generate pending approval entries for the dashboard demo."""
    now = datetime.now(timezone.utc)
    session_id = str(uuid.uuid4())

    approvals = [
        {
            "approval_id": str(uuid.uuid4()),
            "action_id": str(uuid.uuid4()),
            "tool_name": "send_email",
            "tool_parameters": {
                "to": "vip-customer@company.com",
                "subject": "Important Account Update",
                "body": "Dear valued customer, there has been a change to your account settings...",
            },
            "step_functions_task_token": "",
            "step_functions_execution_arn": "",
            "status": "PENDING",
            "created_at": (now - timedelta(minutes=3)).isoformat(),
            "expires_at": (now + timedelta(minutes=12)).isoformat(),
            "risk_level": "MEDIUM",
            "cedar_reason": "Sending external emails requires human approval per company policy",
            "agent_session_id": session_id,
        },
        {
            "approval_id": str(uuid.uuid4()),
            "action_id": str(uuid.uuid4()),
            "tool_name": "issue_refund",
            "tool_parameters": {
                "customer_id": "C456",
                "amount": 7500.0,
                "reason": "Warranty claim — laptop motherboard failure",
            },
            "step_functions_task_token": "",
            "step_functions_execution_arn": "",
            "status": "PENDING",
            "created_at": (now - timedelta(minutes=1)).isoformat(),
            "expires_at": (now + timedelta(minutes=14)).isoformat(),
            "risk_level": "MEDIUM",
            "cedar_reason": "Refund of ₹7,500.00 exceeds automatic threshold. Requires human approval",
            "agent_session_id": session_id,
        },
    ]

    return approvals


def main():
    print("🛡️  AgentGuard — Demo Data Seeder")
    print("=" * 60)

    # Seed audit log entries
    print("\n📝 Seeding audit log entries...")
    audit_table = dynamodb.Table(AUDIT_TABLE)
    entries = generate_demo_entries()

    for entry in entries:
        try:
            item = convert_floats(entry)
            audit_table.put_item(Item=item)
            status_emoji = {
                "ALLOWED": "✅",
                "PENDING": "⏳",
                "BLOCKED": "🚫",
                "APPROVED": "👍",
                "DENIED": "❌",
            }.get(entry["final_status"], "❓")
            print(f"   {status_emoji} {entry['tool_name']:30s} → {entry['final_status']}")
        except Exception as e:
            print(f"   ❌ Failed: {entry['tool_name']} — {e}")

    print(f"\n   Total audit entries: {len(entries)}")

    # Seed pending approvals
    print("\n⏳ Seeding pending approvals...")
    approvals_table = dynamodb.Table(APPROVALS_TABLE)
    approvals = generate_pending_approvals()

    for approval in approvals:
        try:
            item = convert_floats(approval)
            approvals_table.put_item(Item=item)
            print(f"   ⏳ {approval['tool_name']:30s} → PENDING (expires in 15 min)")
        except Exception as e:
            print(f"   ❌ Failed: {approval['tool_name']} — {e}")

    print(f"\n   Total pending approvals: {len(approvals)}")

    # Summary
    print("\n" + "=" * 60)
    status_counts = {}
    for entry in entries:
        status = entry["final_status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    print("📊 Summary:")
    for status, count in sorted(status_counts.items()):
        print(f"   {status}: {count}")
    print(f"   PENDING (approvals): {len(approvals)}")

    print("\n✅ Demo data seeded successfully!")
    print("   Open the AgentGuard dashboard to see the data.")


if __name__ == "__main__":
    main()
