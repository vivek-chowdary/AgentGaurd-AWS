import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getPendingApprovals, approveAction, denyAction } from '../api/approvals';
import StatusBadge from './StatusBadge';
import { formatDistanceToNow } from 'date-fns';
import {
  Clock, Check, X, Loader2,
  Mail, CreditCard, ShieldAlert
} from 'lucide-react';

const TOOL_ICONS = {
  send_email: Mail,
  issue_refund: CreditCard,
};

export default function ApprovalQueue() {
  const queryClient = useQueryClient();
  const [actionInProgress, setActionInProgress] = useState(null);

  const { data: pending = [], isLoading } = useQuery({
    queryKey: ['approvals-pending'],
    queryFn: getPendingApprovals,
    refetchInterval: 3000,
  });

  const approveMutation = useMutation({
    mutationFn: (id) => approveAction(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals-pending'] });
      queryClient.invalidateQueries({ queryKey: ['approvals-stats'] });
      queryClient.invalidateQueries({ queryKey: ['audit-stats'] });
      queryClient.invalidateQueries({ queryKey: ['audit-live'] });
      queryClient.invalidateQueries({ queryKey: ['audit-log'] });
      setActionInProgress(null);
    },
    onError: () => setActionInProgress(null),
  });

  const denyMutation = useMutation({
    mutationFn: (id) => denyAction(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals-pending'] });
      queryClient.invalidateQueries({ queryKey: ['approvals-stats'] });
      queryClient.invalidateQueries({ queryKey: ['audit-stats'] });
      queryClient.invalidateQueries({ queryKey: ['audit-live'] });
      queryClient.invalidateQueries({ queryKey: ['audit-log'] });
      setActionInProgress(null);
    },
    onError: () => setActionInProgress(null),
  });

  const handleApprove = (id) => {
    setActionInProgress(id);
    approveMutation.mutate(id);
  };

  const handleDeny = (id) => {
    setActionInProgress(id);
    denyMutation.mutate(id);
  };

  return (
    <div className="flex flex-col h-full bg-inherit">
      {/* Slim Header with clear boundary */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--border-panel)] bg-black/[0.015] dark:bg-white/[0.015]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md nm-card flex items-center justify-center text-mono-950 dark:text-mono-50 border border-[var(--border-panel)]">
            <Clock className="w-3 h-3 stroke-[2.2]" />
          </div>
          <h2 className="text-xs font-mono font-bold tracking-wider uppercase text-mono-950 dark:text-mono-50">
            Authorization Queue
          </h2>
        </div>
        <div>
          {pending.length > 0 ? (
            <span className="text-[0.62rem] font-mono font-bold px-2 py-0.5 rounded nm-inset text-amber-600 dark:text-amber-400 border border-[var(--border-panel)]">
              {pending.length} PENDING
            </span>
          ) : (
            <span className="text-[0.62rem] font-mono font-bold px-2 py-0.5 rounded nm-inset text-mono-500 border border-[var(--border-panel)]">
              CLEAR
            </span>
          )}
        </div>
      </div>

      {/* Queue items list — Comfortable height */}
      <div className="flex-1 p-3.5 space-y-3 overflow-y-auto max-h-[300px]">
        {isLoading && pending.length === 0 && (
          <div className="h-28 flex items-center justify-center text-xs text-mono-400 font-mono gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Checking authorizations...</span>
          </div>
        )}

        {pending.length === 0 && !isLoading && (
          <div className="h-28 flex flex-col items-center justify-center text-center p-4 space-y-1.5 text-mono-400 font-mono">
            <div className="w-8 h-8 rounded-xl nm-inset flex items-center justify-center border border-[var(--border-inset)]">
              <Check className="w-4 h-4 stroke-[2]" />
            </div>
            <p className="text-xs font-bold text-mono-600 dark:text-mono-400">Queue is clear</p>
            <p className="text-[0.68rem] text-mono-500">Actions requiring human approval will pause here</p>
          </div>
        )}

        {pending.map((item) => {
          const Icon = TOOL_ICONS[item.tool_name] || ShieldAlert;
          const isBusy = actionInProgress === item.action_id;

          let timeRequested = 'just now';
          try {
            if (item.requested_at) {
              timeRequested = formatDistanceToNow(new Date(item.requested_at), { addSuffix: true });
            }
          } catch {}

          return (
            <div
              key={item.action_id}
              className="p-3.5 rounded-2xl nm-card space-y-2.5 border border-[var(--border-card)] shadow-sm"
            >
              {/* Header row */}
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg nm-inset flex items-center justify-center text-mono-900 dark:text-mono-100 border border-[var(--border-inset)]">
                    <Icon className="w-3.5 h-3.5 stroke-[2]" />
                  </div>
                  <div>
                    <h3 className="text-xs font-mono font-bold text-mono-950 dark:text-mono-50">
                      {item.tool_name}
                    </h3>
                    <span className="text-[0.62rem] text-mono-500 font-mono">
                      {timeRequested}
                    </span>
                  </div>
                </div>
                <StatusBadge status="REQUIRE_APPROVAL" size="sm" />
              </div>

              {/* Cedar rationale */}
              {item.cedar_reason && (
                <div className="text-[0.72rem] text-mono-800 dark:text-mono-200 font-sans nm-inset p-2 rounded-lg border border-[var(--border-inset)] leading-snug">
                  {item.cedar_reason}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-0.5">
                <button
                  onClick={() => handleApprove(item.action_id)}
                  disabled={isBusy}
                  className="flex-1 nm-btn nm-btn-primary py-2 px-3 rounded-xl text-xs font-mono font-bold flex items-center justify-center gap-1.5 disabled:opacity-40"
                >
                  {isBusy && approveMutation.isPending ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <>
                      <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                      <span>AUTHORIZE</span>
                    </>
                  )}
                </button>

                <button
                  onClick={() => handleDeny(item.action_id)}
                  disabled={isBusy}
                  className="flex-1 nm-btn py-2 px-3 rounded-xl text-xs font-mono font-bold text-mono-700 dark:text-mono-300 hover:text-rose-600 dark:hover:text-rose-400 flex items-center justify-center gap-1.5 border border-[var(--border-card)] disabled:opacity-40"
                >
                  {isBusy && denyMutation.isPending ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <>
                      <X className="w-3.5 h-3.5 stroke-[2.2]" />
                      <span>REJECT</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
