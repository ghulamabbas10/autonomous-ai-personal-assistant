import type { AuthenticationResponse, User } from "@/lib/types";

interface ApiErrorBody {
  detail?: string | Array<{ msg?: string }>;
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
  }
}

function errorMessage(body: ApiErrorBody): string {
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) return body.detail.map((item) => item.msg).filter(Boolean).join(". ");
  return "Something went wrong. Please try again.";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let body: ApiErrorBody = {};
    try { body = (await response.json()) as ApiErrorBody; } catch { /* non-JSON error */ }
    throw new ApiError(errorMessage(body), response.status);
  }
  return response.json() as Promise<T>;
}

export const authApi = {
  register: (payload: { email: string; password: string; display_name: string; timezone: string }) =>
    request<AuthenticationResponse>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload: { email: string; password: string }) =>
    request<AuthenticationResponse>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  me: () => request<User>("/auth/me"),
  logout: (csrfToken: string) => request<{ message: string }>("/auth/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": csrfToken },
  }),
};

export function getCsrfCookie(): string {
  if (typeof document === "undefined") return "";
  const cookie = document.cookie.split("; ").find((item) => item.startsWith("assistant_csrf="));
  return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : "";
}
