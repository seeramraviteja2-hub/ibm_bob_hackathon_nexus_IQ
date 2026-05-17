"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, ChevronRight } from "lucide-react";
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

export default function LearningPage() {
  const params   = useParams();
  const courseId = params.courseId as string;
  const router   = useRouter();

  const [data, setData]                   = useState<ModuleData | null>(null);
  const [isLoading, setIsLoading]         = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [teachingHistory, setTeachingHistory]   = useState<any[]>([]);

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
