"use client";

/**
 * Session Logs Page — Manager view of a live/past agent session.
 *
 * FIXES vs previous (crashed):
 * 1. Fetches GET /manager/sessions/{id} for metadata (endpoint was missing)
 * 2. Connects to /ws/logs/{session_id} — NOT /ws/status/{id} (wrong URL before)
 * 3. WebSocket messages are JSON log entries — NOT data.agents arrays
 *    (frontend was trying to read data.agents → always undefined)
 * 4. LogViewer no longer regex-parses the raw string — receives structured JSON
 *    so agent_name, level, message render correctly
 * 5. Historical logs loaded via GET /manager/sessions/{id}/logs (lrange from Redis)
 */

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Loader2, Radio, CheckCircle, XCircle, Info } from "lucide-react";
import api from "@/lib/api";

interface LogEntry {
  session_id: string;
  agent_name: string;
  level: string;
  message: string;
  metadata?: Record<string, any>;
  timestamp: string;
  // fallback for malformed entries
  raw?: string;
}

interface SessionMeta {
  session_id: string;
  employee_name: string;
  course_title: string;
  status: string;
  current_module_index: number;
  ws_url: string;
}

export default function SessionLogsPage() {
  const params = useParams();
  const sessionId = params.sessionId as string;

  const [meta, setMeta] = useState<SessionMeta | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [wsStatus, setWsStatus] = useState<"connecting" | "open" | "closed">("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // 1. Load session metadata + historical logs from REST
  useEffect(() => {
    const load = async () => {
      try {
        const [metaRes, logsRes] = await Promise.all([
          api.get(`/api/v1/manager/sessions/${sessionId}`),
          api.get(`/api/v1/manager/sessions/${sessionId}/logs`),
        ]);
        setMeta(metaRes.data);
        const historical: LogEntry[] = logsRes.data.logs ?? [];
        setLogs(historical);
      } catch (err) {
        console.error("Session load failed:", err);
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [sessionId]);

  // 2. Connect to WebSocket for live updates
  // FIX: correct path is /ws/logs/{session_id}, NOT /ws/status/{id}
  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const host = process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:\/\//, "") ?? window.location.host;
    const wsUrl = `${protocol}://${host}/ws/logs/${sessionId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setWsStatus("open");
    ws.onclose = () => setWsStatus("closed");

    ws.onmessage = (event) => {
      try {
        const entry: LogEntry = JSON.parse(event.data);
        // Skip heartbeat messages
        if ((entry as any).type === "heartbeat") return;
        setLogs(prev => [...prev, entry]);
      } catch {
        // Malformed message — show as raw
        setLogs(prev => [...prev, {
          session_id: sessionId,
          agent_name: "SYSTEM",
          level: "INFO",
          message: event.data,
          timestamp: new Date().toISOString(),
        }]);
      }
    };

    return () => { ws.close(); };
  }, [sessionId]);

  // 3. Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const levelColor: Record<string, string> = {
    ERROR:   "text-red-400",
    WARNING: "text-yellow-400",
    INFO:    "text-blue-400",
    DEBUG:   "text-muted-foreground",
    SUCCESS: "text-green-400",
  };

  const LevelIcon = ({ level }: { level: string }) => {
    if (level === "ERROR") return <XCircle size={12} className="text-red-400 shrink-0" />;
    if (level === "SUCCESS") return <CheckCircle size={12} className="text-green-400 shrink-0" />;
    return <Info size={12} className="text-blue-400 shrink-0" />;
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center h-screen">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-[#0a0a0f] text-white">
      {/* Header */}
      <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-base font-bold">{meta?.employee_name ?? sessionId}</h1>
          <p className="text-xs text-muted-foreground">{meta?.course_title} · Module {(meta?.current_module_index ?? 0) + 1}</p>
        </div>
        <div className="flex items-center gap-2">
          <Radio size={12} className={wsStatus === "open" ? "text-green-400 animate-pulse" : "text-muted-foreground"} />
          <span className="text-xs text-muted-foreground capitalize">{wsStatus}</span>
        </div>
      </div>

      {/* Log feed */}
      <div className="flex-1 overflow-y-auto font-mono text-xs p-4 space-y-1">
        {logs.length === 0 && (
          <p className="text-muted-foreground text-center mt-10">No logs yet. Waiting for agent activity…</p>
        )}
        {logs.map((log, i) => (
          <div key={i} className="flex items-start gap-3 py-0.5 hover:bg-white/5 px-2 rounded">
            <LevelIcon level={log.level?.toUpperCase()} />
            <span className="text-muted-foreground shrink-0 w-20 truncate">{log.agent_name}</span>
            <span className={`shrink-0 w-14 uppercase ${levelColor[log.level?.toUpperCase()] ?? "text-muted-foreground"}`}>
              {log.level}
            </span>
            <span className="text-white/80 flex-1 break-words">{log.message}</span>
            <span className="text-muted-foreground shrink-0 tabular-nums">
              {new Date(log.timestamp).toLocaleTimeString()}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
