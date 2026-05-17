"use client";
import { useRouter } from "next/navigation";
import { CheckCircle, XCircle, BookOpen, RotateCcw } from "lucide-react";

interface ModuleResult {
  module_id: string;
  title: string;
  task_score: number | null;
  interview_score: number | null;
  final_score: number | null;
  passed: boolean;
}

interface Props {
  courseId: string;
  passed: boolean;
  finalScore: number;
  taskScore: number;
  interviewScore: number;
  nextModuleIndex?: number;
  courseComplete?: boolean;
  tutorPlan?: any;
}

export default function ScoreResults({
  courseId, passed, finalScore, taskScore, interviewScore,
  nextModuleIndex, courseComplete, tutorPlan,
}: Props) {
  const router = useRouter();

  return (
    <div className="flex flex-col items-center justify-center h-full p-6 space-y-6 max-w-md mx-auto text-center">
      {passed ? (
        <CheckCircle size={60} className="text-green-400" />
      ) : (
        <XCircle size={60} className="text-red-400" />
      )}

      <div>
        <h2 className={`text-2xl font-bold ${passed ? "text-green-400" : "text-red-400"}`}>
          {courseComplete ? "Course Complete! 🎉" : passed ? "Module Passed!" : "Module Not Passed"}
        </h2>
        <p className="text-white/50 text-sm mt-1">
          {passed ? "Great work! Keep it up." : "Review the feedback and try again."}
        </p>
      </div>

      {/* Score breakdown */}
      <div className="w-full bg-white/5 border border-white/8 rounded-xl p-5 space-y-3">
        <div className="flex justify-between text-sm">
          <span className="text-white/50">Task Score (40%)</span>
          <span className="text-white font-semibold">{taskScore?.toFixed(1) ?? "—"}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-white/50">Interview Score (60%)</span>
          <span className="text-white font-semibold">{interviewScore?.toFixed(1) ?? "—"}</span>
        </div>
        <div className="border-t border-white/8 pt-2 flex justify-between">
          <span className="text-white font-semibold">Final Score</span>
          <span className={`text-xl font-bold ${finalScore >= 60 ? "text-green-400" : "text-red-400"}`}>
            {finalScore?.toFixed(1) ?? "—"}
          </span>
        </div>
      </div>

      {/* Actions */}
      {courseComplete ? (
        <button onClick={() => router.push("/employee/dashboard")}
          className="w-full py-3 bg-green-600 hover:bg-green-500 text-white font-semibold rounded-xl transition flex items-center justify-center gap-2">
          <BookOpen size={16} /> Back to Dashboard
        </button>
      ) : passed && nextModuleIndex !== undefined ? (
        <button onClick={() => router.push(`/employee/courses/${courseId}`)}
          className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl transition">
          Continue to Module {nextModuleIndex + 1} →
        </button>
      ) : !passed ? (
        <div className="w-full space-y-3">
          {tutorPlan && (
            <div className="bg-yellow-900/10 border border-yellow-500/20 rounded-xl p-4 text-left space-y-2">
              <p className="text-xs text-yellow-400 uppercase tracking-widest">Your Tutor Plan</p>
              {tutorPlan.revision_areas && tutorPlan.revision_areas.map((area: string, i: number) => (
                <p key={i} className="text-xs text-yellow-200/70">• {area}</p>
              ))}
            </div>
          )}
          <button onClick={() => router.push(`/employee/courses/${courseId}`)}
            className="w-full py-3 bg-white/10 hover:bg-white/15 text-white font-semibold rounded-xl transition flex items-center justify-center gap-2">
            <RotateCcw size={16} /> Retry Module
          </button>
        </div>
      ) : null}
    </div>
  );
}
