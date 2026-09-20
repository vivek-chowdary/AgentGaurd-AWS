import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAuditLog } from '../api/audit';
import ActionCard from './ActionCard';
import { Radio, Loader2, Activity } from 'lucide-react';

export default function LiveFeed({ onSelectAction }) {
  const { data: entries = [], isLoading } = useQuery({
    queryKey: ['audit-live'],
    queryFn: () => getAuditLog({ limit: 25 }),
    refetchInterval: 2500,
  });

  return (
    <div className="flex flex-col h-full bg-inherit">
      {/* Header with clear boundary */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border-panel)] bg-black/[0.015] dark:bg-white/[0.015]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl nm-card flex items-center justify-center text-mono-950 dark:text-mono-50 border border-[var(--border-panel)]">
            <Radio className="w-4 h-4 stroke-[2.2]" />
          </div>
          <div>
            <h2 className="text-xs font-mono font-bold tracking-wider uppercase text-mono-950 dark:text-mono-50">
              Live Action Stream
            </h2>
            <p className="text-[0.68rem] text-mono-500 font-mono">
              Intercepted telemetry stream
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[0.65rem] font-mono font-bold px-2 py-0.5 rounded-md nm-inset text-mono-700 dark:text-mono-300 border border-[var(--border-panel)]">
            POLLING_ACTIVE
          </span>
        </div>
      </div>

      {/* Feed list */}
      <div className="flex-1 p-5 space-y-3 overflow-y-auto min-h-[300px]">
        {isLoading && entries.length === 0 && (
          <div className="h-full min-h-[200px] flex items-center justify-center text-xs text-mono-400 font-mono gap-2.5">
            <Loader2 className="w-4 h-4 animate-spin text-mono-800 dark:text-mono-200" />
            <span>Streaming actions...</span>
          </div>
        )}

        {entries.length === 0 && !isLoading && (
          <div className="h-full min-h-[200px] flex flex-col items-center justify-center text-center p-6 space-y-2 text-mono-400 font-mono">
            <Activity className="w-6 h-6 stroke-[1.5]" />
            <p className="text-xs font-bold text-mono-600 dark:text-mono-400">No actions intercepted yet</p>
            <p className="text-[0.7rem] text-mono-500">Run a command in the console to observe telemetry</p>
          </div>
        )}

        {entries.map((entry) => (
          <ActionCard
            key={entry.action_id}
            action={entry}
            compact
            onClick={() => onSelectAction && onSelectAction(entry)}
          />
        ))}
      </div>
    </div>
  );
}
