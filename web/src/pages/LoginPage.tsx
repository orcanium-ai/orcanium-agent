import { useState, type FormEvent } from "react";
import { useAuth } from "../hooks/useAuth";
import { useNavigate } from "react-router-dom";

export default function LoginPage() {
  const { status, login, setup } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const isSetup = status && !status.setup_complete;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (isSetup) {
        const ok = await setup(password);
        if (ok) navigate("/dashboard");
        else setError("Setup failed. Is the backend running?");
      } else {
        const ok = await login(password);
        if (ok) navigate("/dashboard");
        else setError("Invalid password.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-dvh items-center justify-center bg-stone-900/90">
      <form
        onSubmit={handleSubmit}
        className="w-full mx-4 max-w-sm rounded-3xl border border-stone-700/50 bg-[#191917]/50 p-8 shadow-lg shadow-stone-400/[0.1]"
      >
        <div className="mb-6 text-center">
          <div className="grid h-9 w-9 shrink-0 grid-cols-2 gap-[3px] rounded-full p-[5px]">
            <span className="rounded-full bg-white" />
            <span className="rounded-full bg-white/80" />
            <span className="rounded-full bg-white/60" />
            <span className="rounded-full bg-[#ff8a50]" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Orcanium
          </h1>
          <p className="mt-1 text-sm text-zinc-400">
            {isSetup ? "Create admin password" : "Enter admin password"}
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-900/40 px-4 py-2 text-sm text-red-400">
            {error}
          </div>
        )}

        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={isSetup ? "New password (min 4 chars)" : "Password"}
          minLength={4}
          required
          autoFocus
          className="mb-4 w-full rounded-lg border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-sm text-white placeholder-zinc-500 outline-none transition-colors focus:border-zinc-500"
        />

        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-zinc-100 px-4 py-2.5 text-sm font-medium text-black transition-colors hover:bg-zinc-300 disabled:opacity-50"
        >
          {busy ? "Please wait..." : isSetup ? "Set Password" : "Sign In"}
        </button>

        <p className="mt-4 text-center text-[10px] text-zinc-600">
          Orcanium AOS — Agent Orchestration System
        </p>
      </form>
    </div>
  );
}
