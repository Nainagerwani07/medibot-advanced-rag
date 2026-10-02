"use client";

import { useState } from "react";
import { login, type Session } from "@/lib/api";

const DEMO_ACCOUNTS = [
  { username: "dr.mehta", password: "doctor", role: "doctor" },
  { username: "nurse.priya", password: "nurse", role: "nurse" },
  { username: "billing.ravi", password: "billing_executive", role: "billing_executive" },
  { username: "tech.anand", password: "technician", role: "technician" },
  { username: "admin.sys", password: "admin", role: "admin" },
];

export default function Login({ onLogin }: { onLogin: (s: Session) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(u = username, p = password) {
    setBusy(true);
    setError(null);
    try {
      onLogin(await login(u, p));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login">
      <div className="login-card">
        <div className="brand">
          <span className="logo">✚</span>
          <div>
            <h1>MediBot</h1>
            <p className="muted">MediAssist Health Network · internal assistant</p>
          </div>
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <label>
            Username
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={busy || !username || !password}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <div className="demo">
          <p className="muted">Demo accounts</p>
          <div className="demo-grid">
            {DEMO_ACCOUNTS.map((a) => (
              <button
                key={a.username}
                className="demo-btn"
                disabled={busy}
                onClick={() => {
                  setUsername(a.username);
                  setPassword(a.password);
                  submit(a.username, a.password);
                }}
              >
                <span className={`role-dot role-${a.role}`} />
                <span>{a.username}</span>
                <span className="muted small">{a.role}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
