import { apiFetch, buildHeaders } from "./api-client";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface DocumentInfo {
  id: string;
  name: string;
  sha256: string;
  pages: number | null;
  status: string;
  created_at: string;
}

export interface UploadResponse {
  document_id: string;
  job_id: string;
  name: string;
  sha256: string;
  inline: boolean;
}

export interface JobStatus {
  id: string;
  document_id: string;
  status: string;
  progress: number;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export async function uploadDocument(
  sessionId: string,
  file: File,
): Promise<UploadResponse> {
  const fd = new FormData();
  fd.append("file", file, file.name);
  const headers = buildHeaders();
  headers.delete("Content-Type"); // let the browser set the multipart boundary

  const res = await fetch(
    `${API_BASE}/api/sessions/${sessionId}/documents`,
    {
      method: "POST",
      headers,
      body: fd,
    },
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return (await res.json()) as UploadResponse;
}

export async function listDocuments(sessionId: string): Promise<DocumentInfo[]> {
  return apiFetch<DocumentInfo[]>(`/api/sessions/${sessionId}/documents`);
}

export async function getJob(jobId: string): Promise<JobStatus> {
  return apiFetch<JobStatus>(`/api/jobs/${jobId}`);
}
