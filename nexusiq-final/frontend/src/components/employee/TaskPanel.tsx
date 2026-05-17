"use client";
import { useRef, useState } from "react";
import { Upload, Loader2, CheckCircle, XCircle } from "lucide-react";

interface Task {
  task_title: string;
  description: string;
  requirements: string[];
  evaluation_criteria: string[];
  hints?: string[];
}

interface TaskResult {
  score: number;
  feedback: string;
  passed: boolean;
}

interface Props {
  task: Task;
  onSubmit: (file: File) => Promise<void>;
  result: TaskResult | null;
  isLoading: boolean;
  onProceedToInterview: () => void;
}

export default function TaskPanel({ task, onSubmit, result, isLoading, onProceedToInterview }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) setSelectedFile(e.target.files[0]);
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto p-6 space-y-6 max-w-3xl mx-auto w-full">
      <div>
        <h2 className="text-xl font-bold text-white">{task.task_title}</h2>
        <p className="text-sm text-white/60 mt-1">{task.description}</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white/5 border border-white/8 rounded-xl p-4 space-y-2">
          <h3 className="text-xs text-white/40 uppercase tracking-widest">Requirements</h3>
          <ul className="space-y-1.5">
            {task.requirements.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-white/80">
                <span className="text-indigo-400 mt-0.5 shrink-0">•</span> {r}
              </li>
            ))}
          </ul>
        </div>
        <div className="bg-white/5 border border-white/8 rounded-xl p-4 space-y-2">
          <h3 className="text-xs text-white/40 uppercase tracking-widest">Evaluation Criteria</h3>
          <ul className="space-y-1.5">
            {task.evaluation_criteria.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-white/80">
                <span className="text-green-400 mt-0.5 shrink-0">✓</span> {c}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {task.hints && task.hints.length > 0 && (
        <div className="bg-yellow-900/10 border border-yellow-500/20 rounded-xl p-4 space-y-1">
          <h3 className="text-xs text-yellow-400 uppercase tracking-widest">Hints</h3>
          {task.hints.map((h, i) => (
            <p key={i} className="text-xs text-yellow-300/70">💡 {h}</p>
          ))}
        </div>
      )}

      {!result ? (
        <div className="space-y-3">
          <div onClick={() => fileRef.current?.click()}
            className="border-2 border-dashed border-white/15 rounded-xl p-8 text-center cursor-pointer hover:border-indigo-500/50 transition">
            <Upload size={24} className="mx-auto mb-2 text-white/30" />
            <p className="text-sm text-white/50">
              {selectedFile ? selectedFile.name : "Click to upload your solution"}
            </p>
          </div>
          <input ref={fileRef} type="file" className="hidden" onChange={handleFileChange} />
          <button
            disabled={!selectedFile || isLoading}
            onClick={() => selectedFile && onSubmit(selectedFile)}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold rounded-xl transition flex items-center justify-center gap-2">
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : null}
            Submit for Review
          </button>
        </div>
      ) : (
        <div className={`rounded-xl p-5 space-y-3 border ${result.passed ? "bg-green-900/15 border-green-500/30" : "bg-red-900/15 border-red-500/30"}`}>
          <div className="flex items-center gap-3">
            {result.passed
              ? <CheckCircle size={20} className="text-green-400" />
              : <XCircle    size={20} className="text-red-400" />}
            <div>
              <p className={`font-semibold ${result.passed ? "text-green-400" : "text-red-400"}`}>
                {result.passed ? "Task Passed!" : "Not Passed"} — Score: {result.score}/100
              </p>
            </div>
          </div>
          <p className="text-sm text-white/70">{result.feedback}</p>
          {result.passed && (
            <button onClick={onProceedToInterview}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg transition text-sm">
              Proceed to Interview →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
