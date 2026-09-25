"use client";

import { Activity, CheckSquare2, ChevronDown, CircleHelp, FolderKanban, LogOut, Menu, MessageSquareText, PanelLeftClose, Plus, Settings, ShieldCheck, Sparkles, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { authApi, getCsrfCookie } from "@/lib/api";
import type { User } from "@/lib/types";
import { Logo } from "./logo";
import { ThemeToggle } from "./theme-toggle";

const nav = [
  [MessageSquareText, "Chat", true], [FolderKanban, "Projects", false], [CheckSquare2, "Tasks", false],
  [ShieldCheck, "Approvals", false], [Activity, "Activity", false],
] as const;

export function AppShell() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [preview, setPreview] = useState("");

  useEffect(() => {
    let live = true;
    authApi.me().then((value) => { if (live) setUser(value); }).catch(() => router.replace("/login"));
    return () => { live = false; };
  }, [router]);

  async function logout() {
    try { await authApi.logout(getCsrfCookie()); } finally { router.replace("/login"); }
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!message.trim()) return;
    setPreview(message.trim());
    setMessage("");
  }

  return (
    <main className="workspace">
      <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
        <div className="sidebar-head"><Logo /><button className="sidebar-close" onClick={() => setMenuOpen(false)} aria-label="Close navigation"><X /></button><PanelLeftClose className="desktop-collapse" size={19} /></div>
        <button className="new-chat"><Plus size={17} /> New conversation <span>⌘ K</span></button>
        <nav aria-label="Main navigation">{nav.map(([Icon, label, active]) => <button key={label} className={active ? "active" : ""} disabled={!active}><Icon size={18} />{label}{label === "Approvals" && <i>0</i>}</button>)}</nav>
        <div className="sidebar-bottom"><button disabled><Settings size={18} />Settings</button><button disabled><CircleHelp size={18} />Help & feedback</button><div className="profile"><span>{initials(user?.display_name)}</span><div><strong>{user?.display_name ?? "Loading…"}</strong><small>{user?.email ?? ""}</small></div><button onClick={logout} aria-label="Sign out"><LogOut size={17} /></button></div></div>
      </aside>
      {menuOpen && <button className="scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
      <section className="chat-area">
        <header className="topbar"><button className="mobile-menu" onClick={() => setMenuOpen(true)} aria-label="Open navigation"><Menu /></button><button className="conversation-title">New conversation <ChevronDown size={15} /></button><div><span className="status-pill"><i /> Local mock</span><ThemeToggle /></div></header>
        <div className="conversation">
          {preview ? <div className="preview-thread"><div className="user-bubble">{preview}</div><div className="assistant-preview"><span><Sparkles size={17} /></span><div><strong>Chat execution arrives in Phase 5</strong><p>Your message is safely kept in this preview only. The provider-neutral runtime will connect this composer to your free local model next.</p></div></div></div> : <Welcome name={user?.display_name} setMessage={setMessage} />}
        </div>
        <div className="composer-wrap"><form className="composer" onSubmit={submit}><textarea value={message} onChange={(e) => setMessage(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit(); } }} placeholder="Ask Aster to plan, research, or organize…" rows={1} aria-label="Message"/><div className="composer-actions"><button type="button" className="attach" disabled><Plus size={18} /> Add context</button><button className="send" type="submit" disabled={!message.trim()} aria-label="Send message"><span>↑</span></button></div></form><p>Aster can make mistakes. Review important actions before approval.</p></div>
      </section>
    </main>
  );
}

function Welcome({ name, setMessage }: { name?: string; setMessage: (value: string) => void }) {
  const firstName = name?.trim().split(/\s+/)[0];
  const prompts = ["Plan my priorities for this week", "Turn a goal into actionable tasks", "Organize notes into a clear brief"];
  return <div className="welcome"><span className="welcome-mark"><Sparkles size={25} /></span><p className="eyebrow">A focused place to begin</p><h1>{firstName ? `Good to see you, ${firstName}.` : "Good to see you."}</h1><p>What would you like to move forward today?</p><div className="suggestions">{prompts.map((prompt) => <button key={prompt} onClick={() => setMessage(prompt)}>{prompt}<span>→</span></button>)}</div></div>;
}

function initials(name?: string): string { return name?.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "A"; }
