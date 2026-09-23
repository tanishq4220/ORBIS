import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { Radar, Mail, ArrowLeft } from "lucide-react";
import { apiPost, ApiError } from "@/lib/api";

type Step = "form" | "sent" | "error";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [step, setStep] = useState<Step>("form");
  const [errorMsg, setErrorMsg] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg("");
    try {
      await apiPost("/auth/forgot-password", { email: email.trim() });
      setStep("sent");
    } catch (err) {
      if (err instanceof ApiError && err.status !== 500) {
        setErrorMsg(err.status === 429 ? "Too many requests. Please wait before trying again." : "An error occurred. Please try again.");
      } else {
        setErrorMsg("An error occurred. Please try again.");
      }
      setStep("error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-testid="forgot-password-page" className="relative grid min-h-screen place-items-center overflow-hidden bg-[#050811] px-5">
      <div className="absolute inset-0 opacity-20 [background-image:linear-gradient(rgba(0,229,255,.12)_1px,transparent_1px),linear-gradient(90deg,rgba(0,229,255,.12)_1px,transparent_1px)] [background-size:64px_64px]" />
      <div className="relative w-full max-w-md rounded-xl border border-slate-800 bg-[#0a101d]/95 p-8 shadow-2xl">
        <div className="mb-8 flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded border border-cyan-400/50 bg-cyan-400/10 text-cyan-300"><Radar /></div>
          <div>
            <div data-testid="forgot-password-brand" className="font-heading text-xl font-black tracking-[0.2em] text-white">ORBIS</div>
            <div className="font-mono text-[9px] tracking-[0.16em] text-slate-500">RECOVERY CHANNEL</div>
          </div>
        </div>

        {step === "form" && (
          <>
            <h1 data-testid="forgot-password-heading" className="font-heading text-2xl font-bold text-white">Reset access</h1>
            <p data-testid="forgot-password-description" className="mt-2 text-sm text-slate-500">Enter your operator email. If an account exists, a secure reset link will be sent.</p>
            <form data-testid="forgot-password-form" onSubmit={submit} className="mt-7 space-y-4">
              <label className="block font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Email
                <input
                  data-testid="forgot-password-email-input"
                  required
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-2 h-11 w-full rounded border border-slate-800 bg-slate-950 px-3 text-sm text-white outline-none focus:border-cyan-400/60"
                />
              </label>
              <button
                data-testid="forgot-password-submit"
                type="submit"
                disabled={loading || !email.trim()}
                className="flex h-11 w-full items-center justify-center gap-2 rounded bg-cyan-400 text-sm font-bold text-slate-950 transition-colors hover:bg-cyan-300 disabled:opacity-50"
              >
                <Mail size={16} />
                {loading ? "SENDING…" : "SEND RESET LINK"}
              </button>
            </form>
          </>
        )}

        {step === "sent" && (
          <div data-testid="forgot-password-success">
            <div className="mb-4 grid h-14 w-14 place-items-center rounded-full border border-emerald-400/40 bg-emerald-400/10">
              <Mail size={24} className="text-emerald-300" />
            </div>
            <h1 className="font-heading text-2xl font-bold text-white">Check your email</h1>
            <p data-testid="forgot-password-success-message" className="mt-3 text-sm leading-6 text-slate-400">
              If an account exists for <span className="text-cyan-300">{email}</span>, a secure reset link has been sent. The link expires in 1 hour and is single-use.
            </p>
            <p className="mt-3 text-xs text-slate-500">No email? Check your spam folder. In a development environment, check the server console.</p>
          </div>
        )}

        {step === "error" && (
          <div data-testid="forgot-password-error">
            <h1 className="font-heading text-2xl font-bold text-white">Something went wrong</h1>
            <p data-testid="forgot-password-error-message" className="mt-3 text-sm text-red-300">{errorMsg}</p>
            <button onClick={() => setStep("form")} className="mt-4 text-sm text-cyan-300 hover:text-white">← Try again</button>
          </div>
        )}

        <div className="mt-6 border-t border-slate-800 pt-5">
          <Link data-testid="forgot-password-back-link" to="/login" className="flex items-center gap-2 text-sm text-slate-500 hover:text-cyan-300">
            <ArrowLeft size={14} /> Return to sign in
          </Link>
        </div>
      </div>
    </div>
  );
}