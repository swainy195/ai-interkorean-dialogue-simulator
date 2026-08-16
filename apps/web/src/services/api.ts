// Production uses VITE_API_BASE_URL; local Vite proxies /api and /health to FastAPI.
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export type State = Record<string, any>;
export type Turn = Record<string, any>;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { headers: { "Content-Type": "application/json" }, ...init });
  if (!response.ok) throw new Error("AI 응답을 불러오지 못했습니다.");
  return response.json() as Promise<T>;
}

export const createSimulation = (payload: Record<string, any>) => request<{ session_id: string; state: State }>("/api/v1/simulations", { method: "POST", body: JSON.stringify(payload) });
export const nextTurn = (id: string) => request<Record<string, any>>(`/api/v1/simulations/${id}/next`, { method: "POST" });
export const userTurn = (id: string, message: string) => request<Record<string, any>>(`/api/v1/simulations/${id}/user-turn`, { method: "POST", body: JSON.stringify({ message }) });
export const getSuggestions = (id: string) => request<{ suggestions: string[] }>(`/api/v1/simulations/${id}/suggestions`, { method: "POST" });
export const getEvidence = (id: string) => request<{ evidence: Record<string, any>[] }>(`/api/v1/simulations/${id}/evidence`);
export const getSimulation = (id: string) => request<{ session_id: string; state: State }>(`/api/v1/simulations/${id}`);

export async function streamNext(id: string, onToken: (text: string) => void): Promise<Record<string, any>> {
  const response = await fetch(`${API_BASE}/api/v1/simulations/${id}/next/stream`, { method: "POST" });
  if (!response.ok || !response.body) throw new Error("Streaming을 시작하지 못했습니다.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let final: Record<string, any> | null = null;
  while (true) {
    const chunk = await reader.read();
    if (chunk.done) break;
    buffer += decoder.decode(chunk.value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const event of events) {
      const data = event.split("\n").find((line) => line.startsWith("data: "))?.slice(6);
      if (!data) continue;
      const parsed = JSON.parse(data) as Record<string, any>;
      if (event.startsWith("event: token")) onToken(parsed.text || "");
      if (event.startsWith("event: done")) final = parsed;
      if (event.startsWith("event: error")) throw new Error(parsed.message || "Streaming 오류");
    }
  }
  if (!final) throw new Error("Streaming 응답이 완결되지 않았습니다.");
  return final;
}
