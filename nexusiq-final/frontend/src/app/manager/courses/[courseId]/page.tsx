"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Users, Loader2, UserPlus, Trash2 } from "lucide-react";
import api from "@/lib/api";

interface Employee { id: string; email: string; first_name: string; last_name: string; }

export default function CourseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const courseId = params.courseId as string;
  const [course, setCourse] = useState<any>(null);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [assigned, setAssigned] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get(`/api/v1/manager/courses/${courseId}`),
      api.get("/api/v1/manager/employees"),
      api.get(`/api/v1/manager/courses/${courseId}/assigned`)
    ]).then(([c, e, a]) => {
      setCourse(c.data);
      setEmployees(e.data ?? []);
      setAssigned((a.data ?? []).map((x: any) => x.employee_id));
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

  if (isLoading) return <div className="flex-1 flex items-center justify-center"><Loader2 className="h-10 w-10 animate-spin text-indigo-400" /></div>;

  return (
    <div className="p-6 md:p-10 space-y-6 max-w-5xl mx-auto">
      <button onClick={() => router.back()} className="flex items-center gap-1 text-xs text-white/40 hover:text-white transition">
        <ArrowLeft size={13} /> Back
      </button>
      <div>
        <h1 className="text-2xl font-bold text-white">{course?.title}</h1>
        <p className="text-sm text-white/50 mt-1">{course?.description || "No description"}</p>
      </div>
      <div className="bg-white/5 border border-white/8 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Users size={16} className="text-indigo-400" />
          <h2 className="text-white font-semibold">Assigned Employees ({assigned.length})</h2>
        </div>
        <div className="space-y-2">
          {employees.map(emp => {
            const isAssigned = assigned.includes(emp.id);
            return (
              <div key={emp.id} className="flex items-center justify-between p-3 bg-white/5 border border-white/8 rounded-lg">
                <span className="text-sm text-white">{emp.first_name} {emp.last_name} <span className="text-white/40">({emp.email})</span></span>
                <button onClick={() => isAssigned ? unassign(emp.id) : assign(emp.id)}
                  className={`flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg transition ${isAssigned ? "bg-red-600/20 text-red-400 hover:bg-red-600/30" : "bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30"}`}>
                  {isAssigned ? <><Trash2 size={11} /> Unassign</> : <><UserPlus size={11} /> Assign</>}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
