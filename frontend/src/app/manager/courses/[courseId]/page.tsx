"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft, Users, Loader2, UserPlus, Trash2,
  CheckCircle, XCircle, Clock, BarChart2, ChevronDown, ChevronUp, Activity,
} from "lucide-react";
import api from "@/lib/api";

interface Employee { id: string; email: string; first_name: string; last_name: string; }
interface EmployeeProgress {
  employee_id: string;
  name: string;
  email: string;
  status: string;
  current_module_index: number;
  total_modules: number;
  completion_rate: number;
  consecutive_fails: number;
  module_progresses: Array<{
    module_index: number;
    module_title: string;
    passed: boolean | null;
    task_score: number | null;
    interview_score: number | null;
    final_score: number | null;
  }>;
}

const statusIcon = (s: string) => {
  if (s === "completed") return <CheckCircle size={13} className="text-green-400" />;
  if (s === "in_progress") return <Clock size={13} className="text-blue-400" />;
  return <Clock size={13} className="text-white/30" />;
};

function EmployeeProgressCard({ progress }: { progress: EmployeeProgress }) {
  const [expanded, setExpanded] = useState(false);
  const pct = Math.round(progress.completion_rate);

  return (
    <div className={`bg-white/5 border rounded-xl transition ${progress.consecutive_fails >= 2 ? "border-red-500/30" : "border-white/8"}`}>
      <div
        className="flex items-center gap-4 p-4 cursor-pointer"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {statusIcon(progress.status)}
            <span className="text-white text-sm font-medium truncate">{progress.name}</span>
            {progress.consecutive_fails >= 2 && (
              <span className="text-[10px] bg-red-900/40 text-red-400 px-2 py-0.5 rounded-full font-bold">
                {progress.consecutive_fails} fails
              </span>
            )}
            {progress.status === "completed" && (
              <span className="text-[10px] bg-green-900/30 text-green-400 px-2 py-0.5 rounded-full font-bold">Well Compiled ✓</span>
            )}
          </div>
          <p className="text-xs text-white/40 mt-0.5">{progress.email}</p>
        </div>

        <div className="shrink-0 text-right space-y-1">
          <p className="text-xs text-white/50">
            Module {progress.current_module_index + 1} / {progress.total_modules}
          </p>
          <div className="flex items-center gap-2">
            <div className="w-20 h-1.5 bg-white/10 rounded-full overflow-hidden">
              <div className="h-full bg-indigo-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
            </div>
            <span className="text-[10px] text-white/40">{pct}%</span>
          </div>
        </div>
        <div className="shrink-0 text-white/30">
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {expanded && progress.module_progresses.length > 0 && (
        <div className="px-4 pb-4 border-t border-white/8 pt-3 space-y-2">
          <p className="text-[10px] text-white/40 uppercase tracking-widest mb-2">Module Breakdown</p>
          {progress.module_progresses.map((mp, i) => (
            <div key={i} className="flex items-center gap-3 text-xs">
              <div className="w-5 shrink-0">
                {mp.passed === true
                  ? <CheckCircle size={12} className="text-green-400" />
                  : mp.passed === false
                  ? <XCircle size={12} className="text-red-400" />
                  : <Clock size={12} className="text-white/20" />}
              </div>
              <span className="text-white/60 flex-1 truncate">{mp.module_title || `Module ${mp.module_index + 1}`}</span>
              {mp.final_score !== null && (
                <span className={`font-semibold ${mp.passed ? "text-green-400" : "text-red-400"}`}>
                  {mp.final_score?.toFixed(0)}
                </span>
              )}
              {mp.task_score !== null && (
                <span className="text-white/30">T:{mp.task_score?.toFixed(0)}</span>
              )}
              {mp.interview_score !== null && (
                <span className="text-white/30">I:{mp.interview_score?.toFixed(0)}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function CourseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const courseId = params.courseId as string;

  const [course, setCourse]         = useState<any>(null);
  const [employees, setEmployees]   = useState<Employee[]>([]);
  const [assigned, setAssigned]     = useState<string[]>([]);
  const [progresses, setProgresses] = useState<EmployeeProgress[]>([]);
  const [isLoading, setIsLoading]   = useState(true);
  const [activeTab, setActiveTab]   = useState<"assign" | "progress">("progress");

  useEffect(() => {
    Promise.all([
      api.get(`/api/v1/manager/courses/${courseId}`),
      api.get("/api/v1/manager/employees"),
      api.get(`/api/v1/manager/courses/${courseId}/assigned`),
      api.get(`/api/v1/manager/courses/${courseId}/progress`).catch(() => ({ data: { employees: [] } })),
    ]).then(([c, e, a, p]) => {
      setCourse(c.data);
      setEmployees(e.data ?? []);
      setAssigned((a.data ?? []).map((x: any) => x.employee_id));
      // Backend returns { employees: [...] } or flat array
      const rawEmployees = Array.isArray(p.data) ? p.data : (p.data?.employees ?? []);
      const total = (c.data?.total_modules) || 1;
      const mapped: EmployeeProgress[] = rawEmployees.map((emp: any) => ({
        employee_id: emp.employee_id,
        name: emp.name || "Unknown",
        email: emp.email || "",
        status: emp.status || "assigned",
        current_module_index: emp.current_module_index ?? 0,
        total_modules: total,
        completion_rate: emp.current_module_index ? Math.round((emp.current_module_index / total) * 100) : 0,
        consecutive_fails: emp.consecutive_fails ?? 0,
        module_progresses: emp.module_progresses ?? [],
      }));
      setProgresses(mapped);
    }).finally(() => setIsLoading(false));
  }, [courseId]);

  const assign = (empId: string) => {
    api.post(`/api/v1/manager/courses/${courseId}/assign`, { employee_id: empId })
      .then(() => setAssigned(prev => [...prev, empId]));
  };

  const unassign = (empId: string) => {
    api.post(`/api/v1/manager/courses/${courseId}/unassign`, { employee_id: empId })
      .then(() => setAssigned(prev => prev.filter(id => id !== empId)));
  };

  const completed = progresses.filter(p => p.status === "completed").length;
  const struggling = progresses.filter(p => p.consecutive_fails >= 2).length;

  if (isLoading) return (
    <div className="flex-1 flex items-center justify-center">
      <Loader2 className="h-10 w-10 animate-spin text-indigo-400" />
    </div>
  );

  return (
    <div className="p-6 md:p-10 space-y-6 max-w-5xl mx-auto">
      <button onClick={() => router.back()} className="flex items-center gap-1 text-xs text-white/40 hover:text-white transition">
        <ArrowLeft size={13} /> Back
      </button>

      <div>
        <h1 className="text-2xl font-bold text-white">{course?.title}</h1>
        <p className="text-sm text-white/50 mt-1">{course?.description || "No description"}</p>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-white/5 border border-white/8 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-white">{assigned.length}</p>
          <p className="text-xs text-white/40 mt-1">Assigned</p>
        </div>
        <div className="bg-white/5 border border-white/8 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-green-400">{completed}</p>
          <p className="text-xs text-white/40 mt-1">Completed</p>
        </div>
        <div className="bg-white/5 border border-white/8 rounded-xl p-4 text-center">
          <p className="text-2xl font-bold text-red-400">{struggling}</p>
          <p className="text-xs text-white/40 mt-1">Struggling</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white/5 p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab("progress")}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-semibold transition ${activeTab === "progress" ? "bg-indigo-600 text-white" : "text-white/40 hover:text-white"}`}>
          <Activity size={12} /> Progress Tracking
        </button>
        <button
          onClick={() => setActiveTab("assign")}
          className={`flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-semibold transition ${activeTab === "assign" ? "bg-indigo-600 text-white" : "text-white/40 hover:text-white"}`}>
          <Users size={12} /> Assign Employees
        </button>
      </div>

      {/* Progress tracking tab */}
      {activeTab === "progress" && (
        <div className="space-y-3">
          {progresses.length === 0 && (
            <div className="text-center py-12 text-white/30">
              <BarChart2 size={36} className="mx-auto mb-3 opacity-30" />
              <p>No employee progress yet. Assign employees and they'll appear here.</p>
            </div>
          )}
          {progresses.map(p => (
            <EmployeeProgressCard key={p.employee_id} progress={p} />
          ))}
        </div>
      )}

      {/* Assign employees tab */}
      {activeTab === "assign" && (
        <div className="space-y-2">
          {employees.map(emp => {
            const isAssigned = assigned.includes(emp.id);
            return (
              <div key={emp.id} className="flex items-center justify-between p-3 bg-white/5 border border-white/8 rounded-lg">
                <span className="text-sm text-white">
                  {emp.first_name} {emp.last_name}
                  <span className="text-white/40 ml-2">({emp.email})</span>
                </span>
                <button
                  onClick={() => isAssigned ? unassign(emp.id) : assign(emp.id)}
                  className={`flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg transition ${
                    isAssigned
                      ? "bg-red-600/20 text-red-400 hover:bg-red-600/30"
                      : "bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30"
                  }`}>
                  {isAssigned ? <><Trash2 size={11} /> Unassign</> : <><UserPlus size={11} /> Assign</>}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
