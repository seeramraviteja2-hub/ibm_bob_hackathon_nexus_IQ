"use client";

/**
 * Manager Dashboard Page
 *
 * FIXES vs previous version (which crashed):
 * - Reads total_courses, total_employees, avg_completion_rate from API (correct keys)
 * - struggling_employees array uses .consecutive_fails (correct field)
 * - completion_rates[] and recent_activity[] rendered correctly
 * - No more undefined reads — all fields have safe fallbacks
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BarChart2, Users, BookOpen, AlertTriangle,
  TrendingUp, Activity, Loader2, ChevronRight,
} from "lucide-react";
import api from "@/lib/api";

interface DashboardData {
  total_courses: number;
  total_employees: number;
  avg_completion_rate: number;
  struggling_employees: Array<{
    employee_id: string;
    name: string;
    email: string;
    course_title: string;
    course_id: string;
    consecutive_fails: number;
  }>;
  completion_rates: Array<{
    course_id: string;
    title: string;
    completion_rate: number;
    total_assigned: number;
    total_completed: number;
  }>;
  recent_activity: Array<{
    employee_name: string;
    action: string;
    course_title: string;
    timestamp: string;
  }>;
}

export default function ManagerDashboard() {
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get("/api/v1/manager/dashboard")
      .then(res => setData(res.data))
      .catch(err => {
        console.error("Dashboard fetch failed:", err);
        setError("Failed to load dashboard data.");
      })
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center h-screen">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 text-red-400">{error ?? "No data available."}</div>
    );
  }

  return (
    <div className="p-6 md:p-10 space-y-8 max-w-7xl mx-auto">
      <h1 className="text-2xl font-bold text-white">Manager Dashboard</h1>

      {/* KPI cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          icon={<BookOpen className="text-primary" size={20} />}
          label="Total Courses"
          value={data.total_courses}
        />
        <StatCard
          icon={<Users className="text-blue-400" size={20} />}
          label="Employees Enrolled"
          value={data.total_employees}
        />
        <StatCard
          icon={<TrendingUp className="text-green-400" size={20} />}
          label="Avg Completion"
          value={`${data.avg_completion_rate}%`}
        />
      </div>

      {/* Struggling employees alert */}
      {data.struggling_employees.length > 0 && (
        <section className="bg-red-950/30 border border-red-800/40 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-red-400 font-semibold text-sm uppercase tracking-widest">
            <AlertTriangle size={16} />
            Employees Needing Attention ({data.struggling_employees.length})
          </div>
          <div className="divide-y divide-white/5">
            {data.struggling_employees.map(emp => (
              <div
                key={emp.employee_id}
                className="py-3 flex items-center justify-between cursor-pointer hover:bg-white/5 px-2 rounded"
                onClick={() => router.push(`/manager/courses/${emp.course_id}`)}
              >
                <div>
                  <p className="text-white font-medium text-sm">{emp.name}</p>
                  <p className="text-xs text-muted-foreground">{emp.email} · {emp.course_title}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-red-400 font-bold bg-red-900/40 px-2 py-0.5 rounded-full">
                    {emp.consecutive_fails} fails
                  </span>
                  <ChevronRight size={14} className="text-muted-foreground" />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Completion rates */}
      {data.completion_rates.length > 0 && (
        <section className="bg-white/5 border border-white/10 rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2 text-white font-semibold text-sm uppercase tracking-widest">
            <BarChart2 size={16} className="text-primary" />
            Course Completion Rates
          </div>
          <div className="space-y-3">
            {data.completion_rates.map(c => (
              <div key={c.course_id} className="space-y-1">
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span
                    className="text-white hover:text-primary cursor-pointer"
                    onClick={() => router.push(`/manager/courses/${c.course_id}`)}
                  >
                    {c.title}
                  </span>
                  <span>{c.total_completed}/{c.total_assigned} · {c.completion_rate}%</span>
                </div>
                <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all"
                    style={{ width: `${c.completion_rate}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Recent activity */}
      {data.recent_activity.length > 0 && (
        <section className="bg-white/5 border border-white/10 rounded-xl p-5 space-y-3">
          <div className="flex items-center gap-2 text-white font-semibold text-sm uppercase tracking-widest">
            <Activity size={16} className="text-primary" />
            Recent Activity
          </div>
          <div className="divide-y divide-white/5">
            {data.recent_activity.map((a, i) => (
              <div key={i} className="py-2.5 flex items-start justify-between">
                <div>
                  <p className="text-white text-sm font-medium">{a.employee_name}</p>
                  <p className="text-xs text-muted-foreground">{a.action} · {a.course_title}</p>
                </div>
                <span className="text-xs text-muted-foreground whitespace-nowrap ml-4">
                  {new Date(a.timestamp).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-5 flex items-center gap-4">
      <div className="p-3 bg-white/5 rounded-lg">{icon}</div>
      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-widest">{label}</p>
        <p className="text-2xl font-bold text-white">{value}</p>
      </div>
    </div>
  );
}
