import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useRef, useCallback } from "react";
import {
  Radio,
  Zap,
  Activity,
  Droplets,
  Wind,
  ShieldAlert,
  Bot,
  RefreshCw,
  AlertTriangle,
  Send,
  Gauge,
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceLine,
} from "recharts";
import {
  getNodes,
  getEvents,
  ackEvent,
  getEnergy,
  getAnomalyScores,
  queryAssistant,
  eventsWsUrl,
  type NodeStatus,
  type EventPayload,
  type EnergyPoint,
  type AnomalyScore,
} from "@/lib/api";

export const Route = createFileRoute("/console")({
  component: ConsoleDashboard,
});

const DEFAULT_APPLIANCES = ["refrigerator", "hvac", "microwave", "other"];
const APPLIANCE_COLORS: Record<string, string> = {
  refrigerator: "#818cf8",
  hvac: "#38bdf8",
  microwave: "#e11d48",
  other: "#9ca3af",
};

const fmtTime = (tsSeconds: number) =>
  new Date(tsSeconds * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const titleCase = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
const applianceColor = (a: string) => APPLIANCE_COLORS[a] ?? "#9ca3af";

function ConsoleDashboard() {
  const [nodes, setNodes] = useState<NodeStatus[]>([]);
  const [events, setEvents] = useState<EventPayload[]>([]);
  const [energy, setEnergy] = useState<EnergyPoint[]>([]);
  const [appliances, setAppliances] = useState<string[]>(DEFAULT_APPLIANCES);
  const [anomalies, setAnomalies] = useState<AnomalyScore[]>([]);
  const [online, setOnline] = useState(false);

  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<Array<{ sender: "user" | "bot"; text: string }>>([
    { sender: "bot", text: "Hello! I am your on-device AuraSense assistant. Ask me about energy usage, anomalies, or node status." },
  ]);
  const [isLlmLoading, setIsLlmLoading] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Poll the hub for live data (the client handles pairing/token itself).
  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      const [n, e, en, an] = await Promise.allSettled([
        getNodes(),
        getEvents(),
        getEnergy(60),
        getAnomalyScores(60),
      ]);
      if (cancelled) return;
      const anyOk = [n, e, en, an].some((r) => r.status === "fulfilled");
      setOnline(anyOk);
      if (n.status === "fulfilled") setNodes(n.value);
      if (e.status === "fulfilled") setEvents(e.value);
      if (en.status === "fulfilled") {
        setEnergy(en.value.points);
        if (en.value.appliances.length) setAppliances(en.value.appliances);
      }
      if (an.status === "fulfilled") setAnomalies(an.value);
    };
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Live event stream over WebSocket.
  useEffect(() => {
    let closedByUs = false;
    const connect = () => {
      try {
        const ws = new WebSocket(eventsWsUrl());
        wsRef.current = ws;
        ws.onopen = () => setIsLive(true);
        ws.onmessage = (ev) => {
          if (ev.data === "pong") return;
          try {
            const frame = JSON.parse(ev.data);
            if (frame.type === "event_notification") {
              setEvents((prev) => [frame.data as EventPayload, ...prev]);
            }
          } catch {
            /* ignore malformed frame */
          }
        };
        ws.onclose = () => {
          setIsLive(false);
          if (!closedByUs) setTimeout(connect, 5000);
        };
      } catch {
        setIsLive(false);
      }
    };
    connect();
    return () => {
      closedByUs = true;
      wsRef.current?.close();
    };
  }, []);

  const acknowledge = useCallback(async (eventId: string) => {
    setEvents((prev) => prev.map((e) => (e.event_id === eventId ? { ...e, acknowledged: true } : e)));
    try {
      await ackEvent(eventId);
    } catch {
      /* optimistic update already applied */
    }
  }, []);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = chatInput.trim();
    if (!text) return;
    setChatMessages((prev) => [...prev, { sender: "user", text }]);
    setChatInput("");
    setIsLlmLoading(true);
    try {
      const reply = await queryAssistant(text);
      setChatMessages((prev) => [...prev, { sender: "bot", text: reply }]);
    } catch {
      setChatMessages((prev) => [
        ...prev,
        { sender: "bot", text: "The hub is unreachable right now. Check that the API is running and try again." },
      ]);
    } finally {
      setIsLlmLoading(false);
    }
  };

  // Derived chart data.
  const nilmData = energy.slice(-40).map((p) => {
    const row: Record<string, number | string> = { time: fmtTime(p.ts) };
    for (const a of appliances) row[titleCase(a)] = Number(p[a] ?? 0);
    return row;
  });
  const anomalyData = anomalies.slice(-40).map((s) => ({ time: fmtTime(s.ts), score: Number(s.score.toFixed(3)) }));
  const latestAnomaly = anomalies.length ? anomalies[anomalies.length - 1].score : 0;

  return (
    <div className="mx-auto max-w-7xl px-6 py-10">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isLive ? "bg-emerald-400" : "bg-amber-400"}`}></span>
              <span className={`relative inline-flex rounded-full h-3 w-3 ${isLive ? "bg-emerald-500" : "bg-amber-500"}`}></span>
            </span>
            <span className="text-xs uppercase tracking-wider text-muted-foreground font-semibold">
              {isLive ? "Live Stream Connected" : online ? "Connected (polling)" : "Hub Offline"}
            </span>
          </div>
          <h1 className="mt-1 font-display text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            AuraSense Console
          </h1>
        </div>
        <div className="rounded-lg border border-border bg-card/50 px-4 py-2 text-sm font-medium text-muted-foreground">
          Hub Host: <span className="font-semibold text-foreground">Raspberry Pi 5</span>
        </div>
      </div>

      {/* Main Grid */}
      <div className="mt-8 grid gap-8 lg:grid-cols-3">
        {/* Left Column */}
        <div className="space-y-8 lg:col-span-2">
          {/* Nodes Registry */}
          <div className="rounded-2xl border border-border bg-card p-6">
            <h2 className="font-display text-xl font-bold text-foreground mb-4">Sensor Node Fleet</h2>
            {nodes.length === 0 ? (
              <p className="text-sm text-muted-foreground">No nodes reporting yet. Start the device simulator to populate the fleet.</p>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                {nodes.map((node) => {
                  let Icon = Radio;
                  if (node.type === "power") Icon = Zap;
                  if (node.type === "motion") Icon = Activity;
                  if (node.type === "audio") Icon = Droplets;
                  if (node.type === "env") Icon = Wind;
                  return (
                    <div key={node.node_id} className="flex items-center justify-between rounded-xl border border-border/50 bg-secondary/20 p-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                          <Icon className="h-5 w-5" />
                        </div>
                        <div>
                          <h4 className="text-sm font-semibold text-foreground">{node.node_id}</h4>
                          <p className="text-xs text-muted-foreground uppercase">{node.type} node</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${node.status === "ONLINE" ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"}`}>
                          {node.status}
                        </span>
                        <p className="mt-1 text-[10px] text-muted-foreground">v{node.firmware_version}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* NILM chart */}
          <div className="rounded-2xl border border-border bg-card p-6">
            <h2 className="font-display text-xl font-bold text-foreground mb-1">Energy Disaggregation (NILM)</h2>
            <p className="text-xs text-muted-foreground mb-6">Per-appliance load, analyzed locally from the mains clamp — served live from the hub.</p>
            <div className="h-72 w-full">
              {nilmData.length === 0 ? (
                <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                  Waiting for energy data… run the simulator's power node.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={nilmData}>
                    <XAxis dataKey="time" stroke="#6b7280" fontSize={11} minTickGap={24} />
                    <YAxis stroke="#6b7280" fontSize={11} unit="W" />
                    <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: "8px", color: "#fff" }} />
                    <Legend verticalAlign="top" height={36} />
                    {appliances.map((a) => (
                      <Area
                        key={a}
                        type="monotone"
                        dataKey={titleCase(a)}
                        stackId="1"
                        stroke={applianceColor(a)}
                        fill={applianceColor(a)}
                        fillOpacity={0.3}
                      />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>

          {/* Behavioral anomaly chart */}
          <div className="rounded-2xl border border-border bg-card p-6">
            <div className="flex items-center justify-between mb-1">
              <h2 className="font-display text-xl font-bold text-foreground flex items-center gap-2">
                <Gauge className="h-5 w-5 text-primary" />
                Behavioral Anomaly Score
              </h2>
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${latestAnomaly > 0.8 ? "bg-rose-500/10 text-rose-500" : latestAnomaly > 0.5 ? "bg-amber-500/10 text-amber-500" : "bg-emerald-500/10 text-emerald-500"}`}>
                current {latestAnomaly.toFixed(2)}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mb-6">On-device model score (0–1); the dashed line marks the alert threshold.</p>
            <div className="h-52 w-full">
              {anomalyData.length === 0 ? (
                <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                  Waiting for anomaly scores… the inference engine emits these each cycle.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={anomalyData}>
                    <defs>
                      <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="time" stroke="#6b7280" fontSize={11} minTickGap={24} />
                    <YAxis stroke="#6b7280" fontSize={11} domain={[0, 1]} />
                    <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: "8px", color: "#fff" }} />
                    <ReferenceLine y={0.8} stroke="#e11d48" strokeDasharray="4 4" />
                    <Area type="monotone" dataKey="score" stroke="#f59e0b" fill="url(#colorScore)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-8">
          {/* Alerts */}
          <div className="rounded-2xl border border-border bg-card p-6 flex flex-col h-[400px]">
            <h2 className="font-display text-xl font-bold text-foreground mb-4 flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-rose-500 animate-pulse" />
              Recent Alert Logs
            </h2>
            <div className="flex-1 overflow-y-auto space-y-3 pr-2">
              {events.length === 0 ? (
                <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                  No alerts recorded. Everything is peaceful.
                </div>
              ) : (
                events.map((evt) => (
                  <div key={evt.event_id} className={`rounded-xl border p-4 transition-all ${evt.acknowledged ? "border-border bg-secondary/10 opacity-60" : "border-rose-500/30 bg-rose-500/5"}`}>
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        {evt.severity === "CRITICAL" ? (
                          <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0" />
                        ) : (
                          <ShieldAlert className="h-4 w-4 text-amber-500 shrink-0" />
                        )}
                        <h4 className="text-sm font-semibold text-foreground uppercase tracking-tight">{evt.type}</h4>
                      </div>
                      {!evt.acknowledged && (
                        <button
                          onClick={() => acknowledge(evt.event_id)}
                          className="rounded bg-primary/10 hover:bg-primary/20 px-2 py-0.5 text-xs text-primary transition-colors font-medium"
                        >
                          Ack
                        </button>
                      )}
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                      {evt.type === "microwave_running" ? "High continuous active load detected." : JSON.stringify(evt.payload)}
                    </p>
                    <p className="mt-2 text-[10px] text-muted-foreground/60">{fmtTime(evt.ts)}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Assistant */}
          <div className="rounded-2xl border border-border bg-card p-6 flex flex-col h-[400px]">
            <h2 className="font-display text-xl font-bold text-foreground mb-1 flex items-center gap-2">
              <Bot className="h-5 w-5 text-primary" />
              On-Device Assistant
            </h2>
            <p className="text-xs text-muted-foreground mb-4">Query your hub locally without sharing home metrics with third parties</p>
            <div className="flex-1 overflow-y-auto space-y-3 mb-4 pr-2">
              {chatMessages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] rounded-xl px-4 py-2.5 text-xs leading-relaxed ${msg.sender === "user" ? "bg-primary text-primary-foreground" : "bg-secondary/40 text-foreground"}`}>
                    {msg.text}
                  </div>
                </div>
              ))}
              {isLlmLoading && (
                <div className="flex justify-start">
                  <div className="flex items-center gap-2 rounded-xl bg-secondary/40 px-4 py-2.5 text-xs text-muted-foreground">
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    Thinking…
                  </div>
                </div>
              )}
            </div>
            <form onSubmit={handleSendMessage} className="flex gap-2">
              <input
                type="text"
                placeholder="Ask about electricity, falls, or node alerts…"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                className="flex-1 rounded-lg border border-border bg-secondary/20 px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <button
                type="submit"
                disabled={isLlmLoading}
                className="rounded-lg bg-primary hover:bg-primary/90 text-primary-foreground p-2 shrink-0 transition-colors"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
