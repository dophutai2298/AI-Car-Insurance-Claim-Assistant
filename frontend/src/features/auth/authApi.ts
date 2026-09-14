import type { AuthSession, AuthUser, LoginCredentials } from "./types";

export class AuthApiError extends Error {}

export async function login(
  credentials: LoginCredentials,
): Promise<AuthSession> {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });
  const body = (await response.json()) as AuthSession | { detail?: string };

  if (!response.ok) {
    throw new AuthApiError(
      "detail" in body && body.detail ? body.detail : "Unable to sign in",
    );
  }

  return body as AuthSession;
}

export async function getCurrentUser(accessToken: string): Promise<AuthUser> {
  const response = await fetch("/api/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) throw new AuthApiError("Session expired");
  return (await response.json()) as AuthUser;
}
