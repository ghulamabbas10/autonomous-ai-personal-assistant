"use client";

import { Activity, CheckSquare2, ChevronDown, CircleHelp, FolderKanban, LoaderCircle, LogOut, Menu, MessageSquareText, PanelLeftClose, Plus, Settings, ShieldCheck, Sparkles, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { authApi, chatApi, getCsrfCookie } from "@/lib/api";
import type { ChatMessage, Conversation, User } from "@/lib/types";
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
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState("");

  useEffect(() => {
    let live = true;
    Promise.all([authApi.me(), chatApi.list()]).then(([currentUser, history]) => {
      if (live) { setUser(currentUser); setConversations(history); }
    }).catch(() => router.replace("/login"));
    return () => { live = false; };
  }, [router]);

  async function logout() {
    try { await authApi.logout(getCsrfCookie()); } finally { router.replace("/login"); }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const content = message.trim();
    if (!content || sending) return;
    setMessage("");
    setSending(true);
    setChatError("");
    const optimistic: ChatMessage = { id: `pending-${Date.now()}`, role: "user", content, token_count: null, created_at: new Date().toISOString() };
    setMessages((current) => [...current, optimistic]);
    try {
      const response = await chatApi.send(content, conversationId, getCsrfCookie());
      setConversationId(response.conversation.id);
      setMessages((current) => [...current.filter((item) => item.id !== optimistic.id), response.user_message, response.assistant_message]);
      setConversations((current) => [response.conversation, ...current.filter((item) => item.id !== response.conversation.id)]);
    } catch (error) {
      setMessages((current) => current.filter((item) => item.id !== optimistic.id));
      setChatError(error instanceof Error ? error.message : "Unable to reach the assistant");
      setMessage(content);
    } finally { setSending(false); }
  }

  async function openConversation(id: string) {
    setMenuOpen(false); setChatError("");
    try { const detail = await chatApi.get(id); setConversationId(id); setMessages(detail.messages); }
    catch (error) { setChatError(error instanceof Error ? error.message : "Unable to load conversation"); }
  }

  function newConversation() { setConversationId(null); setMessages([]); setMessage(""); setChatError(""); setMenuOpen(false); }

  return (
    <main className="workspace">
      <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
        <div className="sidebar-head"><Logo /><button className="sidebar-close" onClick={() => setMenuOpen(false)} aria-label="Close navigation"><X /></button><PanelLeftClose className="desktop-collapse" size={19} /></div>
        <button className="new-chat" onClick={newConversation}><Plus size={17} /> New conversation <span>⌘ K</span></button>
        <nav aria-label="Main navigation">{nav.map(([Icon, label, active]) => <button key={label} className={active ? "active" : ""} disabled={!active}><Icon size={18} />{label}{label === "Approvals" && <i>0</i>}</button>)}</nav>
        {conversations.length > 0 && <div className="history"><p>Recent</p>{conversations.map((conversation) => <button key={conversation.id} className={conversation.id === conversationId ? "selected" : ""} onClick={() => openConversation(conversation.id)}>{conversation.title}</button>)}</div>}
        <div className="sidebar-bottom"><button disabled><Settings size={18} />Settings</button><button disabled><CircleHelp size={18} />Help & feedback</button><div className="profile"><span>{initials(user?.display_name)}</span><div><strong>{user?.display_name ?? "Loading…"}</strong><small>{user?.email ?? ""}</small></div><button onClick={logout} aria-label="Sign out"><LogOut size={17} /></button></div></div>
      </aside>
      {menuOpen && <button className="scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
      <section className="chat-area">
        <header className="topbar"><button className="mobile-menu" onClick={() => setMenuOpen(true)} aria-label="Open navigation"><Menu /></button><button className="conversation-title">{conversationId ? conversations.find((item) => item.id === conversationId)?.title ?? "Conversation" : "New conversation"} <ChevronDown size={15} /></button><div><span className="status-pill"><i /> Free local AI</span><ThemeToggle /></div></header>
        <div className="conversation">
          {messages.length > 0 ? <div className="preview-thread">{messages.map((item) => item.role === "user" ? <div className="user-bubble" key={item.id}>{item.content}</div> : <div className="assistant-preview" key={item.id}><span><Sparkles size={17} /></span><div><p>{item.content}</p></div></div>)}{sending && <div className="assistant-preview"><span><LoaderCircle className="spin" size={17} /></span><div><p>Thinking locally…</p></div></div>}</div> : <Welcome name={user?.display_name} setMessage={setMessage} />}
        </div>
        <div className="composer-wrap">{chatError && <p className="chat-error" role="alert">{chatError}</p>}<form className="composer" onSubmit={submit}><textarea value={message} onChange={(e) => setMessage(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); e.currentTarget.form?.requestSubmit(); } }} placeholder="Ask Aster to plan, research, or organize…" rows={1} maxLength={20000} aria-label="Message"/><div className="composer-actions"><button type="button" className="attach" disabled><Plus size={18} /> Add context</button><button className="send" type="submit" disabled={!message.trim() || sending} aria-label="Send message"><span>↑</span></button></div></form><p>Aster can make mistakes. Review important actions before approval.</p></div>
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
