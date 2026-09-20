"""
AgentGuard DynamoDB Helpers — All database interactions go through this module.
Provides typed methods for audit log and pending approvals tables.
Uses structured JSON logging for every operation.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from backend.shared.constants import (
    APPROVALS_STATUS_INDEX,
    APPROVALS_TABLE_NAME,
    AUDIT_STATUS_INDEX,
    AUDIT_TABLE_NAME,
    AWS_REGION,
    ApprovalStatus,
)
from backend.shared.models import AuditLogEntry, PendingApproval

logger = logging.getLogger("agentguard.dynamodb")
logger.setLevel(logging.INFO)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types from DynamoDB."""
    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            if o % 1 == 0:
                return int(o)
            return float(o)
        return super().default(o)


def _convert_floats_to_decimal(obj: Any) -> Any:
    """Recursively convert float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: _convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_floats_to_decimal(item) for item in obj]
    return obj


def _convert_decimals(obj: Any) -> Any:
    """Recursively convert Decimal values to int/float for JSON serialization."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    elif isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals(item) for item in obj]
    return obj


class DynamoDBClient:
    """Centralized DynamoDB client for all AgentGuard tables."""

    def __init__(self, region: str = AWS_REGION):
        self._dynamodb = boto3.resource("dynamodb", region_name=region)
        self._audit_table = self._dynamodb.Table(AUDIT_TABLE_NAME)
        self._approvals_table = self._dynamodb.Table(APPROVALS_TABLE_NAME)

    # ============================================================
    # AUDIT LOG OPERATIONS
    # ============================================================

    def put_audit_log(self, entry: AuditLogEntry) -> dict[str, Any]:
        """Write an audit log entry. Audit records are immutable once written."""
        try:
            item = _convert_floats_to_decimal(entry.to_dynamo_item())
            self._audit_table.put_item(Item=item)
            logger.info(json.dumps({
                "level": "INFO",
                "service": "dynamodb",
                "operation": "put_audit_log",
                "action_id": entry.action_id,
                "tool": entry.tool_name,
                "status": entry.final_status,
            }))
            return _convert_decimals(item)
        except ClientError as e:
            logger.error(json.dumps({
                "level": "ERROR",
                "service": "dynamodb",
                "operation": "put_audit_log",
                "action_id": entry.action_id,
                "error": str(e),
            }))
            raise

    def get_audit_logs(
        self,
        limit: int = 50,
        tool_filter: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Query audit log entries with optional filters. Returns newest first."""
        try:
            if status_filter:
                # Use the GSI to query by status
                kwargs: dict[str, Any] = {
                    "IndexName": AUDIT_STATUS_INDEX,
                    "KeyConditionExpression": Key("final_status").eq(status_filter),
                    "ScanIndexForward": False,
                    "Limit": limit,
                }
                if tool_filter:
                    kwargs["FilterExpression"] = Attr("tool_name").eq(tool_filter)
                response = self._audit_table.query(**kwargs)
            else:
                # Scan (for demo purposes — in production, use proper indexes)
                kwargs = {"Limit": limit}
                filter_expressions = []
                if tool_filter:
                    filter_expressions.append(Attr("tool_name").eq(tool_filter))
                if filter_expressions:
                    combined = filter_expressions[0]
                    for expr in filter_expressions[1:]:
                        combined = combined & expr
                    kwargs["FilterExpression"] = combined
                response = self._audit_table.scan(**kwargs)

            items = response.get("Items", [])
            # Sort by timestamp descending
            items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return [_convert_decimals(item) for item in items[:limit]]
        except ClientError as e:
            logger.error(json.dumps({
                "level": "ERROR",
                "service": "dynamodb",
                "operation": "get_audit_logs",
                "error": str(e),
            }))
            raise

    def get_audit_log(self, action_id: str) -> Optional[dict[str, Any]]:
        """Get a single audit log entry by action_id. Returns the latest record."""
        try:
            response = self._audit_table.query(
                KeyConditionExpression=Key("action_id").eq(action_id),
                ScanIndexForward=False,
                Limit=1,
            )
            items = response.get("Items", [])
            if items:
                return _convert_decimals(items[0])
            return None
        except ClientError as e:
            logger.error(json.dumps({
                "level": "ERROR",
                "service": "dynamodb",
                "operation": "get_audit_log",
                "action_id": action_id,
                "error": str(e),
            }))
            raise

    # ============================================================
    # PENDING APPROVALS OPERATIONS
    # ============================================================

    def put_pending_approval(self, approval: PendingApproval) -> dict[str, Any]:
        """Create a new pending approval record."""
        try:
            item = _convert_floats_to_decimal(approval.to_dynamo_item())
            self._approvals_table.put_item(Item=item)
            logger.info(json.dumps({
                "level": "INFO",
                "service": "dynamodb",
                "operation": "put_pending_approval",
                "approval_id": approval.approval_id,
                "tool": approval.tool_name,
                "status": approval.status,
            }))
            return _convert_decimals(item)
        except ClientError as e:
            logger.error(json.dumps({
                "level": "ERROR",
                "service": "dynamodb",
                "operation": "put_pending_approval",
                "approval_id": approval.approval_id,
                "error": str(e),
            }))
            raise

    def get_pending_approvals(self) -> list[dict[str, Any]]:
        """Query all PENDING approvals using the GSI."""
        try:
            response = self._approvals_table.query(
                IndexName=APPROVALS_STATUS_INDEX,
                KeyConditionExpression=Key("status").eq(ApprovalStatus.PENDING.value),
                ScanIndexForward=False,
            )
            items = response.get("Items", [])
            # Filter out expired approvals
            now = datetime.now(timezone.utc).isoformat()
            active = []
            for item in items:
                expires_at = item.get("expires_at", "")
                if expires_at and expires_at < now:
                    # Mark as expired
                    self.update_approval_status(
                        item["approval_id"],
                        ApprovalStatus.EXPIRED.value,
                        approved_by=None,
                    )
                else:
                    active.append(_convert_decimals(item))
            return active
        except ClientError as e:
            logger.error(json.dumps({
                "level": "ERROR",
                "service": "dynamodb",
                "operation": "get_pending_approvals",
                "error": str(e),
            }))
            raise

    def get_pending_approval(self, approval_id: str) -> Optional[dict[str, Any]]:
        """Get a single pending approval by ID."""
        try:
            response = self._approvals_table.get_item(
                Key={"approval_id": approval_id}
            )
            item = response.get("Item")
            if item:
                return _convert_decimals(item)
            return None
        except ClientError as e:
            logger.error(json.dumps({
                "level": "ERROR",
                "service": "dynamodb",
                "operation": "get_pending_approval",
                "approval_id": approval_id,
                "error": str(e),
            }))
            raise

    def update_approval_status(
        self,
        approval_id: str,
        status: str,
        approved_by: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Update approval status. Idempotent — if already in the target status,
        returns the existing record without error.
        """
        try:
            # First, check current status for idempotency
            current = self.get_pending_approval(approval_id)
            if current and current.get("status") == status:
                logger.info(json.dumps({
                    "level": "INFO",
                    "service": "dynamodb",
                    "operation": "update_approval_status",
                    "approval_id": approval_id,
                    "message": f"Already in status {status}, idempotent return",
                }))
                return current

            update_expr = "SET #s = :status, updated_at = :updated_at"
            expr_values: dict[str, Any] = {
                ":status": status,
                ":updated_at": datetime.now(timezone.utc).isoformat(),
            }
            expr_names = {"#s": "status"}

            if approved_by:
                update_expr += ", approved_by = :approved_by, approval_timestamp = :approval_ts"
                expr_values[":approved_by"] = approved_by
                expr_values[":approval_ts"] = datetime.now(timezone.utc).isoformat()

            response = self._approvals_table.update_item(
                Key={"approval_id": approval_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
                ReturnValues="ALL_NEW",
            )
            updated = response.get("Attributes", {})
            logger.info(json.dumps({
                "level": "INFO",
                "service": "dynamodb",
                "operation": "update_approval_status",
                "approval_id": approval_id,
                "new_status": status,
                "approved_by": approved_by or "N/A",
            }))
            return _convert_decimals(updated)
        except ClientError as e:
            logger.error(json.dumps({
                "level": "ERROR",
                "service": "dynamodb",
                "operation": "update_approval_status",
                "approval_id": approval_id,
                "error": str(e),
            }))
            raise


# Singleton instance for Lambda reuse across warm invocations
_client: Optional[DynamoDBClient] = None


def get_dynamodb_client() -> DynamoDBClient:
    """Get or create the singleton DynamoDB client."""
    global _client
    if _client is None:
        _client = DynamoDBClient()
    return _client
