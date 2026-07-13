import type { HealthResponse, LectureDetail, LectureSummary } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail ?? message;
    } catch {
      // Preserve the HTTP status when the response is not JSON.
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  list: () => request<LectureSummary[]>("/lectures"),
  get: (id: string) => request<LectureDetail>(`/lectures/${id}`),
  upload: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<LectureSummary>("/lectures", { method: "POST", body });
  },
  delete: (id: string) => request<void>(`/lectures/${id}`, { method: "DELETE" }),
  exportUrl: (id: string) => `${API_BASE}/lectures/${id}/export.md`,
};
