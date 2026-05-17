"use client";
import { ChevronLeft, ChevronRight, CheckCircle, Lock, PlayCircle } from "lucide-react";

interface ModuleItem {
  index: number;
  title: string;
  estimated_minutes: number;
  status: "current" | "completed" | "locked";
}

interface Props {
  modules: ModuleItem[];
  currentModuleIndex: number;
  isCollapsed: boolean;
  onToggle: () => void;
}

export default function CourseSidebar({ modules, currentModuleIndex, isCollapsed, onToggle }: Props) {
  const statusIcon = (s: string) => {
    if (s === "completed") return <CheckCircle size={14} className="text-green-400 shrink-0" />;
    if (s === "current")   return <PlayCircle  size={14} className="text-indigo-400 shrink-0" />;
    return <Lock size={14} className="text-white/20 shrink-0" />;
  };

  return (
    <aside className={`flex flex-col border-r border-white/8 bg-[#111118] transition-all duration-300 ${isCollapsed ? "w-12" : "w-64"}`}>
      <div className="flex items-center justify-between px-3 py-3 border-b border-white/8">
        {!isCollapsed && <span className="text-xs text-white/40 uppercase tracking-widest">Modules</span>}
        <button onClick={onToggle} className="p-1 text-white/30 hover:text-white transition ml-auto">
          {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>
      {!isCollapsed && (
        <div className="flex-1 overflow-y-auto p-2 space-y-0.5">
          {modules.map(mod => (
            <div key={mod.index}
              className={`flex items-start gap-2.5 px-3 py-2.5 rounded-lg ${mod.status === "current" ? "bg-indigo-600/15 border border-indigo-500/30" : "hover:bg-white/5"} transition`}>
              <div className="mt-0.5">{statusIcon(mod.status)}</div>
              <div className="min-w-0">
                <p className={`text-xs font-medium truncate ${mod.status === "locked" ? "text-white/30" : "text-white"}`}>
                  {mod.title}
                </p>
                <p className="text-[10px] text-white/30">{mod.estimated_minutes}m</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}
