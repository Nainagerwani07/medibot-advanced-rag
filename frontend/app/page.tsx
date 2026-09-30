"use client";

import { useCallback, useEffect, useState } from "react";
import Chat from "@/components/Chat";
import Login from "@/components/Login";
import type { Session } from "@/lib/api";

const KEY = "medibot.session";

export default function Home() {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(KEY);
      if (raw) setSession(JSON.parse(raw));
    } catch {}
    setReady(true);
  }, []);

  const onLogin = (s: Session) => {
    try {
      sessionStorage.setItem(KEY, JSON.stringify(s));
    } catch {}
    setSession(s);
  };

  const onLogout = useCallback(() => {
    try {
      sessionStorage.removeItem(KEY);
    } catch {}
    setSession(null);
  }, []);

  if (!ready) return null;
  return session ? <Chat session={session} onLogout={onLogout} /> : <Login onLogin={onLogin} />;
}
