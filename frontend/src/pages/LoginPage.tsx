import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

export function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoading } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login(email, password);
      navigate("/trips");
    } catch {
      setError("Incorrect email or password.");
    }
  }

  return (
    <div className="max-w-md mx-auto px-6 py-24">
      <p className="label-eyebrow mb-2">Welcome back</p>
      <h1 className="font-display text-3xl text-text mb-8">Sign in</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" required />
        <Field label="Password" type="password" value={password} onChange={setPassword} autoComplete="current-password" required />
        {error && <p className="text-sm text-stamp">{error}</p>}
        <button
          type="submit"
          disabled={isLoading}
          className="mt-2 px-6 py-3 rounded-full bg-accent text-accent-ink font-medium hover:bg-accent-soft transition-colors disabled:opacity-60"
        >
          {isLoading ? "Signing in..." : "Sign in"}
        </button>
      </form>
      <div className="flex flex-col gap-4 mt-4">
        <div className="relative flex items-center py-2">
          <div className="flex-grow border-t border-border-soft"></div>
          <span className="flex-shrink-0 mx-4 text-text-faint text-xs">or</span>
          <div className="flex-grow border-t border-border-soft"></div>
        </div>
        <a
          href={(import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api").replace("/api", "") + "/api/oauth/google/login"}
          className="w-full text-center px-6 py-3 rounded-full border border-border-soft bg-surface text-text font-medium hover:bg-bg-soft transition-colors"
        >
          Continue with Google
        </a>
      </div>
      <p className="text-sm text-text-muted mt-6">
        New here?{" "}
        <Link to="/register" className="text-accent hover:text-accent-soft">
          Create an account
        </Link>
      </p>
    </div>
  );
}

export function Field({
  label, type, value, onChange, autoComplete, required, minLength,
}: {
  label: string; type: string; value: string; onChange: (v: string) => void;
  autoComplete?: string; required?: boolean; minLength?: number;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="label-eyebrow">{label}</span>
      <input
        type={type}
        value={value}
        required={required}
        minLength={minLength}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className="bg-surface border border-border-soft rounded-lg px-4 py-2.5 text-text placeholder:text-text-faint focus:border-accent transition-colors outline-none"
      />
    </label>
  );
}
