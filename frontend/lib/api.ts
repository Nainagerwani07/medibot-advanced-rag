// Thin client for the FastAPI backend (R6). The role shown in the UI always comes from the
// server (login response / chat response), never from local state the user could edit.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Session = {
  access_token: string;
  username: string;
  role: string;
  collections: string[];
};

export type Source = { source_document: string; section_title: string; collection: string };

export type ChatResponse = {
  answer: string;
  sources: Source[];
  retrieval_type: "hybrid_rag" | "sql_rag";
  role: string;
  blocked: boolean;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export const login = (username: string, password: string) =>
  request<Session>("/login", { method: "POST", body: JSON.stringify({ username, password }) });

export const chat = (question: string, token: string) =>
  request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify({ question }) }, token);

export const collections = (role: string, token: string) =>
  request<{ role: string; collections: string[] }>(`/collections/${role}`, {}, token);
