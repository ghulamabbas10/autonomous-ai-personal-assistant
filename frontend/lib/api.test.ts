import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, authApi, getCsrfCookie } from "./api";

afterEach(() => vi.restoreAllMocks());

describe("auth API", () => {
  it("sends credentials with login", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ user: {}, csrf_token: "token" }), { status: 200 }));
    await authApi.login({ email: "person@example.com", password: "Example123456" });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/auth/login", expect.objectContaining({ method: "POST", credentials: "include" }));
  });

  it("surfaces API detail", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "invalid email or password" }), { status: 401 }));
    await expect(authApi.login({ email: "person@example.com", password: "bad" })).rejects.toEqual(new ApiError("invalid email or password", 401));
  });

  it("reads the CSRF cookie", () => {
    document.cookie = "assistant_csrf=test-token";
    expect(getCsrfCookie()).toBe("test-token");
  });
});
