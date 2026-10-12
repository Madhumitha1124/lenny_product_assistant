// API service — all calls to the FastAPI backend
import type {
  Session, Message, ChatRequest, ChatResponse,
  ModelsResponse, Artifact, Ship30Request, Ship30Response,
  HealthResponse, KnowledgeSource,
} from '../types';

const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      detail = err.detail ?? err.message ?? detail;
    } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Health ────────────────────────────────────────────────────────────────────
export const getHealth = () => request<HealthResponse>('/health');

// ── Models ────────────────────────────────────────────────────────────────────
export const getModels = () => request<ModelsResponse>('/models');

// ── Sessions ──────────────────────────────────────────────────────────────────
export const getSessions = () => request<Session[]>('/sessions');

export const createSession = (title = 'New Chat', provider = 'ollama', model = 'llama3.2:3b') =>
  request<Session>('/sessions', {
    method: 'POST',
    body: JSON.stringify({ title, provider, model }),
  });

export const getMessages = (sessionId: string) =>
  request<Message[]>(`/sessions/${sessionId}/messages`);

export const deleteSession = (sessionId: string) =>
  request<void>(`/sessions/${sessionId}`, { method: 'DELETE' });

// ── Chat ──────────────────────────────────────────────────────────────────────
export const sendChat = (body: ChatRequest) =>
  request<ChatResponse>('/chat', { method: 'POST', body: JSON.stringify(body) });

// ── Knowledge ─────────────────────────────────────────────────────────────────
export const getKnowledgeSources = () => request<KnowledgeSource[]>('/knowledge/sources');

export const ingestFile = (filePath: string, title: string, author?: string, sourceUrl?: string) =>
  request('/ingest', {
    method: 'POST',
    body: JSON.stringify({ file_path: filePath, title, author, source_url: sourceUrl }),
  });

// ── Artifacts ─────────────────────────────────────────────────────────────────
export const getArtifact = (id: string) => request<Artifact>(`/artifacts/${id}`);

export const createArtifact = (
  prompt: string,
  artifactType: string,
  title: string,
  sessionId?: string,
  provider = 'ollama',
  model = 'llama3.2:3b',
) =>
  request<Artifact>('/artifacts', {
    method: 'POST',
    body: JSON.stringify({
      prompt,
      artifact_type: artifactType,
      title,
      session_id: sessionId,
      provider,
      model,
    }),
  });

// ── Ship 30 ───────────────────────────────────────────────────────────────────
export const generateShip30 = (body: Ship30Request) =>
  request<Ship30Response>('/skills/ship30', { method: 'POST', body: JSON.stringify(body) });
