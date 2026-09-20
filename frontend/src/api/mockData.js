/**
 * Realistic Mock Data & Fallback Store for AgentGuard.
 * Ensures the dashboard is immediately interactive and full of rich data
 * even when the AWS backend is not yet running locally.
 */

export const MOCK_POLICIES = [
  {
    policy_id: 'policy_001_read_profile',
    description: 'Permit agents to read customer profile data (low risk read-only)',
    effect: 'permit',
    principal: 'AgentGuard::Agent',
    action: 'AgentGuard::Action::"read_customer_profile"',
    resource: 'AgentGuard::CustomerProfile',
    conditions: 'none',
  },
  {
    policy_id: 'policy_002_draft_email',
    description: 'Permit agents to draft emails (requires no customer contact)',
    effect: 'permit',
    principal: 'AgentGuard::Agent',
    action: 'AgentGuard::Action::"create_draft_email"',
    resource: 'AgentGuard::EmailDraft',
    conditions: 'none',
  },
  {
    policy_id: 'policy_003_send_email_approval',
    description: 'Require human approval before sending any email to a customer',
    effect: 'forbid',
    principal: 'AgentGuard::Agent',
    action: 'AgentGuard::Action::"send_email"',
    resource: 'AgentGuard::Customer',
    conditions: 'unless approved by human supervisor',
  },
  {
    policy_id: 'policy_004_refund_under_threshold',
    description: 'Permit refund issuance under ₹2,000 without human intervention',
    effect: 'permit',
    principal: 'AgentGuard::Agent',
    action: 'AgentGuard::Action::"issue_refund"',
    resource: 'AgentGuard::Transaction',
    conditions: 'when { context.amount <= 2000 }',
  },
  {
    policy_id: 'policy_005_refund_exceeds_max',
    description: 'Strictly forbid refund issuance exceeding ₹50,000 (hard security limit)',
    effect: 'forbid',
    principal: 'AgentGuard::Agent',
    action: 'AgentGuard::Action::"issue_refund"',
    resource: 'AgentGuard::Transaction',
    conditions: 'when { context.amount > 50000 }',
  },
  {
    policy_id: 'policy_006_delete_permanently_forbidden',
    description: 'Permanently forbid customer record deletion by automated agents',
    effect: 'forbid',
    principal: 'AgentGuard::Agent',
    action: 'AgentGuard::Action::"delete_customer_record"',
    resource: 'AgentGuard::CustomerProfile',
    conditions: 'always',
  },
];

export const RAW_CEDAR_POLICIES = `// -------------------------------------------------------------
// AGENTGUARD CEDAR AUTHORIZATION POLICIES
// -------------------------------------------------------------

// Policy 1: Always permit reading customer profiles (read-only)
permit(
    principal == AgentGuard::Agent::"CustomerCareBot",
    action == AgentGuard::Action::"read_customer_profile",
    resource
);

// Policy 2: Always permit drafting emails
permit(
    principal == AgentGuard::Agent::"CustomerCareBot",
    action == AgentGuard::Action::"create_draft_email",
    resource
);

// Policy 3: Forbid sending email directly without human authorization
forbid(
    principal == AgentGuard::Agent::"CustomerCareBot",
    action == AgentGuard::Action::"send_email",
    resource
) unless {
    context.human_approved == true
};

// Policy 4: Permit refunds up to INR 2,000 automatically
permit(
    principal == AgentGuard::Agent::"CustomerCareBot",
    action == AgentGuard::Action::"issue_refund",
    resource
) when {
    context.amount <= 2000
};

// Policy 5: Strictly forbid refunds exceeding INR 50,000
forbid(
    principal == AgentGuard::Agent::"CustomerCareBot",
    action == AgentGuard::Action::"issue_refund",
    resource
) when {
    context.amount > 50000
};

// Policy 6: Absolutely forbid customer record deletion
forbid(
    principal,
    action == AgentGuard::Action::"delete_customer_record",
    resource
);`;

// Initial mock pending approvals
export let localPendingApprovals = [
  {
    action_id: 'act-req-901',
    tool_name: 'send_email',
    tool_parameters: {
      recipient: 'john.doe@enterprise.io',
      subject: 'Account Renewal Confirmation & Premium SLA Agreement',
      body: 'Dear John, Your annual renewal has been initiated with upgraded dedicated tier.',
    },
    cedar_reason: 'External email transmissions require human approval per Policy 003.',
    requested_at: new Date(Date.now() - 45 * 1000).toISOString(),
    expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
    risk_level: 'MEDIUM',
    status: 'PENDING',
  },
  {
    action_id: 'act-req-902',
    tool_name: 'issue_refund',
    tool_parameters: {
      customer_id: 'C-8842',
      amount: 14500,
      reason: 'Disputed double charge during annual subscription billing transition',
    },
    cedar_reason: 'Refund exceeds ₹2,000 threshold. Supervisor confirmation required.',
    requested_at: new Date(Date.now() - 140 * 1000).toISOString(),
    expires_at: new Date(Date.now() + 12 * 60 * 1000).toISOString(),
    risk_level: 'HIGH',
    status: 'PENDING',
  },
];

// Initial mock audit entries
export let localAuditEntries = [
  {
    action_id: 'act-001-rfnd',
    timestamp: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
    tool_name: 'issue_refund',
    tool_parameters: { customer_id: 'C-1092', amount: 500, reason: 'Duplicate item return' },
    cedar_decision: 'ALLOW',
    cedar_reason: 'Refund amount ₹500 is within automated threshold (<= ₹2,000).',
    risk_level: 'LOW',
    final_status: 'ALLOWED',
  },
  {
    action_id: 'act-002-del',
    timestamp: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    tool_name: 'delete_customer_record',
    tool_parameters: { customer_id: 'C-9901', reason: 'User GDPR erasure request' },
    cedar_decision: 'DENY',
    cedar_reason: 'Customer record deletion is permanently forbidden for autonomous agents.',
    risk_level: 'CRITICAL',
    final_status: 'BLOCKED',
  },
  {
    action_id: 'act-003-mail',
    timestamp: new Date(Date.now() - 9 * 60 * 1000).toISOString(),
    tool_name: 'send_email',
    tool_parameters: { recipient: 'sarah.m@apex.org', subject: 'Refund Receipt #4419' },
    cedar_decision: 'ALLOW',
    cedar_reason: 'Approved by human supervisor (id: admin-ops-01).',
    risk_level: 'MEDIUM',
    final_status: 'APPROVED',
  },
  {
    action_id: 'act-004-prof',
    timestamp: new Date(Date.now() - 14 * 60 * 1000).toISOString(),
    tool_name: 'read_customer_profile',
    tool_parameters: { customer_id: 'C-1092' },
    cedar_decision: 'ALLOW',
    cedar_reason: 'Read-only profile inspection permitted.',
    risk_level: 'LOW',
    final_status: 'ALLOWED',
  },
  {
    action_id: 'act-005-drft',
    timestamp: new Date(Date.now() - 22 * 60 * 1000).toISOString(),
    tool_name: 'create_draft_email',
    tool_parameters: { recipient: 'support@vendor.com', subject: 'Invoice Discrepancy #102' },
    cedar_decision: 'ALLOW',
    cedar_reason: 'Draft creation isolated to internal staging queue.',
    risk_level: 'LOW',
    final_status: 'ALLOWED',
  },
  {
    action_id: 'act-006-rfnd75k',
    timestamp: new Date(Date.now() - 31 * 60 * 1000).toISOString(),
    tool_name: 'issue_refund',
    tool_parameters: { customer_id: 'C-9999', amount: 75000, reason: 'Manual chargeback claim' },
    cedar_decision: 'DENY',
    cedar_reason: 'Amount ₹75,000 strictly exceeds maximum ceiling of ₹50,000.',
    risk_level: 'CRITICAL',
    final_status: 'BLOCKED',
  },
];
