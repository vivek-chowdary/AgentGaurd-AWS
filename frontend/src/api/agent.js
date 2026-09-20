/**
 * AgentGuard API — Agent endpoint calls with intelligent offline simulation.
 */

import { localAuditEntries, localPendingApprovals } from './mockData';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function runAgent(userMessage, sessionId) {
  try {
    const response = await fetch(`${API_BASE}/agent/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_message: userMessage,
        session_id: sessionId,
      }),
      signal: AbortSignal.timeout(2500),
    });

    if (response.ok) {
      return response.json();
    }
  } catch (err) {
    // Fallback to local agent simulation
  }

  // Simulate thinking delay
  await new Promise((r) => setTimeout(r, 600));

  const lower = userMessage.toLowerCase();
  const actionId = `act-sim-${Math.random().toString(36).substring(2, 9)}`;

  // 1. Delete customer record -> DENIED / BLOCKED
  if (lower.includes('delete')) {
    const entry = {
      action_id: actionId,
      timestamp: new Date().toISOString(),
      tool_name: 'delete_customer_record',
      tool_parameters: { customer_id: 'C789', reason: 'User prompt request' },
      cedar_decision: 'DENY',
      cedar_reason: 'Cedar Policy 006: Deleting customer records is permanently forbidden for agents.',
      risk_level: 'CRITICAL',
      final_status: 'BLOCKED',
    };
    localAuditEntries.unshift(entry);
    return {
      response: 'AgentGuard Security Alert: Tool execution BLOCKED by Cedar policy. Customer record deletion is strictly forbidden.',
      actions: [
        {
          tool: 'delete_customer_record',
          decision: 'DENY',
          reason: 'Cedar Policy 006: Permanent prohibition on customer deletion',
        },
      ],
    };
  }

  // 2. Large Refund (> 50,000) -> BLOCKED
  if (lower.includes('75,000') || lower.includes('75000') || (lower.includes('refund') && lower.includes('large'))) {
    const entry = {
      action_id: actionId,
      timestamp: new Date().toISOString(),
      tool_name: 'issue_refund',
      tool_parameters: { customer_id: 'C999', amount: 75000, reason: 'High-value customer claim' },
      cedar_decision: 'DENY',
      cedar_reason: 'Cedar Policy 005: Refund of ₹75,000 exceeds maximum permitted limit of ₹50,000.',
      risk_level: 'CRITICAL',
      final_status: 'BLOCKED',
    };
    localAuditEntries.unshift(entry);
    return {
      response: 'AgentGuard Security Interceptor: Refund request ₹75,000 was BLOCKED. The maximum permissible transaction limit is ₹50,000.',
      actions: [
        {
          tool: 'issue_refund',
          decision: 'DENY',
          reason: 'Exceeds maximum authorization cap of ₹50,000',
        },
      ],
    };
  }

  // 3. Send email -> REQUIRE APPROVAL
  if (lower.includes('send') && lower.includes('email')) {
    const pendingItem = {
      action_id: actionId,
      tool_name: 'send_email',
      tool_parameters: {
        recipient: 'customer.c456@example.com',
        subject: 'Welcome to AgentGuard Secured Services',
        body: 'Welcome! Your account is now provisioned under continuous Cedar authorization guardrails.',
      },
      cedar_reason: 'Cedar Policy 003: External customer email requires human approval.',
      requested_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
      risk_level: 'MEDIUM',
      status: 'PENDING',
    };
    localPendingApprovals.unshift(pendingItem);
    localAuditEntries.unshift({
      action_id: actionId,
      timestamp: new Date().toISOString(),
      tool_name: 'send_email',
      tool_parameters: pendingItem.tool_parameters,
      cedar_decision: 'REQUIRE_APPROVAL',
      cedar_reason: 'External email transmission paused. Awaiting operator confirmation in Approval Queue.',
      risk_level: 'MEDIUM',
      final_status: 'PENDING',
    });
    return {
      response: 'Action paused by AgentGuard: Outbound email requires human approval. The request has been dispatched to the Authorization Queue.',
      actions: [
        {
          tool: 'send_email',
          decision: 'REQUIRE_APPROVAL',
          reason: 'Cedar Policy 003: Human supervisor verification required before outbound dispatch',
        },
      ],
    };
  }

  // 4. Draft email -> ALLOWED
  if (lower.includes('draft')) {
    localAuditEntries.unshift({
      action_id: actionId,
      timestamp: new Date().toISOString(),
      tool_name: 'create_draft_email',
      tool_parameters: { recipient: 'john@example.com', subject: 'Order Update #5821' },
      cedar_decision: 'ALLOW',
      cedar_reason: 'Cedar Policy 002: Drafting emails is low-risk internal staging — permitted.',
      risk_level: 'LOW',
      final_status: 'ALLOWED',
    });
    return {
      response: 'Email draft created successfully in staging. Ready for review.',
      actions: [
        {
          tool: 'create_draft_email',
          decision: 'ALLOW',
          reason: 'Internal staging action permitted',
        },
      ],
    };
  }

  // 5. Small Refund (e.g. ₹500) -> ALLOWED
  if (lower.includes('refund') || lower.includes('500')) {
    localAuditEntries.unshift({
      action_id: actionId,
      timestamp: new Date().toISOString(),
      tool_name: 'issue_refund',
      tool_parameters: { customer_id: 'C123', amount: 500, reason: 'Customer satisfaction refund' },
      cedar_decision: 'ALLOW',
      cedar_reason: 'Cedar Policy 004: Refund ₹500 is within automated threshold (<= ₹2,000).',
      risk_level: 'LOW',
      final_status: 'ALLOWED',
    });
    return {
      response: 'Refund of ₹500 has been authorized and dispatched to processing.',
      actions: [
        {
          tool: 'issue_refund',
          decision: 'ALLOW',
          reason: 'Within autonomous refund limit (<= ₹2,000)',
        },
      ],
    };
  }

  // Default: Read profile or general query -> ALLOWED
  localAuditEntries.unshift({
    action_id: actionId,
    timestamp: new Date().toISOString(),
    tool_name: 'read_customer_profile',
    tool_parameters: { customer_id: 'C123' },
    cedar_decision: 'ALLOW',
    cedar_reason: 'Cedar Policy 001: Read-only profile inspection permitted.',
    risk_level: 'LOW',
    final_status: 'ALLOWED',
  });
  return {
    response: 'Customer C123 profile retrieved: John Doe (Enterprise Tier, Active since 2024).',
    actions: [
      {
        tool: 'read_customer_profile',
        decision: 'ALLOW',
        reason: 'Read-only queries permitted',
      },
    ],
  };
}
