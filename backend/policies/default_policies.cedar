// ============================================================
// AgentGuard Cedar Policies — Source of Truth
// ============================================================
// These policies define the authorization rules for every tool
// the AI agent can call. Cedar evaluates these deterministically
// to produce ALLOW, REQUIRE_APPROVAL, or DENY decisions.
// ============================================================

// Policy 1: Read operations are always permitted
// Risk: LOW — reading customer data has no side effects
permit(
  principal,
  action == Action::"read_customer_profile",
  resource
);

// Policy 2: Draft creation is always permitted
// Risk: LOW — creating a draft doesn't send anything
permit(
  principal,
  action == Action::"create_draft_email",
  resource
);

// Policy 3: Sending emails requires human approval
// Risk: MEDIUM — external communication must be reviewed
permit(
  principal,
  action == Action::"send_email",
  resource
) when {
  context.approval_status == "APPROVED"
};

// Policy 4a: Small refunds (≤ ₹1,000) are auto-approved
// Risk: LOW — within automatic threshold
permit(
  principal,
  action == Action::"issue_refund",
  resource
) when {
  context.amount <= 1000
};

// Policy 4b: Medium refunds (₹1,001 – ₹10,000) need approval
// Risk: MEDIUM — significant amount requires human sign-off
permit(
  principal,
  action == Action::"issue_refund",
  resource
) when {
  context.amount > 1000 &&
  context.amount <= 10000 &&
  context.approval_status == "APPROVED"
};

// Policy 5: Deleting customer records is ALWAYS forbidden
// Risk: CRITICAL — no exceptions, no overrides, permanent block
forbid(
  principal,
  action == Action::"delete_customer_record",
  resource
);
