// Session boundary: auth is an httpOnly cookie the backend owns; the frontend's one
// duty is wiping the react-query cache so one account's data never renders for the next.
import { queryClient } from "./queryClient";
import { apiGet, apiPost } from "./api";
import type { AuthUser } from "./orbis";

export class SessionCookieError extends Error {
  constructor() {
    super("Your browser blocked the sign-in session in this preview. Open ORBIS in a new tab and sign in there.");
    this.name = "SessionCookieError";
  }
}

// Confirm the browser returned the HTTP-only cookie before entering protected routes.
export async function verifySession(): Promise<AuthUser> {
  const user = await apiGet<AuthUser | null>("/auth/me");
  if (!user) throw new SessionCookieError();
  return user;
}

// Call after every successful login/signup.
export function beginSession(): void {
  queryClient.clear();
}

// Call from every sign-out control; the hard redirect resets all in-memory state.
export async function endSession(redirectTo: string = "/login"): Promise<void> {
  await apiPost("/auth/logout");
  queryClient.clear();
  window.location.assign(redirectTo);
}
