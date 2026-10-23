
"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, LockKeyhole, Mail, Sparkles } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Login gagal.");
      }

      // Halaman utama akan membaca role dari sesi.
      router.replace("/");
      router.refresh();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Terjadi kesalahan."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <div className="login-glow" />

      <div className="login-container">
        <div className="brand login-brand">
          <div className="brand-logo">
            <Sparkles size={20} />
          </div>
          <span>
            HR <span className="brand-accent">Agent</span>
          </span>
        </div>

        <div className="login-head">
          <span className="eyebrow">
            <span className="live-dot" />
            AI-POWERED HR ASSISTANT
          </span>

          <h1>
            Selamat <span className="gradient-text">Datang.</span>
          </h1>

          <p>
            Masuk ke akun HR Agent untuk mengakses asisten AI,
            pengelolaan cuti, dan monitoring.
          </p>
        </div>

        <div className="login-card auth-card">
          <div className="auth-card-heading">
            <h2>Masuk ke Akun</h2>
            <p>Gunakan email dan password yang telah terdaftar.</p>
          </div>

          <form onSubmit={handleLogin}>
            <div className="auth-field">
              <label htmlFor="email">Alamat Email</label>
              <div className="auth-input-wrap">
                <Mail size={17} />
                <input
                  id="email"
                  type="email"
                  placeholder="nama@email.com"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="auth-field">
              <label htmlFor="password">Password</label>
              <div className="auth-input-wrap">
                <LockKeyhole size={17} />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Masukkan password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  className="auth-visibility"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={
                    showPassword
                      ? "Sembunyikan password"
                      : "Tampilkan password"
                  }
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="auth-error" role="alert">
                {error}
              </div>
            )}

            <button
              className="primary-btn login-btn"
              type="submit"
              disabled={loading}
            >
              {loading ? "Sedang masuk..." : "Masuk ke HR Agent"}
            </button>
          </form>
        </div>

        <p className="login-footer">
          HR Agent · AI-Powered Human Resource Management
        </p>
      </div>
    </main>
  );
}
