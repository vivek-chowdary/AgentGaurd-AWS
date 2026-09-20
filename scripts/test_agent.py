#!/usr/bin/env python3
"""
AgentGuard — Demo Test Script.

Runs the complete 5-action demo scenario against the deployed API,
demonstrating all three Cedar decision paths: ALLOW, REQUIRE_APPROVAL, DENY.

Usage:
    export API_BASE_URL=https://your-api-id.execute-api.ap-south-1.amazonaws.com/prod
    python scripts/test_agent.py

Or for local testing:
    export API_BASE_URL=http://127.0.0.1:3000
    python scripts/test_agent.py
"""

import json
import os
import sys
import time
import uuid

import requests

API_BASE_URL = os.environ.get(
    "API_BASE_URL",
    "http://127.0.0.1:3000",
)
SESSION_ID = str(uuid.uuid4())


def call_agent(message: str) -> dict:
    """Send a message to the agent and return the response."""
    url = f"{API_BASE_URL}/agent/run"
    payload = {
        "user_message": message,
        "session_id": SESSION_ID,
    }

    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "success": False}


def get_pending_approvals() -> list:
    """Get all pending approvals from the dashboard API."""
    url = f"{API_BASE_URL}/approvals/pending"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️  Could not fetch approvals: {e}")
        return []


def approve_action(approval_id: str) -> dict:
    """Approve a pending action."""
    url = f"{API_BASE_URL}/approvals/{approval_id}/approve"
    payload = {"approved_by": "demo_user"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "success": False}


def get_audit_log(limit: int = 20) -> list:
    """Get the audit log."""
    url = f"{API_BASE_URL}/audit?limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️  Could not fetch audit log: {e}")
        return []


def print_section(title: str):
    """Print a styled section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_result(result: dict):
    """Print an agent response nicely."""
    if result.get("success"):
        print(f"\n   📨 Agent Response:")
        response_text = result.get("response", "No response")
        for line in response_text.split("\n"):
            print(f"      {line}")

        actions = result.get("actions", [])
        if actions:
            print(f"\n   🔧 Actions taken: {len(actions)}")
            for action in actions:
                print(f"      • {action.get('tool_name', '?')}: {action.get('result_preview', '')[:80]}")
    else:
        print(f"\n   ❌ Error: {result.get('error', 'Unknown error')}")


def main():
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║        🛡️  AgentGuard — Demo Scenario Runner         ║
    ║                                                      ║
    ║  5 actions, 5 different outcomes                     ║
    ║  Demonstrating: ALLOW / REQUIRE_APPROVAL / DENY      ║
    ╚══════════════════════════════════════════════════════╝
    """)

    print(f"   API Base URL: {API_BASE_URL}")
    print(f"   Session ID:   {SESSION_ID}")

    # ──────────────────────────────────────────────────────
    # ACTION 1: Read customer profile — ALLOW
    # ──────────────────────────────────────────────────────
    print_section("Action 1: Read Customer Profile (Expected: ✅ ALLOW)")
    print("   Sending: 'Look up the profile for customer C123'")

    result = call_agent("Look up the profile for customer C123. Show me their details.")
    print_result(result)
    time.sleep(2)

    # ──────────────────────────────────────────────────────
    # ACTION 2: Create draft email — ALLOW
    # ──────────────────────────────────────────────────────
    print_section("Action 2: Create Draft Email (Expected: ✅ ALLOW)")
    print("   Sending: 'Draft an email to john@example.com'")

    result = call_agent(
        "Create a draft email to john@example.com with subject 'Order Confirmation' "
        "and body 'Dear John, your order has been confirmed and will be shipped within 2 days.'"
    )
    print_result(result)
    time.sleep(2)

    # ──────────────────────────────────────────────────────
    # ACTION 3: Send email — REQUIRE_APPROVAL
    # ──────────────────────────────────────────────────────
    print_section("Action 3: Send Email (Expected: ⏳ REQUIRE_APPROVAL)")
    print("   Sending: 'Send a welcome email to john@example.com'")

    result = call_agent(
        "Send an email to john@example.com with subject 'Welcome to ShopKart!' "
        "and body 'Dear John, welcome to ShopKart. Enjoy 10% off your first order!'"
    )
    print_result(result)

    # Check for pending approvals
    time.sleep(3)
    print("\n   🔍 Checking pending approvals...")
    pending = get_pending_approvals()
    if pending:
        print(f"   📋 Found {len(pending)} pending approval(s)")
        for p in pending:
            print(f"      • [{p.get('approval_id', '?')[:8]}...] {p.get('tool_name')} — {p.get('cedar_reason', '')[:60]}")

        # Auto-approve the first pending email
        email_pending = [p for p in pending if p.get("tool_name") == "send_email"]
        if email_pending:
            print(f"\n   👆 Auto-approving send_email action...")
            approval_result = approve_action(email_pending[0]["approval_id"])
            print(f"   Result: {approval_result.get('message', approval_result.get('error', '?'))}")
    else:
        print("   ℹ️  No pending approvals found (workflow may not be fully configured)")

    time.sleep(2)

    # ──────────────────────────────────────────────────────
    # ACTION 4a: Small refund — ALLOW
    # ──────────────────────────────────────────────────────
    print_section("Action 4a: Small Refund ₹500 (Expected: ✅ ALLOW)")
    print("   Sending: 'Issue a ₹500 refund to C123 for order cancellation'")

    result = call_agent("Issue a refund of 500 rupees to customer C123 for order cancellation.")
    print_result(result)
    time.sleep(2)

    # ──────────────────────────────────────────────────────
    # ACTION 4b: Large refund — DENY
    # ──────────────────────────────────────────────────────
    print_section("Action 4b: Large Refund ₹75,000 (Expected: 🚫 DENY)")
    print("   Sending: 'Issue a ₹75,000 refund to C999 for billing error'")

    result = call_agent("Issue a refund of 75000 rupees to customer C999 for a billing error.")
    print_result(result)
    time.sleep(2)

    # ──────────────────────────────────────────────────────
    # ACTION 5: Delete customer record — DENY
    # ──────────────────────────────────────────────────────
    print_section("Action 5: Delete Customer Record (Expected: 🚫 DENY)")
    print("   Sending: 'Delete customer record C789'")

    result = call_agent("Delete the customer record for C789.")
    print_result(result)
    time.sleep(2)

    # ──────────────────────────────────────────────────────
    # FINAL: Show audit log
    # ──────────────────────────────────────────────────────
    print_section("📊 Final Audit Log")
    audit = get_audit_log(20)
    if audit:
        print(f"\n   {'Action ID':<12} {'Tool':<28} {'Decision':<20} {'Status':<12}")
        print(f"   {'─'*12} {'─'*28} {'─'*20} {'─'*12}")
        for entry in audit:
            status_emoji = {
                "ALLOWED": "✅",
                "PENDING": "⏳",
                "BLOCKED": "🚫",
                "APPROVED": "👍",
                "DENIED": "❌",
                "EXECUTED": "✅",
            }.get(entry.get("final_status", ""), "❓")

            print(
                f"   {entry.get('action_id', '?')[:12]:<12} "
                f"{entry.get('tool_name', '?'):<28} "
                f"{entry.get('cedar_decision', '?'):<20} "
                f"{status_emoji} {entry.get('final_status', '?')}"
            )
    else:
        print("   ℹ️  No audit entries found")

    print(f"\n{'='*70}")
    print("   🎬 Demo complete! Check the AgentGuard dashboard for the full view.")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
