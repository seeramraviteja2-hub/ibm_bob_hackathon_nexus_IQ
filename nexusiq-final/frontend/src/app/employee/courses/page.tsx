"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BookOpen, Loader2, ChevronRight, Play } from "lucide-react";
import api from "@/lib/api";

interface AssignedCourse {
  course_id: string;
  title: string;
  mode: string;
  status: string;
  current_module_index: number;
}

export default function EmployeeCoursesPage() {
  const router = useRouter();
  const [courses, setCourses] = useState<AssignedCourse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api.get("/api/v1/employee/courses")
      .then(res => setCourses(res.data ?? []))
      .finally(() => setIsLoading(false));
  }, []);

  if (isLoading) return (
    <div className="flex-1 flex items-center justify-center">
      <Loader2 className="animate-spin text-indigo-400" size={36} />
    </div>
  );

  return (
    <div className="p-6 md:p-10 space-y-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-white">My Courses</h1>
      {courses.length === 0 ? (
        <div className="text-center py-20 text-white/30">
          <BookOpen size={40} className="mx-auto mb-4 opacity-30" />
          <p>No courses assigned yet.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {courses.map(c => (
            <div key={c.course_id}
              onClick={() => router.push(`/employee/courses/${c.course_id}`)}
              className="bg-white/5 border border-white/8 rounded-xl p-5 flex items-center justify-between cursor-pointer hover:bg-white/10 transition">
              <div>
                <h2 className="text-white font-semibold">{c.title}</h2>
                <p className="text-xs text-white/40 mt-1">Module {c.current_module_index + 1} · {c.status.replace("_", " ")}</p>
              </div>
              <div className="flex items-center gap-3">
                <button className="flex items-center gap-1 text-xs text-indigo-400 bg-indigo-600/10 px-3 py-1.5 rounded-lg hover:bg-indigo-600/20 transition">
                  <Play size={11} /> Continue
                </button>
                <ChevronRight size={16} className="text-white/30" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
