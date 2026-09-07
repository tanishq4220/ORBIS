import { useState } from "react";
import type { FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Radar, ShieldCheck } from "lucide-react";
import { apiPost, ApiError } from "@/lib/api";
import type { AuthUser } from "@/lib/orbis";
import { beginSession, SessionCookieError, verifySession } from "@/lib/session";

export default function Login() {
  const [email, setEmail] = useState("operator@orbis.local");
  const [password, setPassword] = useState("ORBIS-DEMO-2026");
  const [error, setError] = useState("");
  const [cookieBlocked, setCookieBlocked] = useState(false);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const login = useMutation({
    mutationFn: async () => {
      await apiPost<AuthUser>("/auth/login", { email, password });
      return verifySession();
    },
    onSuccess: (user) => {
      beginSession();
      qc.setQueryData(["auth-me"], user);
      navigate("/dashboard", { replace: true });
    },
    onError: (e) => {
      setCookieBlocked(e instanceof SessionCookieError);
      setError(e instanceof ApiError && typeof e.body === "object" && e.body && "detail" in e.body
        ? String((e.body as { detail: unknown }).detail)
        : e instanceof Error ? e.message : "Authentication failed");
    },
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setCookieBlocked(false);
    login.mutate();
  };

  return <div data-testid="login-page" className="relative grid min-h-screen place-items-center overflow-hidden bg-[#050811] px-5">
    <div className="absolute inset-0 opacity-20 [background-image:linear-gradient(rgba(0,229,255,.12)_1px,transparent_1px),linear-gradient(90deg,rgba(0,229,255,.12)_1px,transparent_1px)] [background-size:64px_64px]" />
    <div className="relative w-full max-w-md rounded-xl border border-slate-800 bg-[#0a101d]/95 p-8 shadow-2xl">
      <div className="mb-8 flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded border border-cyan-400/50 bg-cyan-400/10 text-cyan-300"><Radar /></div>
        <div><div data-testid="login-brand" className="font-heading text-xl font-black tracking-[0.2em] text-white">ORBIS</div><div data-testid="login-brand-subtitle" className="font-mono text-[9px] tracking-[0.16em] text-slate-500">MISSION CONTROL ACCESS</div></div>
      </div>
      <h1 data-testid="login-heading" className="font-heading text-2xl font-bold text-white">Operator sign-in</h1>
      <p data-testid="login-description" className="mt-2 text-sm text-slate-500">Authenticate to access orbital surveillance telemetry.</p>
      <form data-testid="login-form" onSubmit={submit} className="mt-7 space-y-4">
        <label data-testid="login-email-label" className="block font-mono text-[10px] uppercase tracking-wider text-slate-500">Email<input data-testid="login-email-input" required autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} type="email" className="mt-2 h-11 w-full rounded border border-slate-800 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-400/60" /></label>
        <label data-testid="login-password-label" className="block font-mono text-[10px] uppercase tracking-wider text-slate-500">Passphrase<input data-testid="login-password-input" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} type="password" className="mt-2 h-11 w-full rounded border border-slate-800 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-400/60" /></label>
        {error ? <div data-testid="login-error" role="alert" className="rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
          <p data-testid="login-error-message">{error}</p>
          {cookieBlocked ? <a data-testid="login-open-new-tab-link" href="/login" target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-cyan-300 underline transition-colors hover:text-white">Open ORBIS in a new tab</a> : null}
        </div> : null}
        <button data-testid="login-submit-button" disabled={login.isPending} className="flex h-11 w-full items-center justify-center gap-2 rounded bg-cyan-400 text-sm font-bold text-slate-950 transition-colors hover:bg-cyan-300 disabled:opacity-50"><ShieldCheck size={16} />{login.isPending ? "AUTHENTICATING" : "ENTER MISSION CONTROL"}</button>
      </form>
      <div data-testid="demo-credentials-note" className="mt-5 rounded border border-slate-800 bg-slate-950/70 p-3 font-mono text-[10px] text-slate-500">DEMO ACCESS · operator@orbis.local · ORBIS-DEMO-2026</div>
      <div className="mt-5 flex justify-between text-xs"><Link data-testid="forgot-password-link" to="/forgot-password" className="text-slate-500 hover:text-cyan-300">Forgot password?</Link><Link data-testid="register-link" to="/register" className="text-cyan-300 hover:text-white">Register operator</Link></div>
    </div>
  </div>;
}