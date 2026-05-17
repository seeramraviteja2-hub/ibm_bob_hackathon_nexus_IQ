"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, ChevronRight, Cpu, Zap, Bot, Activity, ChevronDown, ChevronUp } from "lucide-react";
import api from "@/lib/api";
import CourseSidebar from "@/components/employee/CourseSidebar";
import TeachingChat from "@/components/employee/TeachingChat";
import ModuleProgressBar from "@/components/employee/ModuleProgressBar";

interface ModuleData {
  session_id: string;
  current_module_index: number;
  current_module: {
    id: string;
    title: string;
    concepts: string[];
    code_examples: any[];
    learning_goals: string[];
    difficulty: string;
    estimated_hours: number;
  };
  total_modules: number;
  course_title: string;
  modules: Array<{ id: string; title: string; concepts: string[]; estimated_hours: number; }>;
  agents_status: Record<string, string>;
}

// Small collapsible agent status panel shown alongside the chat
function AgentPanel({ agentsStatus, isExpanded, onToggle }: {
  agentsStatus: Record<string, string>;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const providerFromStatus = (val: string) => {
    if (val.includes("bob") || val.includes("ibm")) return "IBM Bob";
    if (val.includes("gemini")) return "Gemini";
    if (val.includes("cerebras")) return "Cerebras";
    if (val.includes("groq")) return "Groq";
    return "IBM Bob";
  };

  const agents = [
    { key: "teaching_agent",  label: "Teaching Agent" },
    { key: "course_gen_agent", label: "Course Gen" },
    { key: "progress_agent",  label: "Progress" },
  ];

  const statusColor = (s: string) => {
    if (s === "running") return "text-indigo-400";
    if (s === "complete" || s === "completed") return "text-green-400";
    if (s === "error" || s === "failed") return "text-red-400";
    return "text-white/30";
  };

  const statusDot = (s: string) => {
    if (s === "running") return "bg-indigo-400 animate-pulse";
    if (s === "complete" || s === "completed") return "bg-green-400";
    if (s === "error" || s === "failed") return "bg-red-400";
    return "bg-white/15";
  };

  return (
    <div className="shrink-0 border-b border-white/8 bg-[#0d0d14]">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-4 py-2 text-[10px] text-white/40 uppercase tracking-widest hover:bg-white/4 transition"
      >
        <Activity size={10} className="text-indigo-400" />
        <span>Agent Status</span>
        <div className="ml-auto">{isExpanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}</div>
      </button>

      {isExpanded && (
        <div className="px-4 pb-3 grid grid-cols-3 gap-2">
          {agents.map(({ key, label }) => {
            const val = agentsStatus?.[key] || "idle";
            const provider = providerFromStatus(val);
            return (
              <div key={key} className="flex flex-col gap-0.5 bg-white/4 rounded-lg p-2">
                <div className="flex items-center gap-1">
                  <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${statusDot(val)}`} />
                  <span className={`text-[9px] font-semibold uppercase tracking-wider ${statusColor(val)}`}>{val}</span>
                </div>
                <span className="text-[9px] text-white/50">{label}</span>
                <div className="flex items-center gap-0.5 text-[9px] text-white/25 mt-0.5">
                  {provider === "IBM Bob" ? <Cpu size={8} className="text-indigo-300/50" /> : <Zap size={8} className="text-amber-300/50" />}
                  {provider}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function LearningPage() {
  const params   = useParams();
  const courseId = params.courseId as string;
  const router   = useRouter();

  const [data, setData]                   = useState<ModuleData | null>(null);
  const [isLoading, setIsLoading]         = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [teachingHistory, setTeachingHistory]   = useState<any[]>([]);
  const [agentPanelExpanded, setAgentPanelExpanded] = useState(false);

  useEffect(() => {
    api.get(`/api/v1/employee/courses/${courseId}/module`)
      .then(res => setData(res.data))
      .catch(err => console.error("Module load failed:", err))
      .finally(() => setIsLoading(false));
  }, [courseId]);

  if (isLoading) return (
    <div className="flex-1 flex items-center justify-center">
      <Loader2 className="h-10 w-10 animate-spin text-indigo-400" />
    </div>
  );

  if (!data) return (
    <div className="p-8 text-white/40">Failed to load curriculum. Please try again.</div>
  );

  const sidebarModules = data.modules.map((m, idx) => ({
    index: idx,
    title: m.title,
    estimated_minutes: Math.round((m.estimated_hours || 1) * 60),
    status: (
      idx < data.current_module_index ? "completed" :
      idx === data.current_module_index ? "current" : "locked"
    ) as "current" | "completed" | "locked",
  }));

  return (
    <div className="flex-1 flex min-h-0 overflow-hidden">
      <CourseSidebar
        modules={sidebarModules}
        currentModuleIndex={data.current_module_index}
        isCollapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(c => !c)}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <div className="shrink-0 px-6 py-3 border-b border-white/8 flex items-center justify-between">
          <div>
            <p className="text-white font-semibold text-sm">{data.course_title}</p>
            <p className="text-xs text-white/40">
              Module {data.current_module_index + 1} of {data.total_modules} · {data.current_module.title}
            </p>
          </div>
          <button
            onClick={() => router.push(`/employee/courses/${courseId}/evaluate`)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-indigo-600/15 text-indigo-300 hover:bg-indigo-600/30 border border-indigo-500/30 rounded-lg transition">
            Evaluate <ChevronRight size={12} />
          </button>
        </div>

        {/* Agent status collapsible panel */}
        <AgentPanel
          agentsStatus={data.agents_status || {}}
          isExpanded={agentPanelExpanded}
          onToggle={() => setAgentPanelExpanded(e => !e)}
        />

        <ModuleProgressBar
          concepts={data.current_module.concepts}
          teachingHistory={teachingHistory}
        />

        <div className="flex-1 min-h-0 overflow-hidden">
          <TeachingChat
            courseId={courseId}
            moduleTitle={data.current_module.title}
            concepts={data.current_module.concepts}
            initialHistory={[]}
            onComplete={() => router.push(`/employee/courses/${courseId}/evaluate`)}
          />
        </div>
      </div>
    </div>
  );
}
