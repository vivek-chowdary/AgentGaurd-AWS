/**
 * AgentGuard API — Approvals endpoint calls with offline fallback.
 */

import { localPendingApprovals, localAuditEntries } from './mockData';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function getPendingApprovals() {
  try {
    const res = await fetch(`${API_BASE}/approvals/pending`, {
      signal: AbortSignal.timeout(2000),
    });
    if (res.ok) {
      const json = await res.json();
      return json.data || [];
    }
  } catch (err) {
    // Fallback
  }
  return [...localPendingApprovals];
}

export async function approveAction(actionId, approverId = 'supervisor-secops') {
  try {
    const res = await fetch(`${API_BASE}/approvals/${actionId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approver_id: approverId }),
      signal: AbortSignal.timeout(2000),
    });
    if (res.ok) {
      return res.json();
    }
  } catch (err) {
    // Fallback
  }

  // Remove from local pending
  const idx = localPendingApprovals.findIndex((a) => a.action_id === actionId);
  if (idx !== -1) {
    const approved = localPendingApprovals.splice(idx, 1)[0];
    localAuditEntries.unshift({
      action_id: approved.action_id,
      timestamp: new Date().toISOString(),
      tool_name: approved.tool_name,
      tool_parameters: approved.tool_parameters,
      cedar_decision: 'ALLOW',
      cedar_reason: `Approved by human operator (${approverId}).`,
      risk_level: approved.risk_level,
      final_status: 'APPROVED',
    });
  }
  return { success: true, action_id: actionId, status: 'APPROVED' };
}

export async function denyAction(actionId, reason = 'Operator rejected execution', approverId = 'supervisor-secops') {
  try {
    const res = await fetch(`${API_BASE}/approvals/${actionId}/deny`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approver_id: approverId, reason }),
      signal: AbortSignal.timeout(2000),
    });
    if (res.ok) {
      return res.json();
    }
  } catch (err) {
    // Fallback
  }

  // Remove from local pending
  const idx = localPendingApprovals.findIndex((a) => a.action_id === actionId);
  if (idx !== -1) {
    const denied = localPendingApprovals.splice(idx, 1)[0];
    localAuditEntries.unshift({
      action_id: denied.action_id,
      timestamp: new Date().toISOString(),
      tool_name: denied.tool_name,
      tool_parameters: denied.tool_parameters,
      cedar_decision: 'DENY',
      cedar_reason: `Denied by human operator: ${reason}.`,
      risk_level: denied.risk_level,
      final_status: 'DENIED',
    });
  }
  return { success: true, action_id: actionId, status: 'DENIED' };
}
