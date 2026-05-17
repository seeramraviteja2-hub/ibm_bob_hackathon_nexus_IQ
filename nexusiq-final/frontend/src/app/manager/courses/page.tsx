"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, BookOpen, Users, Loader2, ChevronRight } from "lucide-react";
import api from "@/lib/api";
import CourseBuilderModal from "@/components/manager/CourseBuilderModal";

interface CourseSummary {
  course_id: string;
  title: string;
  mode: string;
  status: string;
  total_modules: number;
  total_assigned: number;
  created_at: string | null;
}

const statusColor: Record<string, string> = {
  draft:    "text-yellow-400 bg-yellow-900/30",
  active:   "text-green-400 bg-green-900/30",
  archived: "text-white/30 bg-white/5",
};

export default function ManagerCoursesPage() {
  const router = useRouter();
  const [courses, setCourses]     = useState<CourseSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [error, setError]         = useState<string | null>(null);

  const fetchCourses = () => {
    setIsLoading(true);
    api.get("/api/v1/manager/courses")
      .then(res => setCourses(res.data ?? []))
      .catch(err => { console.error(err); setError("Failed to load courses."); })
      .finally(() => setIsLoading(false));
  };

  useEffect(() => { fetchCourses(); }, []);

  if (isLoading) return (
    <div className="flex-1 flex items-center justify-center">
      <Loader2 className="h-10 w-10 animate-spin text-indigo-400" />
    </div>
  );

  return (
    <div className="p-6 md:p-10 space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Courses</h1>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-semibold transition">
          <Plus size={15} /> New Course
        </button>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {courses.length === 0 && !error && (
        <div className="text-center py-20 text-white/30">
          <BookOpen size={40} className="mx-auto mb-4 opacity-30" />
          <p>No courses yet. Create your first one above.</p>
        </div>
      )}

      <div className="space-y-3">
        {courses.map(course => (
          <div
            key={course.course_id}
            onClick={() => router.push(`/manager/courses/${course.course_id}`)}
            className="bg-white/5 border border-white/8 rounded-xl p-5 flex items-center justify-between cursor-pointer hover:bg-white/10 transition"
          >
            <div className="space-y-1.5">
              <div className="flex items-center gap-3">
                <h2 className="text-white font-semibold">{course.title}</h2>
                <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${statusColor[course.status] ?? "text-white/40 bg-white/5"}`}>
                  {course.status}
                </span>
                <span className="text-[10px] text-white/30 uppercase bg-white/5 px-2 py-0.5 rounded-full">
                  {course.mode.replace("_", " ")}
                </span>
              </div>
              <div className="flex items-center gap-4 text-xs text-white/40">
                <span className="flex items-center gap-1"><BookOpen size={11} /> {course.total_modules} modules</span>
                <span className="flex items-center gap-1"><Users size={11} /> {course.total_assigned} assigned</span>
                {course.created_at && <span>{new Date(course.created_at).toLocaleDateString()}</span>}
              </div>
            </div>
            <ChevronRight size={16} className="text-white/30" />
          </div>
        ))}
      </div>

      {showModal && (
        <CourseBuilderModal onClose={() => { setShowModal(false); fetchCourses(); }} />
      )}
    </div>
  );
}
