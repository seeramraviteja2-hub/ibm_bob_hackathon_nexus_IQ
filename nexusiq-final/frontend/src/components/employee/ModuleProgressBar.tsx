"use client";

interface Props {
  concepts: string[];
  teachingHistory: Array<{ role: string; content: string }>;
}

export default function ModuleProgressBar({ concepts, teachingHistory }: Props) {
  const assistantTurns = teachingHistory.filter(m => m.role === "assistant").length;
  const pct = concepts.length > 0 ? Math.min(100, Math.round((assistantTurns / Math.max(concepts.length, 1)) * 100)) : 0;

  return (
    <div className="px-6 py-2.5 border-b border-white/8 flex items-center gap-4">
      <span className="text-xs text-white/40 shrink-0">{pct}% covered</span>
      <div className="flex-1 h-1 bg-white/8 rounded-full overflow-hidden">
        <div className="h-full bg-indigo-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-white/30 shrink-0">{concepts.length} concepts</span>
    </div>
  );
}
