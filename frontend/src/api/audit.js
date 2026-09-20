/**
 * AgentGuard API — Audit log & policies endpoint calls with offline fallback.
 */

import { localAuditEntries, MOCK_POLICIES, RAW_CEDAR_POLICIES } from './mockData';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function getAuditLog({ limit = 50, tool, status } = {}) {
  try {
    const params = new URLSearchParams();
    if (limit) params.set('limit', limit);
    if (tool) params.set('tool', tool);
    if (status) params.set('status', status);

    const res = await fetch(`${API_BASE}/audit?${params.toString()}`, {
      signal: AbortSignal.timeout(2000),
    });
    if (res.ok) {
      const json = await res.json();
      return json.data || [];
    }
  } catch (err) {
    // Fall back to mock data
  }

  let filtered = [...localAuditEntries];
  if (tool) filtered = filtered.filter((e) => e.tool_name === tool);
  if (status) filtered = filtered.filter((e) => e.final_status === status);
  return filtered.slice(0, limit);
}

export async function getAuditEntry(actionId) {
  try {
    const res = await fetch(`${API_BASE}/audit/${actionId}`, {
      signal: AbortSignal.timeout(2000),
    });
    if (res.ok) {
      const json = await res.json();
      return json.data || null;
    }
  } catch (err) {
    // Fallback
  }
  return localAuditEntries.find((e) => e.action_id === actionId) || null;
}

export async function getPolicies() {
  try {
    const res = await fetch(`${API_BASE}/policies`, {
      signal: AbortSignal.timeout(2000),
    });
    if (res.ok) {
      const json = await res.json();
      return json.data || { policies: [], raw_cedar: '' };
    }
  } catch (err) {
    // Fallback
  }
  return { policies: MOCK_POLICIES, raw_cedar: RAW_CEDAR_POLICIES };
}
