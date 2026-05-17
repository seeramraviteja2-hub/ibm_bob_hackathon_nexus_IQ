"use client";

/**
 * CourseBuilderModal — Production Fixed.
 * Props: onClose() — called when user closes or after success.
 *
 * Flow:
 *   Step 1: title + description + mode → POST /manager/courses (JSON)
 *   Step 2: upload spec/code files → POST /manager/courses/{id}/generate (FormData)
 *   Step 3: poll /generate/status until complete or failed
 */

import { useState, useEffect, useRef } from "react";
import { X, Upload, CheckCircle2, Loader2, FileText, Code, ChevronLeft } from "lucide-react";
import api from "@/lib/api";

interface Props {
  onClose: () => void;
}

type Mode = "new_project" | "legacy_codebase";
type GenStatus = "idle" | "queued" | "running" | "complete" | "failed";

export default function CourseBuilderModal({ onClose }: Props) {
  const [step, setStep]           = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [courseId, setCourseId]   = useState<string | null>(null);
  const [error, setError]         = useState<string | null>(null);
  const [title, setTitle]         = useState("");
  const [description, setDesc]    = useState("");
  const [mode, setMode]           = useState<Mode>("new_project");
  const [files, setFiles]         = useState<File[]>([]);
  const fileRef                   = useRef<HTMLInputElement>(null);
  const [genStatus, setGenStatus] = useState<GenStatus>("idle");
  const [genDetail, setGenDetail] = useState("");
  const pollRef                   = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const handleStep1 = async () => {
    if (!title.trim()) { setError("Title is required."); return; }
    setIsLoading(true); setError(null);
    try {
      const res = await api.post("/api/v1/manager/courses", { title, description, mode });
      setCourseId(res.data.id);
      setStep(2);
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to create course.");
    } finally { setIsLoading(false); }
  };

  const handleStep2 = async () => {
    if (!courseId || files.length === 0) { setError("Please attach at least one file."); return; }
    setIsLoading(true); setError(null); setStep(3); setGenStatus("queued");
    try {
      const formData = new FormData();
      files.forEach(f => formData.append("files", f));
      await api.post(`/api/v1/manager/courses/${courseId}/generate`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      pollRef.current = setInterval(async () => {
        try {
          const sr = await api.get(`/api/v1/manager/courses/${courseId}/generate/status`);
          const s: GenStatus = sr.data.status;
          setGenStatus(s); setGenDetail(sr.data.detail ?? "");
          if (s === "complete" || s === "failed") clearInterval(pollRef.current!);
        } catch { /* ignore */ }
      }, 2000);
    } catch (err: any) {
      setGenStatus("failed"); setGenDetail(err.response?.data?.error || "Generation failed.");
    } finally { setIsLoading(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-[#111118] border border-white/10 rounded-2xl shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/8">
          <div>
            <h2 className="text-white font-semibold">New Course</h2>
            <p className="text-xs text-white/40">Step {step} of 3</p>
          </div>
          <button onClick={onClose} className="p-1 text-white/30 hover:text-white transition"><X size={18} /></button>
        </div>
        <div className="h-0.5 bg-white/5">
          <div className="h-full bg-indigo-500 transition-all" style={{ width: `${(step / 3) * 100}%` }} />
        </div>

        <div className="p-6 space-y-5">
          {step === 1 && (
            <>
              <div className="space-y-1">
                <label className="text-xs text-white/50 uppercase tracking-widest">Course Title *</label>
                <input value={title} onChange={e => setTitle(e.target.value)}
                  placeholder="e.g. FastAPI Microservices Bootcamp"
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500 transition" />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-white/50 uppercase tracking-widest">Description</label>
                <textarea value={description} onChange={e => setDesc(e.target.value)} rows={3}
                  placeholder="Brief overview…"
                  className="w-full px-4 py-2.5 bg-white/5 border border-white/10 rounded-lg text-white text-sm focus:outline-none focus:border-indigo-500 transition resize-none" />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-white/50 uppercase tracking-widest">Training Mode</label>
                <div className="grid grid-cols-2 gap-3">
                  {(["new_project", "legacy_codebase"] as Mode[]).map(m => (
                    <button key={m} onClick={() => setMode(m)}
                      className={`p-3 rounded-xl border text-left transition ${mode === m ? "border-indigo-500 bg-indigo-600/15" : "border-white/8 bg-white/5 hover:border-white/20"}`}>
                      <div className="flex items-center gap-2 mb-1">
                        {m === "new_project" ? <FileText size={14} className="text-indigo-400" /> : <Code size={14} className="text-green-400" />}
                        <span className="text-xs font-semibold text-white">
                          {m === "new_project" ? "New Project" : "Legacy Codebase"}
                        </span>
                      </div>
                      <p className="text-[10px] text-white/40">
                        {m === "new_project" ? "Upload spec → AI builds course" : "Upload source code → AI teaches it"}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
              {error && <p className="text-red-400 text-xs">{error}</p>}
              <button onClick={handleStep1} disabled={isLoading}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2 text-sm">
                {isLoading ? <Loader2 size={14} className="animate-spin" /> : null} Continue
              </button>
            </>
          )}

          {step === 2 && (
            <>
              <p className="text-sm text-white/60">
                {mode === "new_project"
                  ? "Upload your project spec (PDF, DOCX, TXT)."
                  : "Upload source code files (.py, .js, .ts, .java, etc.)"}
              </p>
              <div onClick={() => fileRef.current?.click()}
                className="border-2 border-dashed border-white/15 rounded-xl p-8 text-center cursor-pointer hover:border-indigo-500/60 transition">
                <Upload size={28} className="mx-auto mb-2 text-white/30" />
                <p className="text-sm text-white/50">
                  {files.length === 0 ? "Click to select files" : `${files.length} file(s) selected`}
                </p>
                {files.length > 0 && (
                  <ul className="mt-2 space-y-0.5">
                    {files.map((f, i) => <li key={i} className="text-xs text-indigo-300">{f.name}</li>)}
                  </ul>
                )}
              </div>
              <input ref={fileRef} type="file" multiple className="hidden" onChange={e => { if (e.target.files) setFiles(Array.from(e.target.files)); }}
                accept={mode === "new_project" ? ".pdf,.docx,.doc,.txt" : ".py,.js,.ts,.jsx,.tsx,.java,.go,.rs,.cpp,.c,.cs,.rb,.php,.kt,.swift"} />
              {error && <p className="text-red-400 text-xs">{error}</p>}
              <div className="flex gap-3">
                <button onClick={() => setStep(1)} className="flex items-center gap-1 px-4 py-2.5 border border-white/10 text-white/50 hover:text-white rounded-lg text-sm transition">
                  <ChevronLeft size={14} /> Back
                </button>
                <button onClick={handleStep2} disabled={isLoading || files.length === 0}
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2 text-sm">
                  {isLoading ? <Loader2 size={14} className="animate-spin" /> : null} Generate Course
                </button>
              </div>
            </>
          )}

          {step === 3 && (
            <div className="space-y-5 text-center py-4">
              {genStatus === "complete" ? (
                <>
                  <CheckCircle2 size={48} className="mx-auto text-green-400" />
                  <div>
                    <p className="text-white font-semibold">Course Generated!</p>
                    <p className="text-xs text-white/40 mt-1">{genDetail}</p>
                  </div>
                  <button onClick={onClose}
                    className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg transition text-sm">Done</button>
                </>
              ) : genStatus === "failed" ? (
                <>
                  <X size={48} className="mx-auto text-red-400" />
                  <div>
                    <p className="text-white font-semibold">Generation Failed</p>
                    <p className="text-xs text-red-400 mt-1">{genDetail}</p>
                  </div>
                  <button onClick={onClose} className="px-6 py-2.5 border border-white/10 text-white/60 hover:text-white rounded-lg transition text-sm">Close</button>
                </>
              ) : (
                <>
                  <Loader2 size={48} className="mx-auto text-indigo-400 animate-spin" />
                  <p className="text-white font-semibold">{genStatus === "queued" ? "Pipeline queued…" : "AI generating course…"}</p>
                  <p className="text-xs text-white/40">{genDetail || "~30–60 seconds"}</p>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
