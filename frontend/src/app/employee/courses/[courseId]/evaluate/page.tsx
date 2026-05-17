"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, ArrowLeft, Shield } from "lucide-react";
import api from "@/lib/api";
import TaskPanel from "@/components/employee/TaskPanel";
import InterviewChat from "@/components/employee/InterviewChat";
import ScoreResults from "@/components/employee/ScoreResults";

type Phase = "task" | "interview" | "results";
interface InterviewTurn { question: string; answer: string; }

export default function EvaluationPage() {
  const params   = useParams();
  const courseId = params.courseId as string;
  const router   = useRouter();

  const [phase, setPhase]                           = useState<Phase>("task");
  const [isLoading, setIsLoading]                   = useState(true);
  const [task, setTask]                             = useState<any>(null);
  const [taskResult, setTaskResult]                 = useState<any>(null);

  const [turns, setTurns]                           = useState<InterviewTurn[]>([]);
  const [currentQuestion, setCurrentQuestion]       = useState("");
  const [questionCount, setQuestionCount]           = useState(0);
  const [interviewLoading, setInterviewLoading]     = useState(false);
  const [isInterviewComplete, setIsInterviewComplete] = useState(false);

  const [finalResult, setFinalResult]               = useState<any>(null);
  const [tutorPlan, setTutorPlan]                   = useState<any>(null);

  useEffect(() => {
    api.get(`/api/v1/employee/courses/${courseId}/task`)
      .then(res => setTask(res.data))
      .catch(err => console.error("Task load failed:", err))
      .finally(() => setIsLoading(false));
  }, [courseId]);

  const handleTaskSubmit = async (file: File) => {
    setIsLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api.post(`/api/v1/employee/courses/${courseId}/task/submit`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setTaskResult({ score: res.data.task_score, feedback: res.data.feedback, passed: res.data.passed_task });
    } catch (err) { console.error("Task submit failed:", err); }
    finally { setIsLoading(false); }
  };

  const startInterview = async () => {
    setPhase("interview");
    setInterviewLoading(true);
    try {
      const res = await api.post(`/api/v1/employee/courses/${courseId}/interview`, { answer: null });
      setCurrentQuestion(res.data.response);
      setQuestionCount(res.data.question_count || 1);
    } catch (err) { console.error("Interview start failed:", err); }
    finally { setInterviewLoading(false); }
  };

  const handleAnswer = async (answer: string) => {
    setInterviewLoading(true);
    const prevQ = currentQuestion;
    try {
      const res = await api.post(`/api/v1/employee/courses/${courseId}/interview`, { answer });
      setTurns(prev => [...prev, { question: prevQ, answer }]);
      if (res.data.interview_complete) {
        setIsInterviewComplete(true);
        await loadResults(res.data);
      } else {
        setCurrentQuestion(res.data.response);
        setQuestionCount(res.data.question_count || 1);
      }
    } catch (err) { console.error("Answer submit failed:", err); }
    finally { setInterviewLoading(false); }
  };

  const loadResults = async (lastRes: any) => {
    try {
      const res = await api.get(`/api/v1/employee/courses/${courseId}/progress`);
      const mods: any[] = res.data.module_progresses || [];
      const latest = mods[mods.length - 1] ?? null;
      const passed = latest?.passed ?? false;
      setFinalResult({
        taskScore:       latest?.task_score ?? taskResult?.score ?? 0,
        interviewScore:  latest?.interview_score ?? lastRes?.interview_score ?? 0,
        finalScore:      latest?.final_score ?? 0,
        passed,
        courseComplete:  lastRes?.course_complete ?? false,
        nextModuleIndex: lastRes?.next_module_index,
      });
      if (!passed) {
        try {
          const t = await api.get(`/api/v1/employee/courses/${courseId}/tutor`);
          setTutorPlan(t.data.tutor_plan);
        } catch { /* non-fatal */ }
      }
      setPhase("results");
    } catch (err) { console.error("Results load failed:", err); }
  };

  const phasePct = phase === "task" ? 33 : phase === "interview" ? 66 : 100;

  if (isLoading && phase === "task") return (
    <div className="flex-1 flex items-center justify-center">
      <div className="text-center space-y-3">
        <Loader2 className="h-10 w-10 animate-spin text-indigo-400 mx-auto" />
        <p className="text-xs text-white/40 uppercase tracking-widest">Generating Evaluation…</p>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="shrink-0">
        <div className="h-0.5 bg-white/5">
          <div className="h-full bg-indigo-500 transition-all duration-500" style={{ width: `${phasePct}%` }} />
        </div>
        <div className="flex items-center justify-between px-6 py-3 border-b border-white/8">
          <button onClick={() => router.push(`/employee/courses/${courseId}`)}
            className="flex items-center gap-1 text-xs text-white/40 hover:text-white transition">
            <ArrowLeft size={13} /> Back
          </button>
          <div className="flex items-center gap-2">
            <Shield size={12} className="text-indigo-400" />
            <span className="text-[10px] font-bold text-white/40 uppercase tracking-widest">
              {phase === "task" ? "Task Evaluation" : phase === "interview" ? "Technical Interview" : "Results"}
            </span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col">
        {phase === "task" && task && (
          <TaskPanel
            task={task}
            onSubmit={handleTaskSubmit}
            result={taskResult}
            isLoading={isLoading}
            onProceedToInterview={startInterview}
          />
        )}
        {phase === "interview" && (
          <InterviewChat
            turns={turns}
            currentQuestion={currentQuestion}
            questionCount={questionCount}
            isLoading={interviewLoading}
            isComplete={isInterviewComplete}
            onAnswer={handleAnswer}
          />
        )}
        {phase === "results" && finalResult && (
          <ScoreResults
            courseId={courseId}
            passed={finalResult.passed}
            finalScore={finalResult.finalScore}
            taskScore={finalResult.taskScore}
            interviewScore={finalResult.interviewScore}
            nextModuleIndex={finalResult.nextModuleIndex}
            courseComplete={finalResult.courseComplete}
            tutorPlan={tutorPlan}
          />
        )}
      </div>
    </div>
  );
}
