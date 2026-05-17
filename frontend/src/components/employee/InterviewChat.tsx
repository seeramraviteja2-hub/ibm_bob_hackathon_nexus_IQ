"use client";
import { useState, useEffect, useRef } from "react";
import { Send, Loader2, Bot, Cpu, Zap } from "lucide-react";

interface Turn { question: string; answer: string; }

interface Props {
  currentQuestion: string;
  turns: Turn[];
  questionCount: number;
  isLoading: boolean;
  isComplete: boolean;
  onAnswer: (answer: string) => void;
  agentStatus?: { provider: string; status: string } | null;
}

function AgentStatusPanel({ isLoading, agentStatus }: { isLoading: boolean; agentStatus?: { provider: string; status: string } | null }) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!isLoading) return;
    const id = setInterval(() => setTick(t => t + 1), 600);
    return () => clearInterval(id);
  }, [isLoading]);

  const provider = agentStatus?.provider || "IBM Bob";
  const dots = ".".repeat((tick % 3) + 1);

  return (
    <div className="shrink-0 mx-6 mb-3 flex items-center gap-2 px-3 py-2 bg-white/4 border border-white/8 rounded-lg">
      <div className={`w-1.5 h-1.5 rounded-full ${isLoading ? "bg-indigo-400 animate-pulse" : "bg-white/20"}`} />
      <div className="flex items-center gap-1.5 text-[10px] text-white/40 uppercase tracking-widest">
        {provider === "IBM Bob" ? <Cpu size={10} className={isLoading ? "text-indigo-400" : "text-white/20"} /> : <Zap size={10} className={isLoading ? "text-amber-400" : "text-white/20"} />}
        <span className={isLoading ? "text-indigo-300" : "text-white/30"}>
          {isLoading ? `${provider} thinking${dots}` : `${provider} — ready`}
        </span>
      </div>
      <div className="ml-auto flex items-center gap-1 text-[10px] text-white/25">
        <Bot size={10} />
        <span>Interview Agent</span>
      </div>
    </div>
  );
}

export default function InterviewChat({ currentQuestion, turns, questionCount, isLoading, isComplete, onAnswer, agentStatus }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, currentQuestion]);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  }, [input]);

  const submit = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading || isComplete) return;
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    onAnswer(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      submit();
    }
    // plain Enter = new line (default textarea behaviour, no preventDefault)
  };

  const totalQ = 6;

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto w-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/8 flex items-center justify-between shrink-0">
        <div>
          <p className="text-white font-semibold text-sm">Technical Interview</p>
          <p className="text-xs text-white/40">Question {questionCount} of {totalQ} · Ctrl+Enter or ➤ to send</p>
        </div>
        <div className="flex gap-1">
          {Array.from({ length: totalQ }).map((_, i) => (
            <div key={i} className={`w-2 h-2 rounded-full transition-colors ${i < turns.length ? "bg-indigo-500" : "bg-white/10"}`} />
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {turns.map((t, i) => (
          <div key={i} className="space-y-2">
            <div className="flex justify-start">
              <div className="max-w-[80%] bg-white/8 px-4 py-3 rounded-2xl rounded-bl-sm text-sm text-white/90 whitespace-pre-wrap break-words">
                {t.question}
              </div>
            </div>
            <div className="flex justify-end">
              <div className="max-w-[80%] bg-indigo-600 px-4 py-3 rounded-2xl rounded-br-sm text-sm text-white whitespace-pre-wrap break-words font-mono">
                {t.answer}
              </div>
            </div>
          </div>
        ))}
        {currentQuestion && !isComplete && (
          <div className="flex justify-start">
            <div className="max-w-[80%] bg-white/8 px-4 py-3 rounded-2xl rounded-bl-sm text-sm text-white/90 whitespace-pre-wrap">
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

      {/* Agent status bar */}
      <AgentStatusPanel isLoading={isLoading} agentStatus={agentStatus} />

      {/* Input — textarea: Enter = newline, Ctrl+Enter = send, Send button = send */}
      {!isComplete && (
        <div className="px-6 pb-6 pt-1 shrink-0">
          <div className="flex gap-3 bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus-within:border-indigo-500/50 transition items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your answer… (Enter for new line, Ctrl+Enter or ➤ to send)"
              disabled={isLoading || isComplete}
              rows={1}
              className="flex-1 bg-transparent text-white text-sm outline-none placeholder-white/30 disabled:opacity-40 resize-none leading-relaxed overflow-hidden font-mono"
              style={{ minHeight: "24px", maxHeight: "160px" }}
            />
            <button
              onClick={submit}
              disabled={isLoading || !input.trim() || isComplete}
              title="Send (Ctrl+Enter)"
              className="p-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 disabled:bg-white/5 text-white rounded-lg transition shrink-0"
            >
              <Send size={14} />
            </button>
          </div>
          <p className="text-[10px] text-white/20 mt-1.5 text-right">Enter = new line · Ctrl+Enter or ➤ to send</p>
        </div>
      )}

      {isComplete && (
        <div className="px-6 pb-6 shrink-0">
          <div className="p-3 bg-green-900/20 border border-green-500/30 rounded-xl text-center">
            <p className="text-green-400 text-sm font-medium">Interview complete — calculating your results…</p>
          </div>
        </div>
      )}
    </div>
  );
}
