"""
AgentGuard Audit Lambda Handler — Returns audit log to the dashboard.

Routes:
- GET /audit              → Get audit log (supports ?limit=50&tool=&status=)
- GET /audit/{action_id}  → Get a single audit record with full detail
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.shared.constants import CORS_HEADERS
from backend.shared.dynamodb import get_dynamodb_client

logger = logging.getLogger("agentguard.audit")
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route audit log requests."""
    try:
        http_method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        path_params = event.get("pathParameters") or {}
        query_params = event.get("queryStringParameters") or {}

        logger.info(json.dumps({
            "level": "INFO",
            "service": "audit",
            "operation": "request",
            "method": http_method,
            "path": path,
        }))

        # Handle OPTIONS (CORS preflight)
        if http_method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": "",
            }

        # GET /audit/{action_id}
        action_id = path_params.get("action_id", "")
        if action_id:
            return _handle_get_single(action_id)

        # GET /audit
        if http_method == "GET":
            return _handle_get_list(query_params)

        return {
            "statusCode": 404,
            "headers": CORS_HEADERS,
            "body": json.dumps({"success": False, "error": "Route not found"}),
        }

    except Exception as e:
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "audit",
            "operation": "internal_error",
            "error": str(e),
        }))
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "success": False,
                "error": f"Internal error: {str(e)}",
            }),
        }


def _handle_get_list(query_params: dict[str, str]) -> dict[str, Any]:
    """Get audit log entries with optional filters."""
    db = get_dynamodb_client()

    limit = int(query_params.get("limit", "50"))
    tool_filter = query_params.get("tool")
    status_filter = query_params.get("status")

    # Clamp limit to reasonable range
    limit = max(1, min(limit, 200))

    entries = db.get_audit_logs(
        limit=limit,
        tool_filter=tool_filter,
        status_filter=status_filter,
    )

    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({
            "success": True,
            "data": entries,
            "count": len(entries),
            "filters": {
                "limit": limit,
                "tool": tool_filter,
                "status": status_filter,
            },
        }),
    }


def _handle_get_single(action_id: str) -> dict[str, Any]:
    """Get a single audit log entry with full detail."""
    db = get_dynamodb_client()

    entry = db.get_audit_log(action_id)
    if not entry:
        return {
            "statusCode": 404,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "success": False,
                "error": f"Audit entry {action_id} not found",
            }),
        }

    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({
            "success": True,
            "data": entry,
        }),
    }
