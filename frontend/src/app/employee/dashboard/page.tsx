"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, Play, CheckCircle, Loader2, ChevronRight } from "lucide-react";
import api from "@/lib/api";

interface AssignedCourse {
  course_id: string;
  title: string;
  mode: string;
  status: string;
  current_module_index: number;
}

const statusColor: Record<string, string> = {
  assigned:    "text-yellow-400 bg-yellow-900/30",
  in_progress: "text-blue-400 bg-blue-900/30",
  completed:   "text-green-400 bg-green-900/30",
};

const statusIcon: Record<string, React.ReactNode> = {
  assigned:    <BookOpen size={12} />,
  in_progress: <Play size={12} />,
  completed:   <CheckCircle size={12} />,
};

export default function EmployeeDashboard() {
  const router = useRouter();
  const [courses, setCourses] = useState<AssignedCourse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.get("/api/v1/employee/courses")
      .then(res => setCourses(res.data ?? []))
      .catch(err => {
        console.error(err);
        setError("Failed to load your courses.");
      })
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return (
    <div className="flex-1 flex items-center justify-center">
      <Loader2 className="animate-spin text-indigo-400" size={36} />
    </div>
  );

  return (
    <div className="p-6 md:p-10 space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white">My Learning</h1>
        <p className="text-sm text-white/40 mt-1">Pick up where you left off</p>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {courses.length === 0 && !error && (
        <div className="text-center py-20 text-white/30">
          <BookOpen size={40} className="mx-auto mb-4 opacity-30" />
          <p>No courses assigned yet. Your manager will assign courses shortly.</p>
        </div>
      )}

      <div className="space-y-3">
        {courses.map(course => (
          <div
            key={course.course_id}
            onClick={() => router.push(`/employee/courses/${course.course_id}`)}
            className="bg-white/5 border border-white/8 rounded-xl p-5 flex items-center justify-between cursor-pointer hover:bg-white/10 transition"
          >
            <div className="space-y-1.5">
              <div className="flex items-center gap-3">
                <h2 className="text-white font-semibold">{course.title}</h2>
                <span className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${statusColor[course.status] ?? "text-white/40 bg-white/5"}`}>
                  {statusIcon[course.status]}
                  {course.status.replace("_", " ")}
                </span>
              </div>
              <p className="text-xs text-white/40">
                Module {course.current_module_index + 1} · {course.mode.replace("_", " ")}
              </p>
            </div>
            <ChevronRight size={16} className="text-white/30" />
          </div>
        ))}
      </div>
    </div>
  );
}
