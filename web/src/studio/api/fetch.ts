import type { Issue } from "./types";

export class ApiError extends Error {
  status: number;
  issues: Issue[];

  constructor(status: number, message: string, issues: Issue[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.issues = issues;
  }
}

/** The issues a refusal carries: the studio's `{"issues": [...]}`, else FastAPI's `detail`. */
export function issuesOf(body: unknown): Issue[] {
  if (body && typeof body === "object") {
    const b = body as { issues?: unknown; detail?: unknown };
    if (Array.isArray(b.issues)) return b.issues as Issue[];
    if (Array.isArray(b.detail)) {
      return b.detail.map((d: { msg?: string; loc?: unknown[] }) => ({
        level: "error" as const,
        code: "request",
        message: d.msg ?? "invalid request",
        ref: Array.isArray(d.loc) ? d.loc.join(".") : null,
      }));
    }
    if (typeof b.detail === "string") {
      return [
        { level: "error", code: "request", message: b.detail, ref: null },
      ];
    }
  }
  return [];
}

/** orval's mutator: fetch, parse JSON, and throw `ApiError` on a non-2xx reply. */
export async function customFetch<T>(
  url: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(url, init);
  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }
  if (!response.ok) {
    const issues = issuesOf(body);
    const message =
      issues[0]?.message ??
      `${init.method ?? "GET"} ${url} failed (${response.status})`;
    throw new ApiError(response.status, message, issues);
  }
  return {
    data: body,
    status: response.status,
    headers: response.headers,
  } as T;
}
