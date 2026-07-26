// Typed client for the AuraSense hub API.
//
// Handles pairing-based auth (F2) transparently: it exchanges the configured
// pairing code for a bearer token, caches it, and attaches it to every request,
// re-pairing on expiry or a 401. The console imports the typed calls below and
// never deals with tokens itself.

const HUB_URL: string =
  (import.meta.env.VITE_HUB_URL as string | undefined) ?? "http://localhost:8000";
const PAIRING_CODE: string =
  (import.meta.env.VITE_PAIRING_CODE as string | undefined) ?? "aurasense-dev";

export interface NodeStatus {
  node_id: string;
  type: "power" | "audio" | "motion" | "env";
  last_seen: number;
  firmware_version: string;
  status: "ONLINE" | "STALE" | "OFFLINE";
}

export interface EventPayload {
  event_id: string;
  ts: number;
  type: string;
  severity: "INFO" | "WARNING" | "CRITICAL";
  node_id: string;
  payload: Record<string, unknown>;
  acknowledged: boolean;
}

export interface EnergyPoint {
  ts: number;
  node_id: string;
  total_w: number;
  // plus one numeric field per appliance (refrigerator, microwave, hvac, other, ...)
  [appliance: string]: number | string;
}

export interface EnergyResponse {
  points: EnergyPoint[];
  appliances: string[];
}

export interface AnomalyScore {
  ts: number;
  model: string;
  score: number;
  context: Record<string, unknown>;
}

interface Envelope<T> {
  data: T;
  meta?: Record<string, unknown>;
}

// --- token handling ---------------------------------------------------------
let cachedToken: string | null = null;
let tokenExpiresAt = 0; // unix seconds

async function pair(): Promise<string> {
  const res = await fetch(`${HUB_URL}/api/v1/pair`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pairing_code: PAIRING_CODE, client_name: "aurasense-dashboard" }),
  });
  if (!res.ok) throw new Error(`pairing failed: ${res.status}`);
  const body = (await res.json()) as Envelope<{ access_token: string; expires_at: number }>;
  cachedToken = body.data.access_token;
  tokenExpiresAt = body.data.expires_at;
  return cachedToken;
}

async function getToken(): Promise<string> {
  const nowSec = Math.floor(Date.now() / 1000);
  if (cachedToken && nowSec < tokenExpiresAt - 60) return cachedToken;
  return pair();
}

async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = await getToken();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  let res = await fetch(`${HUB_URL}${path}`, { ...init, headers });
  if (res.status === 401) {
    // token stale/rotated — re-pair once and retry
    cachedToken = null;
    const fresh = await getToken();
    headers.set("Authorization", `Bearer ${fresh}`);
    res = await fetch(`${HUB_URL}${path}`, { ...init, headers });
  }
  return res;
}

async function getJson<T>(path: string, init?: RequestInit): Promise<Envelope<T>> {
  const res = await authFetch(path, init);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return (await res.json()) as Envelope<T>;
}

// --- typed calls ------------------------------------------------------------
export async function getNodes(): Promise<NodeStatus[]> {
  return (await getJson<NodeStatus[]>("/api/v1/nodes")).data;
}

export async function getEvents(): Promise<EventPayload[]> {
  return (await getJson<EventPayload[]>("/api/v1/events")).data;
}

export async function ackEvent(eventId: string): Promise<void> {
  await authFetch(`/api/v1/events/${eventId}/ack`, { method: "POST" });
}

export async function getEnergy(minutes = 60): Promise<EnergyResponse> {
  const env = await getJson<EnergyPoint[]>(`/api/v1/energy?minutes=${minutes}`);
  const appliances = (env.meta?.appliances as string[] | undefined) ?? [];
  return { points: env.data, appliances };
}

export async function getAnomalyScores(minutes = 60): Promise<AnomalyScore[]> {
  return (await getJson<AnomalyScore[]>(`/api/v1/anomaly-scores?minutes=${minutes}`)).data;
}

export async function queryAssistant(prompt: string): Promise<string> {
  const res = await getJson<{ response: string }>("/api/v1/assistant", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  return res.data.response;
}

export function eventsWsUrl(): string {
  return `${HUB_URL.replace(/^http/, "ws")}/ws/v1/events`;
}

export const hubUrl = HUB_URL;
