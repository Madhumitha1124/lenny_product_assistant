// Shared TypeScript types for the Lenny Growth Assistant

export interface Session {
  id: string;
  title: string;
  provider: string;
  model: string;
  created_at: string;
  updated_at: string;
}

export interface SourceCitation {
  source_id: string;
  title: string;
  author?: string;
  source_url?: string;
  excerpt: string;
  is_demo: boolean;
}

export interface Message {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  provider?: string;
  model?: string;
  sources: SourceCitation[];
  artifact_id?: string;
  created_at: string;
}

export interface ChatRequest {
  session_id?: string;
  message: string;
  provider: string;
  model: string;
}

export interface ChatResponse {
  session_id: string;
  message_id: string;
  content: string;
  provider: string;
  model: string;
  sources: SourceCitation[];
  artifact_id?: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  available: boolean;
  description: string;
}

export interface ModelsResponse {
  models: ModelInfo[];
  default_provider: string;
  default_model: string;
}

export interface Artifact {
  id: string;
  session_id?: string;
  title: string;
  artifact_type: 'markdown' | 'html' | 'prd' | 'landing_page' | 'growth_plan' | 'strategy' | 'essay';
  content: string;
  created_at: string;
  updated_at: string;
}

export interface Ship30Request {
  topic: string;
  session_id?: string;
  provider: string;
  model: string;
}

export interface Ship30Response {
  artifact_id: string;
  title: string;
  content: string;
  word_count: number;
  sources: SourceCitation[];
}

export interface HealthResponse {
  status: string;
  version: string;
  database: string;
  ollama: string;
  knowledge_sources: number | null;
}

export interface KnowledgeSource {
  id: string;
  title: string;
  author?: string;
  source_url?: string;
  source_type: string;
  is_demo: boolean;
  chunk_count: number;
  ingested_at: string;
}
