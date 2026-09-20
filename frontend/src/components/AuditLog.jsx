import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAuditLog } from '../api/audit';
import StatusBadge from './StatusBadge';
import { formatDistanceToNow } from 'date-fns';
import { ScrollText, ChevronDown, ChevronRight, Loader2, Search } from 'lucide-react';

export default function AuditLog({ statusFilter = 'ALL', onStatusChange }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedRow, setExpandedRow] = useState(null);

  const selectedStatus = statusFilter;

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ['audit-log', selectedStatus],
    queryFn: () => getAuditLog({
      limit: 100,
      status: selectedStatus === 'ALL' ? undefined : selectedStatus,
    }),
    refetchInterval: 4000,
  });

  const filteredEntries = entries.filter((entry) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      entry.action_id?.toLowerCase().includes(q) ||
      entry.tool_name?.toLowerCase().includes(q) ||
      entry.cedar_reason?.toLowerCase().includes(q) ||
      JSON.stringify(entry.tool_parameters || {}).toLowerCase().includes(q)
    );
  });

  const toggleRow = (id) => {
    setExpandedRow((prev) => (prev === id ? null : id));
  };

  return (
    <div className="flex flex-col h-full bg-inherit">
      {/* Clean Header: Simple, no redundant filter clutter */}
      <div className="flex items-center justify-between gap-3 px-5 py-3 border-b border-[var(--border-panel)] bg-black/[0.015] dark:bg-white/[0.015]">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg nm-card flex items-center justify-center text-mono-950 dark:text-mono-50 border border-[var(--border-panel)]">
            <ScrollText className="w-3.5 h-3.5 stroke-[2]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-mono font-bold tracking-wider uppercase text-mono-950 dark:text-mono-50">
                Audit Ledger
              </h2>
              {selectedStatus !== 'ALL' && (
                <span className="text-[0.6rem] font-mono font-bold px-2 py-0.5 rounded nm-btn-primary">
                  {selectedStatus}
                </span>
              )}
            </div>
            <p className="text-[0.65rem] text-mono-500 font-mono">
              DynamoDB compliance log
            </p>
          </div>
        </div>

        {/* Search Bar only */}
        <div className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search records..."
            className="nm-inset rounded-lg px-3 py-1 text-xs font-mono text-mono-950 dark:text-mono-50 placeholder-mono-400 focus:outline-none w-40 sm:w-48 border border-[var(--border-inset)] font-medium"
          />
        </div>
      </div>

      {/* Table list */}
      <div className="flex-1 overflow-y-auto max-h-[380px]">
        {isLoading && filteredEntries.length === 0 && (
          <div className="h-40 flex items-center justify-center text-xs text-mono-400 font-mono gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Loading ledger records...</span>
          </div>
        )}

        {filteredEntries.length === 0 && !isLoading && (
          <div className="h-40 flex flex-col items-center justify-center text-center p-6 space-y-1.5 text-mono-400 font-mono">
            <p className="text-xs font-bold text-mono-600 dark:text-mono-400">
              No records match {selectedStatus !== 'ALL' ? `"${selectedStatus}"` : 'search'}
            </p>
          </div>
        )}

        <div className="divide-y divide-[var(--border-panel)]">
          {filteredEntries.map((entry) => {
            const isExpanded = expandedRow === entry.action_id;
            let timeAgo = '';
            try {
              if (entry.timestamp) {
                timeAgo = formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true });
              }
            } catch {}

            return (
              <div
                key={entry.action_id}
                className="transition-colors hover:bg-black/[0.02] dark:hover:bg-white/[0.02]"
              >
                <div
                  onClick={() => toggleRow(entry.action_id)}
                  className="px-5 py-2.5 flex items-center justify-between gap-3 cursor-pointer text-xs font-mono"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="text-mono-400">
                      {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                    </span>
                    <span className="font-bold text-mono-950 dark:text-mono-50 truncate">
                      {entry.tool_name}
                    </span>
                    <span className="text-[0.68rem] text-mono-500 hidden sm:inline truncate">
                      {entry.action_id?.slice(0, 16)}...
                    </span>
                  </div>

                  <div className="flex items-center gap-3 flex-shrink-0">
                    <span className="text-[0.68rem] text-mono-500 hidden md:inline">
                      {timeAgo}
                    </span>
                    <StatusBadge status={entry.final_status || entry.cedar_decision} size="sm" />
                  </div>
                </div>

                {isExpanded && (
                  <div className="px-5 pb-4 pt-1 animate-fade-in">
                    <div className="nm-inset rounded-xl p-3.5 space-y-2.5 text-xs font-mono border border-[var(--border-inset)]">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[0.7rem]">
                        <div>
                          <span className="text-mono-500 font-bold">ACTION_ID:</span>{' '}
                          <span className="text-mono-950 dark:text-mono-50 font-bold">{entry.action_id}</span>
                        </div>
                        <div>
                          <span className="text-mono-500 font-bold">TIMESTAMP:</span>{' '}
                          <span className="text-mono-950 dark:text-mono-50">{entry.timestamp}</span>
                        </div>
                        <div>
                          <span className="text-mono-500 font-bold">CEDAR_DECISION:</span>{' '}
                          <span className="font-bold text-mono-950 dark:text-mono-50">{entry.cedar_decision}</span>
                        </div>
                        <div>
                          <span className="text-mono-500 font-bold">RISK_LEVEL:</span>{' '}
                          <span className="font-bold">{entry.risk_level || 'LOW'}</span>
                        </div>
                      </div>

                      {entry.cedar_reason && (
                        <div className="pt-2 border-t border-[var(--border-panel)]">
                          <span className="text-mono-500 text-[0.65rem] uppercase font-bold block mb-0.5">
                            Policy Evaluator Rationale:
                          </span>
                          <p className="text-mono-800 dark:text-mono-200 font-sans text-[0.78rem] leading-relaxed">
                            {entry.cedar_reason}
                          </p>
                        </div>
                      )}

                      <div className="pt-2 border-t border-[var(--border-panel)]">
                        <span className="text-mono-500 text-[0.65rem] uppercase font-bold block mb-1">
                          Parameters Payload:
                        </span>
                        <pre className="text-[0.7rem] overflow-x-auto text-mono-900 dark:text-mono-100 leading-relaxed bg-black/[0.03] dark:bg-white/[0.03] p-2 rounded-lg border border-[var(--border-panel)]">
                          {JSON.stringify(entry.tool_parameters || {}, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
