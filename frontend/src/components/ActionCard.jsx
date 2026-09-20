import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import StatusBadge from './StatusBadge';
import { Shield, Mail, UserX, CreditCard, FileText, User } from 'lucide-react';

const TOOL_ICONS = {
  read_customer_profile: User,
  create_draft_email: FileText,
  send_email: Mail,
  issue_refund: CreditCard,
  delete_customer_record: UserX,
};

function formatParamSummary(tool, params) {
  if (!params) return '';
  switch (tool) {
    case 'read_customer_profile':
      return `customer_id: ${params.customer_id || 'N/A'}`;
    case 'create_draft_email':
      return `to: ${params.recipient || 'N/A'}`;
    case 'send_email':
      return `to: ${params.recipient || 'N/A'}`;
    case 'issue_refund':
      return `₹${params.amount?.toLocaleString() || '0'} → ${params.customer_id || 'N/A'}`;
    case 'delete_customer_record':
      return `customer_id: ${params.customer_id || 'N/A'}`;
    default:
      return JSON.stringify(params).slice(0, 40);
  }
}

export default function ActionCard({ action, compact = false, onClick }) {
  const Icon = TOOL_ICONS[action.tool_name] || Shield;
  const paramSummary = formatParamSummary(action.tool_name, action.tool_parameters);

  let timeAgo = '';
  try {
    if (action.timestamp) {
      timeAgo = formatDistanceToNow(new Date(action.timestamp), { addSuffix: true });
    }
  } catch {
    timeAgo = '';
  }

  if (compact) {
    return (
      <div
        onClick={onClick}
        className="flex items-center gap-3.5 px-4 py-3 rounded-2xl nm-card nm-card-interactive cursor-pointer border border-[var(--border-card)] transition-all group"
      >
        <div className="w-9 h-9 rounded-xl nm-inset flex items-center justify-center flex-shrink-0 text-mono-900 dark:text-mono-100 border border-[var(--border-inset)]">
          <Icon className="w-4 h-4 stroke-[2]" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-mono font-bold text-mono-950 dark:text-mono-50 truncate">
              {action.tool_name}
            </span>
            <StatusBadge status={action.final_status || action.cedar_decision} size="sm" />
          </div>
          <div className="flex items-center justify-between text-[0.72rem] text-mono-600 dark:text-mono-400 mt-0.5">
            <span className="truncate font-mono font-medium">{paramSummary}</span>
            <span className="flex-shrink-0 ml-2 font-mono text-[0.68rem] text-mono-400">{timeAgo}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={onClick}
      className="p-5 rounded-2xl nm-card nm-card-interactive cursor-pointer space-y-3.5 border border-[var(--border-card)]"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl nm-inset flex items-center justify-center text-mono-900 dark:text-mono-100 border border-[var(--border-inset)]">
            <Icon className="w-5 h-5 stroke-[2]" />
          </div>
          <div>
            <h4 className="text-xs font-mono font-bold text-mono-950 dark:text-mono-50">
              {action.tool_name}
            </h4>
            <span className="text-[0.7rem] text-mono-500 font-mono">
              {action.action_id?.slice(0, 18)}...
            </span>
          </div>
        </div>
        <StatusBadge status={action.final_status || action.cedar_decision} />
      </div>

      <div className="nm-inset rounded-xl p-3 text-xs font-mono text-mono-800 dark:text-mono-200 space-y-1 border border-[var(--border-inset)]">
        <div className="text-[0.65rem] uppercase tracking-wider text-mono-500 font-bold">
          PAYLOAD PARAMETERS
        </div>
        <p className="truncate font-mono">{paramSummary}</p>
      </div>

      {action.cedar_reason && (
        <p className="text-xs text-mono-700 dark:text-mono-300 leading-relaxed italic border-l-2 border-mono-400 dark:border-mono-600 pl-3">
          "{action.cedar_reason}"
        </p>
      )}

      <div className="flex items-center justify-between text-[0.7rem] text-mono-500 pt-1 font-mono">
        <span className="font-bold">RISK: {action.risk_level || 'LOW'}</span>
        <span>{timeAgo}</span>
      </div>
    </div>
  );
}
