import { Sparkles } from "lucide-react";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="logo-wrap" aria-label="Aster home">
      <span className="logo-mark"><Sparkles size={19} strokeWidth={2.3} /></span>
      {!compact && <span className="logo-type">aster</span>}
    </div>
  );
}
