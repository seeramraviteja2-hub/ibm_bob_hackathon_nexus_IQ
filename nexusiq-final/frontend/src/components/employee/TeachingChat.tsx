"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Send, Loader2, ChevronRight } from "lucide-react";
import api from "@/lib/api";

interface Message { role: "user" | "assistant"; content: string; }

interface Props {
  courseId: string;
  moduleTitle: string;
  concepts: string[];
  initialHistory: Message[];
  onComplete: () => void;
}

export default function TeachingChat({ courseId, moduleTitle, concepts, initialHistory, onComplete }: Props) {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>(initialHistory);
  const [input, setInput]       = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Initial AI greeting
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

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", content: trimmed }]);
    setIsLoading(true);
    try {
      const res = await api.post(`/api/v1/employee/courses/${courseId}/teach`, { message: trimmed });
      const reply = res.data.response || "";
      setMessages(prev => [...prev, { role: "assistant", content: reply }]);
      if (res.data.teaching_complete) {
        setIsComplete(true);
        onComplete();
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, I hit an error. Please try again." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm ${
              m.role === "user"
                ? "bg-indigo-600 text-white rounded-br-sm"
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
        <div className="mx-6 mb-4 p-4 bg-green-900/20 border border-green-500/30 rounded-xl flex items-center justify-between">
          <span className="text-green-400 text-sm font-medium">Teaching complete! Ready for evaluation.</span>
          <button
            onClick={() => router.push(`/employee/courses/${courseId}/evaluate`)}
            className="flex items-center gap-1 text-xs text-green-300 hover:text-white bg-green-600/20 hover:bg-green-600/40 px-3 py-1.5 rounded-lg transition">
            Go to Evaluation <ChevronRight size={12} />
          </button>
        </div>
      )}

      {/* Input */}
      {!isComplete && (
        <div className="px-6 pb-6 pt-2">
          <div className="flex gap-3 bg-white/5 border border-white/10 rounded-xl px-4 py-3 focus-within:border-indigo-500/50 transition">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              placeholder="Ask a question or say 'start'…"
              className="flex-1 bg-transparent text-white text-sm outline-none placeholder-white/30"
            />
            <button onClick={sendMessage} disabled={isLoading || !input.trim()}
              className="p-1 text-indigo-400 hover:text-indigo-300 disabled:opacity-30 transition">
              <Send size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
