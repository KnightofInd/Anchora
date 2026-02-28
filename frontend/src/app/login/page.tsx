"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.login(email, password);
      const token: string = res.data.access_token;
      document.cookie = `access_token=${token}; path=/; max-age=${60 * 60 * 8}; SameSite=Lax`;
      router.push("/dashboard");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Invalid email or password.";
      setError(typeof msg === "string" ? msg : "Invalid credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── Left branding panel ── */}
      <div className="hidden md:flex md:w-[60%] bg-[#0f172a] geometric-grid relative flex-col justify-between p-12 lg:p-20 text-white overflow-hidden">
        {/* logo */}
        <div className="z-10 flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-white/10">
            <span className="material-symbols-outlined text-3xl text-blue-300">anchor</span>
          </div>
          <div>
            <h1 className="text-3xl font-black tracking-tight leading-none">Anchora</h1>
            <p className="text-xs text-blue-300 font-semibold tracking-widest uppercase mt-0.5">Governance · AI · Audit</p>
          </div>
        </div>

        {/* feature blocks */}
        <div className="z-10 flex flex-col gap-8 max-w-lg">
          {[
            { icon: "psychology", title: "AI-augmented decisions", desc: "Enhance compliance accuracy with proprietary decision intelligence models trained on global regulations." },
            { icon: "history_edu", title: "Immutable audit trail", desc: "Complete transparency with cryptographically secure logging of every action and decision point." },
            { icon: "admin_panel_settings", title: "Role-based governance", desc: "Granular access controls designed for enterprise security standards and organisational hierarchies." },
          ].map(({ icon, title, desc }) => (
            <div key={title} className="flex gap-4 items-start group">
              <div className="p-2 rounded-xl bg-white/10 group-hover:bg-white/20 transition-colors shrink-0 mt-0.5">
                <span className="material-symbols-outlined text-blue-300">{icon}</span>
              </div>
              <div>
                <h3 className="text-base font-bold mb-1">{title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        <p className="z-10 text-slate-600 text-xs">© 2024 Anchora Intelligence Systems. All rights reserved.</p>
        {/* gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#0f172a]/80 via-transparent to-transparent pointer-events-none" />
      </div>

      {/* ── Right form panel ── */}
      <div className="flex-1 bg-white flex flex-col justify-center items-center p-6 md:p-12 lg:p-16 overflow-y-auto">
        <div className="w-full max-w-md space-y-8">
          {/* mobile logo */}
          <div className="flex md:hidden items-center gap-2 text-[#1e3fae]">
            <span className="material-symbols-outlined text-3xl">anchor</span>
            <span className="text-2xl font-black">Anchora</span>
          </div>

          <div className="space-y-1">
            <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Sign in to Anchora</h2>
            <p className="text-slate-500 text-sm">Welcome back. Enter your credentials to access the secure portal.</p>
          </div>

          {error && (
            <div role="alert"
              className="flex items-center gap-2 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              <span className="material-symbols-outlined text-base shrink-0">error</span>
              {error}
            </div>
          )}

          <form className="space-y-5" onSubmit={handleSubmit}>
            {/* email */}
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700" htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className={`w-full h-12 px-4 rounded-xl border text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1e3fae] focus:border-transparent transition-all ${error ? "border-red-400" : "border-slate-300"}`}
              />
            </div>

            {/* password */}
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700" htmlFor="password">Password</label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className={`w-full h-12 pl-4 pr-12 rounded-xl border text-slate-900 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1e3fae] focus:border-transparent transition-all ${error ? "border-red-400" : "border-slate-300"}`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-0 top-0 h-full px-3 flex items-center text-slate-400 hover:text-slate-600"
                  tabIndex={-1}
                >
                  <span className="material-symbols-outlined text-xl">
                    {showPassword ? "visibility" : "visibility_off"}
                  </span>
                </button>
              </div>
            </div>

            {/* submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full h-12 mt-2 bg-[#1e3fae] hover:bg-[#162f85] active:bg-[#163296] text-white font-bold rounded-xl shadow-md shadow-[#1e3fae]/20 hover:shadow-lg hover:shadow-[#1e3fae]/30 transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Signing in…
                </>
              ) : (
                <>
                  Sign In
                  <span className="material-symbols-outlined text-lg">arrow_forward</span>
                </>
              )}
            </button>
          </form>

          <div className="pt-6 border-t border-slate-100 text-center space-y-3">
            <p className="text-sm text-slate-500">
              Need enterprise access?{" "}
              <a href="#" className="font-semibold text-[#1e3fae] hover:text-[#162f85]">Contact Support</a>
            </p>
            <div className="flex justify-center items-center gap-1.5 opacity-50">
              <span className="material-symbols-outlined text-slate-400 text-base">lock</span>
              <span className="text-xs text-slate-400 font-medium">256-bit SSL Encrypted Connection</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
