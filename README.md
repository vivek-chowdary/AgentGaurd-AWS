# 🛡️ AgentGuard

**The Enterprise Authorization & Security Firewall for AI Agents**
*Built on AWS Bedrock (Amazon Nova) + Cedar Policy Engine + AWS Step Functions*

[![AWS](https://img.shields.io/badge/Deployed%20on-AWS%20Cloud-FF9900?style=flat&logo=amazonaws)](https://aws.amazon.com)
[![Bedrock](https://img.shields.io/badge/Bedrock-Amazon%20Nova-232F3E?style=flat)](https://aws.amazon.com/bedrock)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python)](https://python.org)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react)](https://react.dev)
[![Cedar](https://img.shields.io/badge/Authorization-Cedar%20Policies-8B5CF6?style=flat)](https://www.cedarpolicy.com)

---

## 🎯 The Core Problem

Autonomous AI agents powered by LLMs now interact with mission-critical systems: issuing customer refunds, sending outbound emails, updating databases, and executing third-party APIs. However, **prompting guardrails alone are probabilistic, non-deterministic, and prone to hallucination or jailbreaks**. 

A customer support bot can accidentally issue a ₹75,000 refund instead of ₹500, or a maintenance agent could execute destructive database commands without authorization.

**AgentGuard solves this.** It functions as an inline, deterministic authorization firewall between the AI agent and any tool it can call. Every tool call is intercepted **before** execution, evaluated in real time against mathematical **Cedar policies**, and routed:
* 🟢 **ALLOW** — Executed immediately if compliant with low-risk policies.
* 🟡 **REQUIRE APPROVAL** — Paused in AWS Step Functions using task tokens until an authorized human signs off.
* 🔴 **DENY / BLOCK** — Blocked immediately, logging the violation to an immutable audit trail.

> **The Analogy:** Web application firewalls (WAF) protect applications from external malicious traffic. **AgentGuard protects your business from your own AI agents' mistakes.**

---

## 🏗️ Production Architecture

```
[User / Client Interaction]
           │
           ▼
[AI Agent Runtime — Amazon Bedrock (Nova 2 Lite)]
           │
           ▼ (Interception Layer: Evaluates BEFORE Execution)
[AgentGuard Interceptor — AWS Lambda]
           │
           ▼
[Cedar Policy Engine — Principal / Action / Resource / Context]
           │
 ┌─────────┴───────────────────────┬──────────────────────────┐
 │                                 │                          │
 ▼ (ALLOW)                         ▼ (REQUIRE APPROVAL)       ▼ (DENY)
[Execute Tool Lambda]    [AWS Step Functions Workflow]    [Block & Raise Alert]
 │                                 │                          │
 │                       (waitForTaskToken Callback)          │
 │                                 │                          │
 │                       [EventBridge + SNS Alert]            │
 │                                 │                          │
 │                       [SecOps Dashboard (React)]           │
 │                                 │                          │
 │                       [Human Decision: Approve/Deny]       │
 │                                 │                          │
 └─────────────────┬───────────────┴──────────────────────────┘
                   │
                   ▼
[Amazon DynamoDB — Immutable Audit Log & Pending Approvals]
                   │
                   ▼
[Amazon CloudWatch — Structured JSON Telemetry & Alarms]
```

---

## 🔧 Technologies Used & Why

| Service / Tool | Purpose in AgentGuard |
|---|---|
| **Amazon Bedrock (Amazon Nova 2 Lite)** | Powers the AI agent with real-time tool-calling via Bedrock Converse API (`us.amazon.nova-2-lite-v1:0`). |
| **Cedar Policy Engine** | Open-source AWS authorization language. Implements deterministic `permit` and `forbid` rules where `forbid` strictly overrides any `permit`. |
| **AWS Step Functions** | Coordinates asynchronous human approvals using `.waitForTaskToken` callback semantics. |
| **AWS Lambda (Python 3.12)** | 7 decoupled microservices: Agent Runner, Interceptor, Approvals API, Audit API, Policy API, Tool Executor, and Event Logger. |
| **Amazon DynamoDB** | Fast NoSQL audit ledger (`agentguard-audit-log`) and approval store (`agentguard-pending-approvals`) with Global Secondary Indexes (`status-index`). |
| **Amazon API Gateway** | Fully managed REST API with CORS headers and proxy integration for the front-end dashboard. |
| **Amazon EventBridge + SNS** | Custom event bus (`agentguard-events`) routing approval notifications to administrator email. |
| **Amazon Cognito** | Enterprise User Pool and Client for dashboard authentication. |
| **React 18 + Vite + Tailwind CSS** | Real-time Security Operations Center (SOC) dashboard with live polling, approval queue, and telemetry stream. |

---

## 🚀 Live AWS Deployment & Infrastructure

The entire platform (Frontend + Backend) is 100% hosted and running on **AWS** (`us-east-1`):

* 🖥️ **Live Web Dashboard (AWS S3)**: **[http://agentguard-artifacts-360908957446-us-east-1.s3-website-us-east-1.amazonaws.com](http://agentguard-artifacts-360908957446-us-east-1.s3-website-us-east-1.amazonaws.com)**
* 🌐 **API Gateway Base URL**: `https://o8boudk53e.execute-api.us-east-1.amazonaws.com/prod`
* 💾 **DynamoDB Audit Ledger**: `agentguard-audit-log`
* ⏳ **DynamoDB Approval Store**: `agentguard-pending-approvals`
* 🔄 **Step Functions State Machine**: `arn:aws:states:us-east-1:360908957446:stateMachine:agentguard-approval-workflow`
* 📬 **SNS Notifications Topic**: `arn:aws:sns:us-east-1:360908957446:agentguard-approval-notifications`
* 👤 **Cognito User Pool ID**: `us-east-1_mnuq0qSBy`
* 🪣 **S3 Website & Artifacts Bucket**: `agentguard-artifacts-360908957446-us-east-1`

---

## 🏆 What We Achieved

1. **Zero Un-Intercepted Tool Calls**: Created a decorator and proxy architecture ensuring no LLM execution reaches the real system without prior Cedar evaluation.
2. **Deterministic Security Rules**: Replaced unreliable prompt instructions with mathematical Cedar logic:
   * Read operations (`read_customer_profile`) ➔ Always **PERMIT**.
   * Draft creations (`create_draft_email`) ➔ Always **PERMIT**.
   * Outbound communications (`send_email`) ➔ **REQUIRE APPROVAL** (human sign-off required).
   * Micro-refunds (≤ ₹1,000) ➔ Auto-approved **PERMIT**.
   * Moderate refunds (₹1,001 - ₹10,000) ➔ **REQUIRE APPROVAL**.
   * Excessive refunds (> ₹10,000) ➔ Implicit **DENY** (default deny).
   * Database deletions (`delete_customer_record`) ➔ Permanent **FORBID** (cannot be overridden).
3. **True Asynchronous Human-in-the-Loop**: Integrated Step Functions task tokens (`$$.Task.Token`). When human approval is triggered, the execution pauses safely in the cloud and resumes only when authorized from the dashboard or SNS link.
4. **Resilient Dual-Mode Operation**: The SecOps frontend connects to the live AWS API Gateway with intelligent offline simulation fallback, ensuring zero presentation downtime during intermittent network or account quotas.

---

## 🎬 5 Core Test Scenarios

| # | Action / Prompt | Tool | Policy Decision | Result |
|---|---|---|---|---|
| 1 | `"Read profile for customer C123"` | `read_customer_profile` | ✅ **PERMIT** | Instant execution (Green) |
| 2 | `"Create a draft email to john@example.com"` | `create_draft_email` | ✅ **PERMIT** | Instant execution (Green) |
| 3 | `"Send a welcome email to john@example.com"` | `send_email` | ⏳ **REQUIRE APPROVAL** | Pauses workflow, appears in approval queue |
| 4a | `"Issue a ₹500 refund to C123"` | `issue_refund` (₹500) | ✅ **PERMIT** | Instant execution (within threshold) |
| 4b | `"Issue a ₹75,000 refund to C999"` | `issue_refund` (₹75,000) | 🚫 **DENY** | Blocked (Exceeds maximum limit) |
| 5 | `"Delete customer record C789"` | `delete_customer_record` | 🚫 **FORBID** | Permanently blocked by Cedar policy |

---

## 📦 "Build-it" vs "Ship-it" — What Model is AgentGuard?

**AgentGuard is a "Ship-it" Ready Enterprise Authorization Middleware.**

It is not merely a toy prompt wrapper or build-time library; it is a **fully deployed, cloud-native security sidecar/proxy**.
* **Deploy Once, Protect Everywhere**: The infrastructure runs autonomously in your AWS account (API Gateway, Step Functions, DynamoDB, Lambdas).
* **Decoupled Security**: Your data science or engineering teams can freely iterate on prompts, models, and agents (Bedrock, LangChain, CrewAI, AutoGen) while your SecOps/compliance teams manage Cedar authorization policies independently.
* **Non-Invasive Architecture**: You don't rewrite your tools. AgentGuard sits in front of existing tool APIs like an API firewall.

---

## 🔌 How External Developers Connect Any AI Agent

If you already have an AI agent running on **LangChain, CrewAI, AutoGen, or Amazon Bedrock**, you integrate AgentGuard in 3 simple steps:

```python
import requests

AGENTGUARD_API = "https://o8boudk53e.execute-api.us-east-1.amazonaws.com/prod"

def guard_tool(tool_name: str, params: dict, agent_id: str = "customer-support-agent"):
    """
    Wrap ANY agent tool with AgentGuard prior to execution.
    """
    # 1. Intercept BEFORE calling the real tool
    response = requests.post(f"{AGENTGUARD_API}/interceptor", json={
        "tool_name": tool_name,
        "tool_parameters": params,
        "agent_id": agent_id
    })
    verdict = response.json() # ALLOW, REQUIRE_APPROVAL, or DENY

    # 2. Act based on Cedar evaluation
    if verdict.get("decision") == "ALLOW":
        return execute_real_tool(tool_name, params)
    
    elif verdict.get("decision") == "REQUIRE_APPROVAL":
        return f"⏳ Action paused: Requires human approval. Tracking ID: {verdict.get('approval_id')}"
    
    else: # DENY
        return f"🚫 Security Alert: Action BLOCKED by Cedar policy: {verdict.get('reason')}"
```

---

## ✍️ How to Author & Push Custom Cedar Policies

**Cedar is completely dynamic — you can write rules for any tool, attribute, or context.**

### 1. Anatomy of a Cedar Policy
* **`principal`**: Who is acting (e.g., `Agent::"BillingBot"` or user role).
* **`action`**: Which tool is being triggered (e.g., `Action::"issue_refund"`, `Action::"restart_ec2"`).
* **`resource`**: The target entity (e.g., `Customer::"C123"`, `Server::"prod-db"`).
* **`context`**: Dynamic parameters passed during invocation (`amount`, `customer_tier`, `time`, `department`).

### 2. Examples of Custom Policies
```cedar
// Example A: Higher limits for VIP customers
permit(
  principal,
  action == Action::"issue_refund",
  resource
) when {
  context.customer_tier == "VIP" &&
  context.amount <= 25000
};

// Example B: Restrict external communications to business hours (9 AM - 6 PM)
permit(
  principal,
  action == Action::"send_email",
  resource
) when {
  context.current_hour >= 9 &&
  context.current_hour <= 18 &&
  context.approval_status == "APPROVED"
};

// Example C: Explicit forbid (Forbid strictly overrides any permit)
forbid(
  principal,
  action == Action::"drop_database",
  resource
);
```

### 3. How to Push New Policies
* **Method 1 (GitOps / File)**: Add your policy to `backend/policies/default_policies.cedar` and run:
  ```bash
  AWS_REGION=us-east-1 python3 scripts/seed_policies.py
  ```
* **Method 2 (Dynamic REST API)**: Post new policies programmatically to the live API:
  `POST https://o8boudk53e.execute-api.us-east-1.amazonaws.com/prod/policies`
* **Method 3 (SecOps Dashboard)**: Inspect active policies in real time from the Cedar Policies tab on the dashboard.

---

## 🔮 Roadmap & Next Improvements

1. **Multi-Agent Fleet Governance**: Register and manage dozens of AI agents across departments (HR, Finance, Support) with isolated, per-agent Cedar policy stores.
2. **Slack & Microsoft Teams Interactive Approvals**: Deliver interactive action cards with 1-click Approve/Deny buttons directly to team channels via EventBridge webhooks.
3. **Visual Cedar Policy Designer**: A no-code visual builder within the dashboard that lets compliance teams create, simulate, and test new authorization rules without writing raw Cedar syntax.
4. **OpenTelemetry & Distributed Tracing**: Export trace telemetry across the Bedrock runtime, Lambda interceptors, and DynamoDB storage for full SOC compliance auditing.
5. **Automated Canary Policy Deployment**: Safely roll out policy updates using shadow-evaluation mode, comparing agent decisions against historical traces before enforcing new rules.

---

## 🛠️ Quick Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/vivek-chowdary/AgentGaurd-AWS.git
cd AgentGaurd-AWS

# 2. Run the frontend dashboard
cd frontend
npm install
npm run dev

# 3. Access Dashboard
# Open http://localhost:5173 in your browser
```

---

## 📄 License
MIT License. Built for enterprise AI agent safety and compliance.
