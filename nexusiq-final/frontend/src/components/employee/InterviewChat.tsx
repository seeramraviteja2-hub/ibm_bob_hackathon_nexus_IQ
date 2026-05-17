"use client";
import { useState, useEffect, useRef } from "react";
import { Send, Loader2 } from "lucide-react";

interface Turn { question: string; answer: string; }

interface Props {
  currentQuestion: string;
  turns: Turn[];
  questionCount: number;
  isLoading: boolean;
  isComplete: boolean;
  onAnswer: (answer: string) => void;
}

export default function InterviewChat({ currentQuestion, turns, questionCount, isLoading, isComplete, onAnswer }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, currentQuestion]);

  const submit = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading || isComplete) return;
    setInput("");
    onAnswer(trimmed);
  };

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto w-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/8 flex items-center justify-between">
        <div>
          <p className="text-white font-semibold text-sm">Technical Interview</p>
          <p className="text-xs text-white/40">Question {questionCount} of 9</p>
        </div>
        <div className="flex gap-1">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className={`w-2 h-2 rounded-full ${i < turns.length ? "bg-indigo-500" : "bg-white/10"}`} />
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {turns.map((t, i) => (
          <div key={i} className="space-y-2">
            <div className="flex justify-start">
              <div className="max-w-[80%] bg-white/8 px-4 py-3 rounded-2xl rounded-bl-sm text-sm text-white/90">
                {t.question}
              </div>
            </div>
            <div className="flex justify-end">
              <div className="max-w-[80%] bg-indigo-600 px-4 py-3 rounded-2xl rounded-br-sm text-sm text-white">
                {t.answer}
              </div>
            </div>
          </div>
        ))}
        {currentQuestion && !isComplete && (
          <div className="flex justify-start">
            <div className="max-w-[80%] bg-white/8 px-4 py-3 rounded-2xl rounded-bl-sm text-sm text-white/90">
              {currentQuestion}
            </div>
          </div>
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white/8 px-4 py-3 rounded-2xl rounded-bl-sm">
              <Loader2 size={14} className="animate-spin text-white/40" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      {!isComplete && (
        <div className="px-6 pb-6 pt-2">
          <div className="flex gap-3 bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus-within:border-indigo-500/50 transition">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
              placeholder="Type your answer…"
              disabled={isLoading || isComplete}
              className="flex-1 bg-transparent text-white text-sm outline-none placeholder-white/30 disabled:opacity-40"
            />
            <button onClick={submit} disabled={isLoading || !input.trim() || isComplete}
              className="p-1 text-indigo-400 hover:text-indigo-300 disabled:opacity-30 transition">
              <Send size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
