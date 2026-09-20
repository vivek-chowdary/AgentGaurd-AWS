import React from 'react';

const STATUS_CONFIG = {
  ALLOWED: {
    label: 'ALLOWED',
    dot: 'bg-emerald-500 shadow-sm',
  },
  PENDING: {
    label: 'PENDING',
    dot: 'bg-amber-500 animate-pulse shadow-sm',
  },
  BLOCKED: {
    label: 'BLOCKED',
    dot: 'bg-rose-500 shadow-sm',
  },
  DENIED: {
    label: 'DENIED',
    dot: 'bg-zinc-500 shadow-sm',
  },
  APPROVED: {
    label: 'APPROVED',
    dot: 'bg-emerald-500 shadow-sm',
  },
  EXECUTED: {
    label: 'EXECUTED',
    dot: 'bg-emerald-600 shadow-sm',
  },
  EXPIRED: {
    label: 'EXPIRED',
    dot: 'bg-zinc-400 shadow-sm',
  },
  REQUIRE_APPROVAL: {
    label: 'APPROVAL REQ',
    dot: 'bg-amber-500 animate-pulse shadow-sm',
  },
  ALLOW: {
    label: 'ALLOWED',
    dot: 'bg-emerald-500 shadow-sm',
  },
  DENY: {
    label: 'DENIED',
    dot: 'bg-rose-500 shadow-sm',
  },
};

export default function StatusBadge({ status, size = 'sm', showDot = true }) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.DENIED;
  const isSm = size === 'sm';

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 font-mono font-bold tracking-wider uppercase
        rounded-lg nm-inset text-mono-950 dark:text-mono-50
        border border-[var(--border-inset)]
        ${isSm ? 'text-[0.65rem] px-2.5 py-0.5' : 'text-xs px-3 py-1'}
      `}
    >
      {showDot && (
        <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      )}
      {config.label}
    </span>
  );
}
