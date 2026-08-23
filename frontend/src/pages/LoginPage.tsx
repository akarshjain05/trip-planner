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
