import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Radar, ShieldCheck, AlertTriangle } from "lucide-react";
import { apiPost, ApiError } from "@/lib/api";

type Step = "form" | "success" | "error";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [step, setStep] = useState<Step>(token ? "form" : "error");
  const [errorMsg, setErrorMsg] = useState(token ? "" : "No reset token found in the URL. Please request a new reset link.");
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setErrorMsg("Passwords do not match.");
      return;
    }
    if (newPassword.length < 8) {
      setErrorMsg("Password must be at least 8 characters.");
      return;
    }
    setLoading(true);
    setErrorMsg("");
    try {
      await apiPost("/auth/reset-password", { token, new_password: newPassword });
      setStep("success");
    } catch (err) {
      const detail = err instanceof ApiError && typeof err.body === "object" && err.body && "detail" in err.body
        ? String((err.body as { detail: unknown }).detail)
        : "An error occurred. The reset link may be expired or already used.";
      setErrorMsg(detail);
      setStep("error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="reset-password-page" className="relative grid min-h-screen place-items-center overflow-hidden bg-[#050811] px-5">
      <div className="absolute inset-0 opacity-20 [background-image:linear-gradient(rgba(0,229,255,.12)_1px,transparent_1px),linear-gradient(90deg,rgba(0,229,255,.12)_1px,transparent_1px)] [background-size:64px_64px]" />
      <div className="relative w-full max-w-md rounded-xl border border-slate-800 bg-[#0a101d]/95 p-8 shadow-2xl">
        <div className="mb-8 flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded border border-cyan-400/50 bg-cyan-400/10 text-cyan-300"><Radar /></div>
          <div>
            <div className="font-heading text-xl font-black tracking-[0.2em] text-white">ORBIS</div>
            <div className="font-mono text-[9px] tracking-[0.16em] text-slate-500">PASSWORD RESET</div>
          </div>
        </div>

        {step === "form" && (
          <>
            <h1 data-testid="reset-password-heading" className="font-heading text-2xl font-bold text-white">Set new passphrase</h1>
            <p className="mt-2 text-sm text-slate-500">Choose a strong passphrase for your operator account. Minimum 8 characters.</p>
            <form data-testid="reset-password-form" onSubmit={submit} className="mt-7 space-y-4">
              <label className="block font-mono text-[10px] uppercase tracking-wider text-slate-500">
                New Passphrase
                <input
                  data-testid="reset-password-new-input"
                  required
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="mt-2 h-11 w-full rounded border border-slate-800 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-400/60"
                />
              </label>
              <label className="block font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Confirm Passphrase
                <input
                  data-testid="reset-password-confirm-input"
                  required
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="mt-2 h-11 w-full rounded border border-slate-800 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-400/60"
                />
              </label>
              {errorMsg && <div data-testid="reset-password-error" className="rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">{errorMsg}</div>}
              <button
                data-testid="reset-password-submit"
                type="submit"
                disabled={loading}
                className="flex h-11 w-full items-center justify-center gap-2 rounded bg-cyan-400 text-sm font-bold text-slate-950 transition-colors hover:bg-cyan-300 disabled:opacity-50"
              >
                <ShieldCheck size={16} />
                {loading ? "UPDATING…" : "SET NEW PASSPHRASE"}
              </button>
            </form>
          </>
        )}

        {step === "success" && (
          <div data-testid="reset-password-success">
            <div className="mb-4 grid h-14 w-14 place-items-center rounded-full border border-emerald-400/40 bg-emerald-400/10">
              <ShieldCheck size={24} className="text-emerald-300" />
            </div>
            <h1 className="font-heading text-2xl font-bold text-white">Passphrase updated</h1>
            <p data-testid="reset-password-success-message" className="mt-3 text-sm leading-6 text-slate-400">
              Your passphrase has been changed. Sign in with your new credentials to access ORBIS mission control.
            </p>
            <Link to="/login" data-testid="reset-password-login-link" className="mt-6 flex h-11 items-center justify-center gap-2 rounded bg-cyan-400 text-sm font-bold text-slate-950 transition-colors hover:bg-cyan-300">
              <ShieldCheck size={16} /> SIGN IN
            </Link>
          </div>
        )}

        {step === "error" && (
          <div data-testid="reset-password-error-state">
            <div className="mb-4 grid h-14 w-14 place-items-center rounded-full border border-amber-400/40 bg-amber-400/10">
              <AlertTriangle size={24} className="text-amber-300" />
            </div>
            <h1 className="font-heading text-2xl font-bold text-white">Reset link invalid</h1>
            <p data-testid="reset-password-error-message" className="mt-3 text-sm leading-6 text-red-300">{errorMsg}</p>
            <Link to="/forgot-password" className="mt-4 block text-sm text-cyan-300 hover:text-white">Request a new reset link →</Link>
          </div>
        )}

        <div className="mt-6 border-t border-slate-800 pt-5">
          <Link to="/login" className="text-sm text-slate-500 hover:text-cyan-300">← Return to sign in</Link>
        </div>
      </div>
    </div>
  );
}
