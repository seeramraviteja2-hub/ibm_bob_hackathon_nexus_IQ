"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Send, Loader2, ChevronRight, Cpu, Bot, Zap } from "lucide-react";
import api from "@/lib/api";

interface Message { role: "user" | "assistant"; content: string; }

interface Props {
  courseId: string;
  moduleTitle: string;
  concepts: string[];
  initialHistory: Message[];
  onComplete: () => void;
}

function AgentStatusPanel({ isLoading, providerHint }: { isLoading: boolean; providerHint: string }) {
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!isLoading) return;
    const id = setInterval(() => setTick(t => t + 1), 600);
    return () => clearInterval(id);
  }, [isLoading]);

  const dots = ".".repeat((tick % 3) + 1);
  const isIBM = providerHint === "IBM Bob";

  return (
    <div className="shrink-0 mx-6 mb-2 flex items-center gap-2 px-3 py-2 bg-white/4 border border-white/8 rounded-lg">
      <div className={`w-1.5 h-1.5 rounded-full ${isLoading ? "bg-indigo-400 animate-pulse" : "bg-white/20"}`} />
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest">
        {isIBM
          ? <Cpu size={10} className={isLoading ? "text-indigo-400" : "text-white/20"} />
          : <Zap size={10} className={isLoading ? "text-amber-400" : "text-white/20"} />}
        <span className={isLoading ? "text-indigo-300" : "text-white/30"}>
          {isLoading ? `${providerHint} responding${dots}` : `${providerHint} — ready`}
        </span>
      </div>
      <div className="ml-auto flex items-center gap-1 text-[10px] text-white/25">
        <Bot size={10} />
        <span>Teaching Agent</span>
      </div>
    </div>
  );
}

export default function TeachingChat({ courseId, moduleTitle, concepts, initialHistory, onComplete }: Props) {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>(initialHistory);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [providerHint, setProviderHint] = useState("IBM Bob");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (messages.length === 0) {
      const greeting: Message = {
        role: "assistant",
        content: `Hi! I'm your AI tutor for **${moduleTitle}**. We'll cover: ${concepts.slice(0, 3).join(", ")}${concepts.length > 3 ? ` and ${concepts.length - 3} more concepts` : ""}.\n\nFeel free to ask questions or type "start" to begin!`,
      };
      setMessages([greeting]);
    }
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
  }, [input]);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setMessages(prev => [...prev, { role: "user", content: trimmed }]);
    setIsLoading(true);
    try {
      const res = await api.post(`/api/v1/employee/courses/${courseId}/teach`, { message: trimmed });
      const reply = res.data.response || "";
      // Check if backend tells us which provider ran
      if (res.data.provider) setProviderHint(res.data.provider);
      setMessages(prev => [...prev, { role: "assistant", content: reply }]);
      if (res.data.teaching_complete) {
        setIsComplete(true);
        onComplete();
      }
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, I hit an error. Please try again." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      sendMessage();
    }
    // plain Enter = new line
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm whitespace-pre-wrap break-words ${
              m.role === "user"
                ? "bg-indigo-600 text-white rounded-br-sm font-mono"
                : "bg-white/8 text-white/90 rounded-bl-sm"
            }`}>
              {m.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white/8 px-4 py-3 rounded-2xl rounded-bl-sm">
              <Loader2 size={14} className="animate-spin text-white/40" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Complete banner */}
      {isComplete && (
        <div className="mx-6 mb-3 p-4 bg-green-900/20 border border-green-500/30 rounded-xl flex items-center justify-between shrink-0">
          <span className="text-green-400 text-sm font-medium">Teaching complete! Ready for evaluation.</span>
          <button
            onClick={() => router.push(`/employee/courses/${courseId}/evaluate`)}
            className="flex items-center gap-1 text-xs text-green-300 hover:text-white bg-green-600/20 hover:bg-green-600/40 px-3 py-1.5 rounded-lg transition">
            Go to Evaluation <ChevronRight size={12} />
          </button>
        </div>
      )}

      {/* Agent status */}
      <AgentStatusPanel isLoading={isLoading} providerHint={providerHint} />

      {/* Input — textarea: Enter = newline, Ctrl+Enter or button = send */}
      {!isComplete && (
        <div className="px-6 pb-6 pt-1 shrink-0">
          <div className="flex gap-3 bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus-within:border-indigo-500/50 transition items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question or say 'start'… (Enter for new line, Ctrl+Enter or ➤ to send)"
              rows={1}
              disabled={isLoading}
              className="flex-1 bg-transparent text-white text-sm outline-none placeholder-white/30 resize-none leading-relaxed overflow-hidden"
              style={{ minHeight: "24px", maxHeight: "160px" }}
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              title="Send (Ctrl+Enter)"
              className="p-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 disabled:bg-white/5 text-white rounded-lg transition shrink-0"
            >
              <Send size={14} />
            </button>
          </div>
          <p className="text-[10px] text-white/20 mt-1.5 text-right">Enter = new line · Ctrl+Enter or ➤ to send</p>
        </div>
      )}
    </div>
  );
}
