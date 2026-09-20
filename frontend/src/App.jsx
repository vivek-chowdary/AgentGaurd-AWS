import React, { useState } from 'react';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';

export default function App() {
  const [user, setUser] = useState({ email: 'demo@agentguard.dev', role: 'admin' });

  // For demo: skip login by default
  // To enable login: change initial state to null
  // const [user, setUser] = useState(null);

  if (!user) {
    return <Login onLogin={setUser} />;
  }

  return <Dashboard />;
}
