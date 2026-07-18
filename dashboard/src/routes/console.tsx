import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import {
  Radio,
  Zap,
  Activity,
  Droplets,
  Wind,
  ShieldAlert,
  Bot,
  RefreshCw,
  CheckCircle,
  AlertTriangle,
  Play,
  Send
} from "lucide-react";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend
} from "recharts";

export const Route = createFileRoute("/console")({
  component: ConsoleDashboard,
});

// Mock Initial data for offline fallback
const initialNodes = [
  { node_id: "node_power_01", type: "power", status: "ONLINE", last_seen: "Just now", firmware_version: "1.0.0" },
  { node_id: "node_acoustic_02", type: "audio", status: "ONLINE", last_seen: "Just now", firmware_version: "1.0.0" },
  { node_id: "node_presence_03", type: "motion", status: "ONLINE", last_seen: "1 min ago", firmware_version: "1.0.0" },
  { node_id: "node_env_04", type: "env", status: "ONLINE", last_seen: "Just now", firmware_version: "1.0.0" }
];

const initialEvents = [
  { event_id: "1", ts: Math.floor(Date.now()/1000) - 30, type: "microwave_running", severity: "INFO", node_id: "node_power_01", payload: { refrigerator: 150.0, microwave: 1200.0, hvac: 0.0, other: 50.0 }, acknowledged: false },
  { event_id: "2", ts: Math.floor(Date.now()/1000) - 120, type: "behavioral_anomaly", severity: "WARNING", node_id: "node_presence_03", payload: { description: "Unusual night time motion detected in lounge" }, acknowledged: false }
];

const mockNilmData = [
  { time: "12:00", Refrigerator: 150, Microwave: 0, HVAC: 1200, Other: 110 },
  { time: "13:00", Refrigerator: 145, Microwave: 1200, HVAC: 1200, Other: 150 },
  { time: "14:00", Refrigerator: 152, Microwave: 0, HVAC: 1200, Other: 95 },
  { time: "15:00", Refrigerator: 148, Microwave: 0, HVAC: 0, Other: 120 },
  { time: "16:00", Refrigerator: 150, Microwave: 0, HVAC: 0, Other: 105 },
  { time: "17:00", Refrigerator: 155, Microwave: 1200, HVAC: 1800, Other: 220 }
];

function ConsoleDashboard() {
  const [nodes, setNodes] = useState(initialNodes);
  const [events, setEvents] = useState(initialEvents);
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<Array<{ sender: "user" | "bot"; text: string }>>([
    { sender: "bot", text: "Hello! I am your on-device AuraSense assistant. Ask me anything about recent energy usages, anomalies, or system sensor status." }
  ]);
  const [isLlmLoading, setIsLlmLoading] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Poll HTTP API or fallback to simulation updates
  useEffect(() => {
    const fetchData = async () => {
      try {
        const nodesRes = await fetch("http://localhost:8000/api/v1/nodes");
        if (nodesRes.ok) {
          const res = await nodesRes.json();
          setNodes(res.data);
        }
        
        const eventsRes = await fetch("http://localhost:8000/api/v1/events");
        if (eventsRes.ok) {
          const res = await eventsRes.json();
          setEvents(res.data);
        }
      } catch (err) {
        // Silent catch: using mock simulation when offline
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  // Connect WebSocket live notifications
  useEffect(() => {
    const connectWs = () => {
      try {
        const ws = new WebSocket("ws://localhost:8000/ws/v1/events");
        wsRef.current = ws;

        ws.onopen = () => {
          setIsLive(true);
        };

        ws.onmessage = (e) => {
          if (e.data === "pong") return;
          try {
            const eventPayload = JSON.parse(e.data);
            if (eventPayload.type === "event_notification") {
              setEvents((prev) => [eventPayload.data, ...prev]);
            }
          } catch (err) {
            console.error("Error parsing WS frame: ", err);
          }
        };

        ws.onclose = () => {
          setIsLive(false);
          // Try to reconnect in 5 seconds
          setTimeout(connectWs, 5000);
        };
      } catch (err) {
        setIsLive(false);
      }
    };

    connectWs();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const acknowledgeEvent = async (eventId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/events/${eventId}/ack`, {
        method: "POST"
      });
      if (res.ok) {
        setEvents((prev) =>
          prev.map((e) => (e.event_id === eventId ? { ...e, acknowledged: true } : e))
        );
      }
    } catch (err) {
      // Fallback local ack update if server is down
      setEvents((prev) =>
        prev.map((e) => (e.event_id === eventId ? { ...e, acknowledged: true } : e))
      );
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userText = chatInput;
    setChatMessages((prev) => [...prev, { sender: "user", text: userText }]);
    setChatInput("");
    setIsLlmLoading(true);

    try {
      const res = await fetch("http://localhost:8000/api/v1/assistant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: userText })
      });
      if (res.ok) {
        const body = await res.json();
        setChatMessages((prev) => [...prev, { sender: "bot", text: body.data.response }]);
      } else {
        throw new Error();
      }
    } catch (err) {
      // Offline fallback simulate
      setTimeout(() => {
        let fallbackReply = "Currently, the backend API is unreachable. Running in offline mock mode. All metrics appear normal.";
        if (userText.toLowerCase().includes("power") || userText.toLowerCase().includes("energy")) {
          fallbackReply = "Based on local sensor caches, average consumption is 280 Watts. The Refrigerator consumes 150W, HVAC is idle, and other loads draw 130W.";
        } else if (userText.toLowerCase().includes("status") || userText.toLowerCase().includes("offline")) {
          fallbackReply = "All four local nodes (Power, Acoustic, Presence, Environment) are responding and showing active status.";
        }
        setChatMessages((prev) => [...prev, { sender: "bot", text: fallbackReply }]);
      }, 800);
    } finally {
      setIsLlmLoading(false);
    }
  };

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
              {isLive ? "Live Stream Connected" : "Simulation / Offline Mode"}
            </span>
          </div>
          <h1 className="mt-1 font-display text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            AuraSense Console
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <div className="rounded-lg border border-border bg-card/50 px-4 py-2 text-sm font-medium text-muted-foreground">
            Hub Host: <span className="font-semibold text-foreground">Raspberry Pi 5</span>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="mt-8 grid gap-8 lg:grid-cols-3">
        {/* Left Column: Node status & energy details */}
        <div className="space-y-8 lg:col-span-2">
          {/* Nodes Registry */}
          <div className="rounded-2xl border border-border bg-card p-6">
            <h2 className="font-display text-xl font-bold text-foreground mb-4">Sensor Node Fleet</h2>
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
          </div>

          {/* NILM chart */}
          <div className="rounded-2xl border border-border bg-card p-6">
            <h2 className="font-display text-xl font-bold text-foreground mb-1">Energy Disaggregation (NILM)</h2>
            <p className="text-xs text-muted-foreground mb-6">Real-time load split analyzed locally from mains clamp-on current data</p>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={mockNilmData}>
                  <defs>
                    <linearGradient id="colorRef" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#818cf8" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#818cf8" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorHVAC" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#38bdf8" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" stroke="#6b7280" fontSize={11} />
                  <YAxis stroke="#6b7280" fontSize={11} unit="W" />
                  <Tooltip contentStyle={{ backgroundColor: "#1f2937", border: "none", borderRadius: "8px", color: "#fff" }} />
                  <Legend verticalAlign="top" height={36}/>
                  <Area type="monotone" dataKey="Refrigerator" stroke="#818cf8" fillOpacity={1} fill="url(#colorRef)" stackId="1" />
                  <Area type="monotone" dataKey="HVAC" stroke="#38bdf8" fillOpacity={1} fill="url(#colorHVAC)" stackId="1" />
                  <Area type="monotone" dataKey="Microwave" stroke="#e11d48" fillOpacity={0.2} fill="#e11d48" stackId="1" />
                  <Area type="monotone" dataKey="Other" stroke="#9ca3af" fillOpacity={0.1} fill="#9ca3af" stackId="1" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Right Column: Alerts and LLM Chat */}
        <div className="space-y-8">
          {/* Alerts Panel */}
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
                          onClick={() => acknowledgeEvent(evt.event_id)}
                          className="rounded bg-primary/10 hover:bg-primary/20 px-2 py-0.5 text-xs text-primary transition-colors font-medium"
                        >
                          Ack
                        </button>
                      )}
                    </div>
                    <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                      {evt.type === "microwave_running" ? "High continuous active load detected." : JSON.stringify(evt.payload)}
                    </p>
                    <p className="mt-2 text-[10px] text-muted-foreground/60">{new Date(evt.ts * 1000).toLocaleTimeString()}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* AI LLM Assistant Panel */}
          <div className="rounded-2xl border border-border bg-card p-6 flex flex-col h-[400px]">
            <h2 className="font-display text-xl font-bold text-foreground mb-1 flex items-center gap-2">
              <Bot className="h-5 w-5 text-primary" />
              On-Device Assistant
            </h2>
            <p className="text-xs text-muted-foreground mb-4">Query your hub locally without sharing home metrics with third parties</p>
            
            {/* Messages box */}
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
                    Thinking...
                  </div>
                </div>
              )}
            </div>

            {/* Input form */}
            <form onSubmit={handleSendMessage} className="flex gap-2">
              <input
                type="text"
                placeholder="Ask about electricity, fall, or node alerts..."
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
