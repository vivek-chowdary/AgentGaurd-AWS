import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAuditLog } from '../api/audit';
import { getPendingApprovals } from '../api/approvals';
import AgentConsole from '../components/AgentConsole';
import LiveFeed from '../components/LiveFeed';
import ApprovalQueue from '../components/ApprovalQueue';
import AuditLog from '../components/AuditLog';
import PolicyViewer from '../components/PolicyViewer';
import { useTheme } from '../context/ThemeContext';
import { Shield, Sun, Moon, LayoutGrid, FileText } from 'lucide-react';

const TABS = [
  { id: 'dashboard', label: 'Security Console', icon: LayoutGrid },
  { id: 'policies', label: 'Cedar Policies', icon: FileText },
];

export default function Dashboard() {
  const { theme, toggleTheme } = useTheme();
  const [activeMainTab, setActiveMainTab] = useState('dashboard');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Stats queries
  const { data: auditEntries = [] } = useQuery({
    queryKey: ['audit-stats'],
    queryFn: () => getAuditLog({ limit: 200 }),
    refetchInterval: 4000,
  });

  const { data: pendingApprovals = [] } = useQuery({
    queryKey: ['approvals-stats'],
    queryFn: getPendingApprovals,
    refetchInterval: 3000,
  });

  const stats = {
    allowed: auditEntries.filter(
      (e) => e.final_status === 'ALLOWED' || e.final_status === 'APPROVED' || e.final_status === 'EXECUTED'
    ).length,
    pending: pendingApprovals.length,
    blocked: auditEntries.filter(
      (e) => e.final_status === 'BLOCKED' || e.final_status === 'DENIED'
    ).length,
  };

  const handleHeaderFilterClick = (status) => {
    setStatusFilter((prev) => (prev === status ? 'ALL' : status));
  };

  return (
    <div className="min-h-screen flex flex-col bg-[var(--bg-body)] text-[var(--text-main)] transition-colors">
      {/* ═══════ HEADER ═══════ */}
      <header className="sticky top-0 z-30 border-b border-[var(--border-panel)] bg-[var(--bg-panel)] shadow-sm backdrop-blur-md transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            {/* Logo */}
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl nm-card flex items-center justify-center text-mono-900 dark:text-mono-100 border border-[var(--border-panel)]">
                <Shield className="w-4 h-4 stroke-[2.2]" />
              </div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-mono font-bold tracking-wider text-mono-950 dark:text-mono-50">
                  AGENTGUARD
                </h1>
                <span className="text-[0.62rem] font-mono font-bold px-1.5 py-0.2 rounded nm-inset text-mono-500">
                  AWS
                </span>
              </div>
            </div>

            {/* Navigation Tabs */}
            <div className="hidden md:flex items-center gap-1.5 nm-inset p-1 rounded-xl">
              {TABS.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeMainTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveMainTab(tab.id)}
                    className={`flex items-center gap-2 px-3 py-1 text-xs font-mono font-semibold rounded-lg transition-all ${
                      isActive
                        ? 'nm-btn-primary'
                        : 'text-mono-600 dark:text-mono-400 hover:text-mono-950 dark:hover:text-mono-50'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* Stats & Controls */}
            <div className="flex items-center gap-3">
              {/* Telemetry Counter Chips - Simply click to filter the ledger */}
              <div className="flex items-center gap-1 nm-inset p-1 rounded-xl text-xs font-mono font-semibold border border-[var(--border-inset)]">
                <button
                  onClick={() => handleHeaderFilterClick('ALLOWED')}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded-lg transition-all ${
                    statusFilter === 'ALLOWED'
                      ? 'nm-btn-primary font-bold shadow-sm'
                      : 'hover:bg-black/[0.05] dark:hover:bg-white/[0.05]'
                  }`}
                  title="Click to filter by ALLOWED"
                >
                  <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-sm" />
                  <span className="text-mono-950 dark:text-mono-50 font-bold">{stats.allowed}</span>
                  <span className="text-[0.65rem] text-mono-500">ALLOWED</span>
                </button>
                <span className="text-mono-300 dark:text-mono-700">│</span>
                <button
                  onClick={() => handleHeaderFilterClick('PENDING')}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded-lg transition-all ${
                    statusFilter === 'PENDING'
                      ? 'nm-btn-primary font-bold shadow-sm'
                      : 'hover:bg-black/[0.05] dark:hover:bg-white/[0.05]'
                  }`}
                  title="Click to filter by PENDING"
                >
                  <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse shadow-sm" />
                  <span className="text-mono-950 dark:text-mono-50 font-bold">{stats.pending}</span>
                  <span className="text-[0.65rem] text-mono-500">PENDING</span>
                </button>
                <span className="text-mono-300 dark:text-mono-700">│</span>
                <button
                  onClick={() => handleHeaderFilterClick('BLOCKED')}
                  className={`flex items-center gap-1.5 px-2 py-1 rounded-lg transition-all ${
                    statusFilter === 'BLOCKED'
                      ? 'nm-btn-primary font-bold shadow-sm'
                      : 'hover:bg-black/[0.05] dark:hover:bg-white/[0.05]'
                  }`}
                  title="Click to filter by BLOCKED"
                >
                  <span className="w-2 h-2 rounded-full bg-rose-500 shadow-sm" />
                  <span className="text-mono-950 dark:text-mono-50 font-bold">{stats.blocked}</span>
                  <span className="text-[0.65rem] text-mono-500">BLOCKED</span>
                </button>
              </div>

              {/* Theme Switcher */}
              <button
                onClick={toggleTheme}
                aria-label="Toggle theme"
                className="nm-btn w-8 h-8 rounded-lg flex items-center justify-center text-mono-900 dark:text-mono-100 transition-all"
                title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
              >
                {theme === 'dark' ? (
                  <Sun className="w-4 h-4 stroke-[2]" />
                ) : (
                  <Moon className="w-4 h-4 stroke-[2]" />
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ═══════ MAIN CONTENT WORKSPACE ═══════ */}
      <main className="flex-1 p-4 sm:p-5">
        <div className="max-w-7xl mx-auto space-y-6">
          {activeMainTab === 'dashboard' ? (
            <>
              {/* TOP TIER: Side-by-side Console and Approval Queue */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Left: Agent Console (Comfortable height) */}
                <div className="nm-panel rounded-2xl overflow-hidden flex flex-col">
                  <AgentConsole />
                </div>

                {/* Right: Authorization Queue */}
                <div className="nm-panel rounded-2xl overflow-hidden flex flex-col">
                  <ApprovalQueue />
                </div>
              </div>

              {/* BOTTOM TIER: Completed Actions / Live Stream & Audit Ledger */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                {/* Left: Live Action Stream */}
                <div className="nm-panel rounded-2xl overflow-hidden flex flex-col">
                  <LiveFeed />
                </div>

                {/* Right: Audit Ledger */}
                <div className="nm-panel rounded-2xl overflow-hidden flex flex-col">
                  <AuditLog statusFilter={statusFilter} onStatusChange={setStatusFilter} />
                </div>
              </div>
            </>
          ) : (
            /* Cedar Policies View */
            <div className="nm-panel rounded-2xl overflow-hidden p-6">
              <PolicyViewer />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
