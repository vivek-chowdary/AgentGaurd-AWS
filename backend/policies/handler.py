"""
AgentGuard Policies Lambda Handler — Returns Cedar policies to the dashboard.

Route:
- GET /policies → List all active Cedar policies with descriptions
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from backend.interceptor.cedar_evaluator import get_policy_descriptions
from backend.shared.constants import CORS_HEADERS

logger = logging.getLogger("agentguard.policies")
logger.setLevel(logging.INFO)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Return all Cedar policies with human-readable descriptions."""
    try:
        http_method = event.get("httpMethod", "GET")

        # Handle OPTIONS (CORS preflight)
        if http_method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": "",
            }

        if http_method != "GET":
            return {
                "statusCode": 405,
                "headers": CORS_HEADERS,
                "body": json.dumps({
                    "success": False,
                    "error": "Method not allowed",
                }),
            }

        # Get policy descriptions from the Cedar evaluator
        policies = get_policy_descriptions()

        # Also try to read the raw Cedar policy file
        cedar_raw = ""
        cedar_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "default_policies.cedar",
        )
        try:
            with open(cedar_file_path, "r") as f:
                cedar_raw = f.read()
        except FileNotFoundError:
            cedar_raw = "// Cedar policy file not found in Lambda package"

        logger.info(json.dumps({
            "level": "INFO",
            "service": "policies",
            "operation": "get_policies",
            "policy_count": len(policies),
        }))

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "success": True,
                "data": {
                    "policies": policies,
                    "raw_cedar": cedar_raw,
                    "total": len(policies),
                },
            }),
        }

    except Exception as e:
        logger.error(json.dumps({
            "level": "ERROR",
            "service": "policies",
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
