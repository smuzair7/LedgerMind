"use client";

import * as React from "react";
import { FileText, UploadCloud, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import {
  getJob,
  listDocuments,
  uploadDocument,
  type DocumentInfo,
  type JobStatus,
} from "@/lib/documents-api";
import { cn } from "@/lib/cn";

interface UploadRow {
  fileName: string;
  documentId?: string;
  jobId?: string;
  status: "uploading" | "queued" | "parsing" | "embedding" | "indexing" | "done" | "error";
  progress: number;
  error?: string;
}

export function DocumentPanel({ sessionId }: { sessionId: string }) {
  const [docs, setDocs] = React.useState<DocumentInfo[]>([]);
  const [uploads, setUploads] = React.useState<UploadRow[]>([]);
  const [dragOver, setDragOver] = React.useState(false);

  const refresh = React.useCallback(async () => {
    try {
      setDocs(await listDocuments(sessionId));
    } catch {
      // empty session = empty list; ignore
    }
  }, [sessionId]);

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleFiles(files: FileList | File[]) {
    const arr = Array.from(files).filter((f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"));
    for (const file of arr) {
      const idx = uploads.length;
      setUploads((prev) => [
        ...prev,
        { fileName: file.name, status: "uploading", progress: 0 },
      ]);
      try {
        const resp = await uploadDocument(sessionId, file);
        setUploads((prev) =>
          patchAt(prev, idx, {
            documentId: resp.document_id,
            jobId: resp.job_id,
            status: resp.inline ? "done" : "queued",
            progress: resp.inline ? 100 : 5,
          }),
        );
        if (!resp.inline) {
          pollJob(resp.job_id, idx);
        } else {
          refresh();
        }
      } catch (e) {
        setUploads((prev) =>
          patchAt(prev, idx, {
            status: "error",
            error: String(e),
          }),
        );
      }
    }
  }

  function pollJob(jobId: string, idx: number) {
    let delay = 800;
    let cancelled = false;

    async function tick() {
      if (cancelled) return;
      try {
        const job: JobStatus = await getJob(jobId);
        setUploads((prev) =>
          patchAt(prev, idx, {
            status: classify(job.status),
            progress: job.progress,
            error: job.error ?? undefined,
          }),
        );
        if (job.status === "done" || job.status === "error") {
          refresh();
          return;
        }
      } catch {
        // ignore one failure; back off and retry
      }
      delay = Math.min(delay + 200, 3000);
      setTimeout(tick, delay);
    }

    tick();
    return () => {
      cancelled = true;
    };
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) {
      void handleFiles(e.dataTransfer.files);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-4 pt-3">
        <h3 className="text-sm font-semibold">Documents</h3>
        <label className="cursor-pointer text-xs text-accent hover:text-accent-hi">
          + Add
          <input
            type="file"
            accept="application/pdf"
            multiple
            className="hidden"
            onChange={(e) => e.target.files && handleFiles(e.target.files)}
          />
        </label>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={cn(
          "mx-4 mt-3 rounded-xl border border-dashed p-6 text-center text-xs transition-colors",
          dragOver ? "border-accent bg-accent/5 text-ink" : "border-border text-muted",
        )}
      >
        <UploadCloud className="mx-auto mb-2 h-5 w-5" />
        Drop a PDF here, or use <span className="text-accent">+ Add</span> above.
      </div>

      {uploads.length > 0 && (
        <ul className="mt-4 space-y-2 px-4">
          {uploads.map((u, i) => (
            <li key={i} className="rounded-md border border-border bg-surface2/60 p-2">
              <div className="flex items-center justify-between text-xs">
                <span className="truncate">{u.fileName}</span>
                <StatusIcon status={u.status} />
              </div>
              <div className="mt-1.5 h-1 w-full overflow-hidden rounded bg-border/60">
                <div
                  className={cn(
                    "h-full transition-all",
                    u.status === "error" ? "bg-negative" : "bg-accent",
                  )}
                  style={{ width: `${u.progress}%` }}
                />
              </div>
              {u.error && <p className="mt-1 text-[10px] text-negative">{u.error}</p>}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-6 px-4 text-xs uppercase tracking-wider text-muted">Indexed</div>
      <ul className="mt-2 space-y-1 px-2 pb-6">
        {docs.length === 0 ? (
          <li className="px-2 text-xs text-muted/80">No documents yet.</li>
        ) : (
          docs.map((d) => (
            <li
              key={d.id}
              className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-ink hover:bg-surface2/60"
              title={`sha256: ${d.sha256.slice(0, 12)}…`}
            >
              <FileText className="h-4 w-4 text-accent" />
              <span className="truncate">{d.name}</span>
              {d.pages != null && (
                <span className="ms-auto shrink-0 text-[11px] text-muted">{d.pages}p</span>
              )}
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

function classify(status: string): UploadRow["status"] {
  const s = status.toLowerCase();
  if (s === "done") return "done";
  if (s === "error") return "error";
  if (s.includes("parse")) return "parsing";
  if (s.includes("embed")) return "embedding";
  if (s.includes("index")) return "indexing";
  return "queued";
}

function patchAt(prev: UploadRow[], idx: number, patch: Partial<UploadRow>): UploadRow[] {
  if (idx < 0 || idx >= prev.length) return prev;
  const next = prev.slice();
  next[idx] = { ...next[idx], ...patch };
  return next;
}

function StatusIcon({ status }: { status: UploadRow["status"] }) {
  if (status === "done") return <CheckCircle2 className="h-4 w-4 text-positive" />;
  if (status === "error") return <AlertCircle className="h-4 w-4 text-negative" />;
  return <Loader2 className="h-4 w-4 animate-spin text-accent" />;
}
