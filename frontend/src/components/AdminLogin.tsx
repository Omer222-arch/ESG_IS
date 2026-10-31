
import { useState, type FormEvent } from "react";

type AdminLoginProps = {
  onLogin: () => Promise<void>;
};

export function AdminLogin({ onLogin }: AdminLoginProps) {
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ password }),
      });

      if (!response.ok) {
        let message = "Login failed. Please try again.";
        try {
          const body = (await response.json()) as { detail?: string };
          message = body.detail || message;
        } catch {
          // Keep the fallback message.
        }
        throw new Error(message);
      }

      setPassword("");
      await onLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to log in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="admin-login-page">
      <form className="admin-login-card" onSubmit={handleSubmit}>
        <p className="admin-login-eyebrow">ESG INTELLIGENCE</p>
        <h1>Admin sign in</h1>
        <p className="admin-login-description">
          Sign in to access ESG document assessment and portfolio analysis.
        </p>

        <label htmlFor="admin-password">Password</label>
        <input
          id="admin-password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
          autoFocus
        />

        {error && (
          <p className="admin-login-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" disabled={loading || !password}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </main>
  );
}
