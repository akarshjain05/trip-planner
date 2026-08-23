import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";
import { Field } from "./LoginPage";

export function RegisterPage() {
  const navigate = useNavigate();
  const { register, isLoading } = useAuthStore();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await register(email, password, fullName || undefined);
      navigate("/trips/new");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Could not create your account.");
    }
  }

  return (
    <div className="max-w-md mx-auto px-6 py-24">
      <p className="label-eyebrow mb-2">Get started</p>
      <h1 className="font-display text-3xl text-text mb-8">Create an account</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <Field label="Name" type="text" value={fullName} onChange={setFullName} autoComplete="name" />
        <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" required />
        <Field label="Password" type="password" value={password} onChange={setPassword} autoComplete="new-password" required minLength={8} />
        {error && <p className="text-sm text-stamp">{error}</p>}
        <button
          type="submit"
          disabled={isLoading}
          className="mt-2 px-6 py-3 rounded-full bg-accent text-accent-ink font-medium hover:bg-accent-soft transition-colors disabled:opacity-60"
        >
          {isLoading ? "Creating account..." : "Create account"}
        </button>
      </form>
      <p className="text-sm text-text-muted mt-6">
        Already have an account?{" "}
        <Link to="/login" className="text-accent hover:text-accent-soft">
          Sign in
        </Link>
      </p>
    </div>
  );
}
