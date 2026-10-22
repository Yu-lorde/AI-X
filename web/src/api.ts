import type { Editor, GenerateFailure, Inputs, Meta, Preview, WorkData, WorkSummary } from "./types";

async function parse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = (data as { detail?: string }).detail || `请求失败（${response.status}）`;
    throw new Error(message);
  }
  return data as T;
}

const post = (url: string, body: unknown) =>
  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const api = {
  meta: () => fetch("/api/meta").then((r) => parse<Meta>(r)),

  generate: (inputs: Inputs) => post("/api/generate", inputs).then((r) => parse<WorkData | GenerateFailure>(r)),

  works: () => fetch("/api/works").then((r) => parse<{ works: WorkSummary[]; error?: string }>(r)),

  work: (workId: string, version?: number) =>
    fetch(`/api/works/${workId}${version ? `?version=${version}` : ""}`).then((r) => parse<WorkData>(r)),

  preview: (workId: string, editor: Editor) =>
    post(`/api/works/${workId}/preview`, { editor }).then((r) => parse<Preview>(r)),

  saveVersion: (workId: string, editor: Editor, sourceVersionNo?: number) =>
    post(`/api/works/${workId}/versions`, { editor, source_version_no: sourceVersionNo ?? null }).then((r) =>
      parse<WorkData>(r),
    ),

  remove: (workId: string) =>
    fetch(`/api/works/${workId}`, { method: "DELETE" }).then((r) => parse<{ ok: boolean }>(r)),

  testKb: () => post("/api/test-kb", {}).then((r) => parse<{ report: string; credentials: Meta["credentials"] }>(r)),
};
