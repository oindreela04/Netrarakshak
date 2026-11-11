"use client";
/** Typed fetch wrapper with access-token refresh. Tokens live in sessionStorage (cleared when the tab closes). */
export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

const ACCESS = "nr_access";
const REFRESH = "nr_refresh";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export const tokens = {
  get access() { return typeof window === "undefined" ? null : sessionStorage.getItem(ACCESS); },
  get refresh() { return typeof window === "undefined" ? null : sessionStorage.getItem(REFRESH); },
  set(a: string, r: string) { sessionStorage.setItem(ACCESS, a); sessionStorage.setItem(REFRESH, r); },
  clear() { sessionStorage.removeItem(ACCESS); sessionStorage.removeItem(REFRESH); },
};

let refreshing: Promise<boolean> | null = null;
async function tryRefresh(): Promise<boolean> {
  if (!tokens.refresh) return false;
  refreshing ??= (async () => {
    try {
      const r = await fetch(`${API_URL}/api/auth/refresh`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: tokens.refresh }),
      });
      if (!r.ok) { tokens.clear(); return false; }
      const j = await r.json();
      tokens.set(j.access_token, j.refresh_token);
      return true;
    } finally { setTimeout(() => (refreshing = null), 0); }
  })();
  return refreshing;
}

function errorMessage(body: any, status: number) {
  const d = body?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((e: any) => `${(e.loc || []).slice(1).join(".")}: ${e.msg}`).join("; ");
  return `Request failed (${status})`;
}

export async function raw(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(init.headers);
  if (tokens.access) headers.set("Authorization", `Bearer ${tokens.access}`);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const res = await fetch(`${API_URL}/api${path}`, { ...init, headers });
  if (res.status === 401 && retry && tokens.refresh && !path.startsWith("/auth/login")) {
    if (await tryRefresh()) return raw(path, init, false);
    if (typeof window !== "undefined" && window.location.pathname.startsWith("/app")) window.location.href = "/login?expired=1";
  }
  if (!res.ok) {
    let body: any = null;
    try { body = await res.json(); } catch {}
    throw new ApiError(res.status, errorMessage(body, res.status));
  }
  return res;
}

export async function api<T = any>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, ...rest } = init;
  const res = await raw(path, json !== undefined ? { ...rest, body: JSON.stringify(json) } : rest);
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function blobUrl(path: string): Promise<string> {
  const res = await raw(path);
  return URL.createObjectURL(await res.blob());
}
