import React, { useState } from 'react';
import { Shield, ArrowRight, Loader2 } from 'lucide-react';

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('demo@agentguard.dev');
  const [password, setPassword] = useState('••••••••••••');
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      onLogin({ email, role: 'admin' });
      setLoading(false);
    }, 400);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[var(--bg-body)] text-[var(--text-main)]">
      <div className="w-full max-w-md nm-panel rounded-3xl p-8 space-y-6 border border-black/[0.06] dark:border-white/[0.08]">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl nm-card mx-auto flex items-center justify-center text-mono-900 dark:text-mono-100">
            <Shield className="w-6 h-6 stroke-[2]" />
          </div>
          <h1 className="text-lg font-mono font-bold tracking-tight text-mono-900 dark:text-mono-100">
            AGENTGUARD
          </h1>
          <p className="text-xs text-mono-500 font-mono">
            AWS Cognito Protected Security Console
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[0.7rem] font-mono uppercase tracking-wider text-mono-400">
              Operator Identifier
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full nm-inset rounded-xl px-4 py-2.5 text-xs font-mono text-mono-900 dark:text-mono-100 focus:outline-none"
              required
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[0.7rem] font-mono uppercase tracking-wider text-mono-400">
              Access Token / Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full nm-inset rounded-xl px-4 py-2.5 text-xs font-mono text-mono-900 dark:text-mono-100 focus:outline-none"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full nm-btn nm-btn-primary py-3 rounded-xl text-xs font-mono font-bold flex items-center justify-center gap-2 mt-2"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <span>ENTER CONSOLE</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </>
            )}
          </button>
        </form>

        <div className="text-center pt-2">
          <button
            type="button"
            onClick={() => onLogin({ email: 'demo@agentguard.dev', role: 'admin' })}
            className="text-[0.7rem] font-mono text-mono-500 hover:text-mono-900 dark:hover:text-mono-100 underline underline-offset-4"
          >
            Quick Access Demo Bypass
          </button>
        </div>
      </div>
    </div>
  );
}
