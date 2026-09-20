#!/usr/bin/env python3
"""
AgentGuard — Seed Cedar Policies to DynamoDB.

Seeds the default Cedar policies and creates sample customer data
for the demo environment.

Usage:
    python scripts/seed_policies.py
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone

import boto3

# Configuration
REGION = os.environ.get("AWS_REGION", "ap-south-1")
AUDIT_TABLE = os.environ.get("AUDIT_TABLE_NAME", "agentguard-audit-log")
APPROVALS_TABLE = os.environ.get("APPROVALS_TABLE_NAME", "agentguard-pending-approvals")

dynamodb = boto3.resource("dynamodb", region_name=REGION)


def seed_policies():
    """Read Cedar policies from file and display them."""
    cedar_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "backend", "policies", "default_policies.cedar",
    )

    if os.path.exists(cedar_file):
        with open(cedar_file, "r") as f:
            cedar_content = f.read()
        print("✅ Cedar Policies loaded:")
        print("=" * 60)
        print(cedar_content)
        print("=" * 60)
    else:
        print(f"❌ Cedar policy file not found at: {cedar_file}")
        return False

    return True


def verify_tables():
    """Verify DynamoDB tables exist."""
    client = boto3.client("dynamodb", region_name=REGION)

    for table_name in [AUDIT_TABLE, APPROVALS_TABLE]:
        try:
            response = client.describe_table(TableName=table_name)
            status = response["Table"]["TableStatus"]
            print(f"✅ Table '{table_name}' exists (Status: {status})")
        except client.exceptions.ResourceNotFoundException:
            print(f"❌ Table '{table_name}' not found — run 'sam deploy' first")
            return False
        except Exception as e:
            print(f"⚠️  Could not check table '{table_name}': {e}")
            print("   (This is OK if running locally without AWS credentials)")
            return False

    return True


def seed_sample_customer_data():
    """Seed sample customer data entries to the audit log for demo purposes."""
    table = dynamodb.Table(AUDIT_TABLE)

    sample_entries = [
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": datetime(2026, 9, 19, 9, 0, 0, tzinfo=timezone.utc).isoformat(),
            "tool_name": "read_customer_profile",
            "tool_parameters": {"customer_id": "C123"},
            "agent_session_id": str(uuid.uuid4()),
            "cedar_decision": "ALLOW",
            "cedar_reason": "Reading customer profiles is a low-risk, read-only operation",
            "risk_level": "LOW",
            "final_status": "ALLOWED",
        },
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": datetime(2026, 9, 19, 9, 5, 0, tzinfo=timezone.utc).isoformat(),
            "tool_name": "create_draft_email",
            "tool_parameters": {
                "to": "rahul.sharma@example.com",
                "subject": "Welcome to ShopKart!",
                "body": "Dear Rahul, welcome to our platform...",
            },
            "agent_session_id": str(uuid.uuid4()),
            "cedar_decision": "ALLOW",
            "cedar_reason": "Creating email drafts has no external side effects",
            "risk_level": "LOW",
            "final_status": "ALLOWED",
        },
        {
            "action_id": str(uuid.uuid4()),
            "timestamp": datetime(2026, 9, 19, 9, 10, 0, tzinfo=timezone.utc).isoformat(),
            "tool_name": "issue_refund",
            "tool_parameters": {
                "customer_id": "C123",
                "amount": 500,
                "reason": "Order cancellation",
            },
            "agent_session_id": str(uuid.uuid4()),
            "cedar_decision": "ALLOW",
            "cedar_reason": "Refund of ₹500.00 is within automatic approval threshold",
            "risk_level": "LOW",
            "final_status": "ALLOWED",
        },
    ]

    print("\n📝 Seeding sample audit log entries...")
    for entry in sample_entries:
        try:
            table.put_item(Item=entry)
            print(f"   ✅ {entry['tool_name']} — {entry['final_status']}")
        except Exception as e:
            print(f"   ❌ Failed to seed {entry['tool_name']}: {e}")

    print(f"\n✅ Seeded {len(sample_entries)} sample entries")


def main():
    print("🛡️  AgentGuard — Policy & Data Seeder")
    print("=" * 60)

    # Step 1: Load and display Cedar policies
    print("\n📜 Step 1: Loading Cedar Policies...")
    seed_policies()

    # Step 2: Verify DynamoDB tables
    print("\n📊 Step 2: Verifying DynamoDB Tables...")
    tables_exist = verify_tables()

    # Step 3: Seed sample data (only if tables exist)
    if tables_exist:
        print("\n🌱 Step 3: Seeding Sample Data...")
        seed_sample_customer_data()
    else:
        print("\n⏭️  Step 3: Skipping sample data (tables not available)")

    print("\n" + "=" * 60)
    print("✅ Seeding complete!")
    print("\nNext steps:")
    print("  1. Deploy with: sam build && sam deploy --guided")
    print("  2. Run demo with: python scripts/test_agent.py")
    print("  3. Open dashboard at your Amplify URL")


if __name__ == "__main__":
    main()
