import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getPolicies } from '../api/audit';
import { FileCode, Loader2, ShieldCheck, ShieldAlert, Copy, Check, Sliders } from 'lucide-react';

export default function PolicyViewer() {
  const [viewMode, setViewMode] = useState('parsed'); // 'parsed' | 'raw'
  const [copied, setCopied] = useState(false);

  const { data: policiesData = { policies: [], raw_cedar: '' }, isLoading } = useQuery({
    queryKey: ['cedar-policies'],
    queryFn: getPolicies,
  });

  const { policies = [], raw_cedar = '' } = policiesData;

  const handleCopy = () => {
    navigator.clipboard.writeText(raw_cedar);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col h-full bg-inherit">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-black/[0.06] dark:border-white/[0.07]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl nm-inset flex items-center justify-center text-mono-900 dark:text-mono-100">
            <FileCode className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-mono-900 dark:text-mono-100">
              Cedar Authorization Policies
            </h2>
            <p className="text-[0.7rem] text-mono-500 font-mono">
              AWS Cedar Language • Fine-grained Access Control Model
            </p>
          </div>
        </div>

        {/* View toggle & copy */}
        <div className="flex items-center gap-2">
          <div className="nm-inset p-1 rounded-xl flex items-center gap-1">
            <button
              onClick={() => setViewMode('parsed')}
              className={`px-3 py-1 text-xs font-mono rounded-lg transition-all ${
                viewMode === 'parsed'
                  ? 'nm-btn-primary font-bold'
                  : 'text-mono-500 hover:text-mono-900 dark:hover:text-mono-100'
              }`}
            >
              Rules ({policies.length})
            </button>
            <button
              onClick={() => setViewMode('raw')}
              className={`px-3 py-1 text-xs font-mono rounded-lg transition-all ${
                viewMode === 'raw'
                  ? 'nm-btn-primary font-bold'
                  : 'text-mono-500 hover:text-mono-900 dark:hover:text-mono-100'
              }`}
            >
              Cedar Source (.cedar)
            </button>
          </div>

          {viewMode === 'raw' && (
            <button
              onClick={handleCopy}
              className="nm-btn p-2 rounded-xl text-mono-700 dark:text-mono-300 hover:text-mono-950 dark:hover:text-mono-50"
              title="Copy Cedar source"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="h-full flex items-center justify-center text-xs text-mono-400 font-mono gap-2">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Loading Cedar policy set...</span>
          </div>
        ) : viewMode === 'parsed' ? (
          <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4">
            {policies.map((policy) => {
              const isPermit = policy.effect?.toLowerCase() === 'permit';
              return (
                <div
                  key={policy.policy_id}
                  className="p-5 rounded-2xl nm-card space-y-3 border border-black/[0.04] dark:border-white/[0.05]"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-lg nm-inset flex items-center justify-center">
                        {isPermit ? (
                          <ShieldCheck className="w-4 h-4 text-mono-900 dark:text-mono-100" />
                        ) : (
                          <ShieldAlert className="w-4 h-4 text-mono-900 dark:text-mono-100" />
                        )}
                      </div>
                      <span className="text-xs font-mono font-bold text-mono-900 dark:text-mono-100 truncate">
                        {policy.policy_id}
                      </span>
                    </div>

                    <span
                      className={`text-[0.65rem] font-mono font-bold px-2 py-0.5 rounded-md nm-inset uppercase tracking-wider ${
                        isPermit ? 'text-mono-900 dark:text-mono-100' : 'text-mono-900 dark:text-mono-100 font-black'
                      }`}
                    >
                      {policy.effect}
                    </span>
                  </div>

                  <p className="text-xs font-sans text-mono-700 dark:text-mono-300 leading-relaxed">
                    {policy.description}
                  </p>

                  <div className="nm-inset rounded-xl p-3 space-y-1 text-[0.7rem] font-mono">
                    <div className="flex justify-between">
                      <span className="text-mono-400">ACTION:</span>
                      <span className="text-mono-900 dark:text-mono-100 font-semibold">{policy.action}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-mono-400">RESOURCE:</span>
                      <span className="text-mono-800 dark:text-mono-200">{policy.resource}</span>
                    </div>
                    {policy.conditions && policy.conditions !== 'none' && (
                      <div className="pt-1 mt-1 border-t border-black/[0.04] dark:border-white/[0.05] flex justify-between">
                        <span className="text-mono-400">CONDITIONS:</span>
                        <span className="text-mono-700 dark:text-mono-300 font-semibold">{policy.conditions}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="max-w-4xl mx-auto">
            <div className="nm-inset rounded-2xl p-6 font-mono text-xs overflow-x-auto text-mono-800 dark:text-mono-200 leading-relaxed">
              <pre>{raw_cedar}</pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
