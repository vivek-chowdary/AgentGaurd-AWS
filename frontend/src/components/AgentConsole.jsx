import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { runAgent } from '../api/agent';
import { Terminal, CornerDownLeft, Loader2, ShieldCheck } from 'lucide-react';
import StatusBadge from './StatusBadge';

const EXAMPLE_PROMPTS = [
  { label: 'Read Profile', text: 'Read profile for customer C123', outcome: 'ALLOW' },
  { label: 'Draft Email', text: 'Create a draft email to john@example.com about order update', outcome: 'ALLOW' },
  { label: 'Send Email', text: 'Send a welcome email to customer C456', outcome: 'APPROVAL' },
  { label: 'Refund ₹500', text: 'Issue a ₹500 refund for customer C123 for cancellation', outcome: 'ALLOW' },
  { label: 'Refund ₹75K', text: 'Issue a ₹75,000 refund for customer C999 for billing error', outcome: 'BLOCK' },
  { label: 'Delete Record', text: 'Delete customer record C789', outcome: 'BLOCK' },
];

export default function AgentConsole() {
  const [input, setInput] = useState('');
  const [sessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState([]);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (message) => runAgent(message, sessionId),
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response || 'Action processed.',
          actions: data.actions || [],
          timestamp: new Date().toISOString(),
        },
      ]);
      queryClient.invalidateQueries({ queryKey: ['audit-stats'] });
      queryClient.invalidateQueries({ queryKey: ['audit-live'] });
      queryClient.invalidateQueries({ queryKey: ['audit-log'] });
      queryClient.invalidateQueries({ queryKey: ['approvals-stats'] });
      queryClient.invalidateQueries({ queryKey: ['approvals-pending'] });
    },
    onError: (error) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'error',
          content: `Execution error: ${error.message}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    },
  });

  const handleSubmit = (text) => {
    const message = text || input;
    if (!message.trim() || mutation.isPending) return;

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: message, timestamp: new Date().toISOString() },
    ]);
    setInput('');
    mutation.mutate(message);
  };

  return (
    <div className="flex flex-col h-full bg-inherit">
      {/* Slim Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--border-panel)] bg-black/[0.015] dark:bg-white/[0.015]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md nm-card flex items-center justify-center text-mono-950 dark:text-mono-50 border border-[var(--border-panel)]">
            <Terminal className="w-3 h-3 stroke-[2.2]" />
          </div>
          <h2 className="text-xs font-mono font-bold tracking-wider uppercase text-mono-950 dark:text-mono-50">
            Agent Console
          </h2>
        </div>
        <span className="text-[0.6rem] font-mono font-bold px-2 py-0.5 rounded nm-inset text-mono-600 dark:text-mono-400 border border-[var(--border-panel)]">
          BEDROCK_CLAUDE
        </span>
      </div>

      {/* Messages area — Compact, comfortable height */}
      <div className="flex-1 p-3.5 space-y-2.5 overflow-y-auto max-h-[180px] min-h-[140px]">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-center p-3 text-mono-500 font-mono text-[0.72rem] nm-inset rounded-xl border border-[var(--border-panel)]">
            <span>Ready. Click a scenario chip below or type an instruction.</span>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className={`text-xs animate-fade-in ${
                msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'
              }`}
            >
              <div
                className={`max-w-[90%] rounded-xl p-3 transition-all ${
                  msg.role === 'user'
                    ? 'nm-card bg-mono-950 text-mono-50 dark:bg-mono-50 dark:text-mono-950 font-sans border border-[var(--border-panel)]'
                    : msg.role === 'error'
                    ? 'nm-inset border border-rose-500/40 text-rose-600 dark:text-rose-400'
                    : 'nm-card border border-[var(--border-panel)] space-y-1.5'
                }`}
              >
                <div className="flex items-center justify-between gap-3 text-[0.62rem] font-mono opacity-70 mb-0.5">
                  <span className="font-bold">{msg.role === 'user' ? 'OPERATOR' : 'INTERCEPTOR'}</span>
                  <span>{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                </div>
                <p className="leading-relaxed font-sans text-[0.78rem] whitespace-pre-wrap">{msg.content}</p>

                {msg.actions && msg.actions.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-[var(--border-subtle)] space-y-1.5">
                    {msg.actions.map((act, idx) => (
                      <div key={idx} className="nm-inset rounded-lg p-2 flex items-center justify-between gap-2 border border-[var(--border-panel)]">
                        <div className="font-mono text-[0.7rem] truncate min-w-0">
                          <span className="font-bold text-mono-950 dark:text-mono-50">{act.tool}</span>
                          {act.reason && <p className="text-[0.65rem] text-mono-500 truncate">{act.reason}</p>}
                        </div>
                        <StatusBadge status={act.decision} size="sm" />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {mutation.isPending && (
          <div className="flex justify-start">
            <div className="nm-card rounded-xl px-3 py-1.5 flex items-center gap-2 text-xs text-mono-600 dark:text-mono-300 font-mono border border-[var(--border-panel)]">
              <Loader2 className="w-3 h-3 animate-spin text-mono-950 dark:text-mono-50" />
              <span>Evaluating Cedar policies...</span>
            </div>
          </div>
        )}
      </div>

      {/* Demo Scenario Chips — Compact & Tidy */}
      <div className="p-2.5 border-t border-[var(--border-panel)] bg-black/[0.01] dark:bg-white/[0.01]">
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5">
          {EXAMPLE_PROMPTS.map((prompt, i) => (
            <button
              key={i}
              onClick={() => handleSubmit(prompt.text)}
              disabled={mutation.isPending}
              className="nm-btn px-2 py-1.5 rounded-lg text-left font-mono transition-all border border-[var(--border-panel)] hover:border-mono-500"
            >
              <div className="text-[0.65rem] font-bold text-mono-950 dark:text-mono-50 truncate">
                {prompt.label}
              </div>
              <div className={`text-[0.58rem] font-bold ${
                prompt.outcome === 'ALLOW' ? 'text-emerald-600 dark:text-emerald-400' :
                prompt.outcome === 'BLOCK' ? 'text-rose-600 dark:text-rose-400' :
                'text-amber-600 dark:text-amber-400'
              }`}>
                [{prompt.outcome}]
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Compact Input row */}
      <div className="p-2.5 border-t border-[var(--border-panel)]">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmit();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Instruct the agent..."
            disabled={mutation.isPending}
            className="flex-1 nm-inset rounded-xl px-3 py-2 text-xs font-sans text-mono-950 dark:text-mono-50 placeholder-mono-400 focus:outline-none border border-[var(--border-inset)] font-medium"
          />
          <button
            type="submit"
            disabled={!input.trim() || mutation.isPending}
            className="nm-btn nm-btn-primary px-4 py-2 rounded-xl text-xs font-mono font-bold flex items-center gap-1.5 disabled:opacity-40"
          >
            {mutation.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <>
                <span>SEND</span>
                <CornerDownLeft className="w-3 h-3" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
