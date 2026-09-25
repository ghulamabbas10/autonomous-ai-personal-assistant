import { BrainCircuit, CheckCircle2, ShieldCheck } from "lucide-react";
import { Logo } from "./logo";
import { ThemeToggle } from "./theme-toggle";

export function AuthShell({ title, copy, children }: { title: string; copy: string; children: React.ReactNode }) {
  return (
    <main className="auth-page">
      <aside className="auth-story">
        <Logo />
        <div className="story-content">
          <span className="eyebrow">Your work, thoughtfully handled</span>
          <h1>Turn intentions into <em>momentum.</em></h1>
          <p>Aster helps you plan, remember, and move important work forward—with you in control.</p>
          <div className="trust-list"><span><BrainCircuit /> Context that compounds</span><span><ShieldCheck /> Approval before action</span><span><CheckCircle2 /> Clear progress, always</span></div>
        </div>
        <p className="story-foot">Private by design · Powered by your chosen model</p>
      </aside>
      <section className="auth-panel">
        <div className="auth-theme"><ThemeToggle /></div>
        <div className="auth-card"><span className="mobile-logo"><Logo /></span><h2>{title}</h2><p>{copy}</p>{children}</div>
      </section>
    </main>
  );
}
