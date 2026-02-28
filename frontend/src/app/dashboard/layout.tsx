"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { workflowApi, authApi } from "@/lib/api";

const NAV = [
  { href: "/dashboard",            label: "Overview",    icon: "dashboard" },
  { href: "/dashboard/decisions",  label: "Decisions",   icon: "balance" },
  { href: "/dashboard/workflows",  label: "Workflows",   icon: "account_tree" },
  { href: "/dashboard/knowledge",  label: "Knowledge",   icon: "library_books" },
  { href: "/dashboard/audit",      label: "Audit Trail", icon: "description" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router   = useRouter();

  // Pending workflow count for badge
  const { data: wfData } = useQuery({
    queryKey: ["workflows"],
    queryFn: () => workflowApi.list(),
    staleTime: 30_000,
  });
  const pendingCount: number =
    (wfData?.data ?? []).filter((w: { status: string }) => w.status === "pending").length;

  async function logout() {
    try { await authApi.logout(); } catch { /* ignore — still clear cookie */ }
    document.cookie = "access_token=; path=/; max-age=0";
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen bg-[#f6f6f8]">
      {/* ── Fixed Sidebar ── */}
      <aside className="fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-slate-200 flex flex-col">
        {/* Logo zone */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-slate-100 shrink-0">
          <div className="p-2 rounded-xl bg-[#1e3fae]/10 shrink-0">
            <span className="material-symbols-outlined text-[#1e3fae] text-xl leading-none">anchor</span>
          </div>
          <div className="min-w-0">
            <p className="text-[15px] font-black text-slate-900 leading-tight">Anchora</p>
            <p className="text-[10px] text-slate-400 font-semibold tracking-widest uppercase leading-tight">Governance &amp; AI</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV.map(({ href, label, icon }) => {
            const active =
              href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors group relative ${
                  active
                    ? "bg-[#1e3fae]/10 text-[#1e3fae]"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <span className={`material-symbols-outlined text-[20px] leading-none shrink-0 ${active ? "text-[#1e3fae]" : "text-slate-400 group-hover:text-slate-700"}`}>
                  {icon}
                </span>
                <span className={active ? "font-semibold" : ""}>{label}</span>
                {label === "Workflows" && pendingCount > 0 && (
                  <span className="ml-auto inline-flex items-center justify-center h-5 w-5 rounded-full bg-amber-100 text-amber-700 text-[10px] font-bold">
                    {pendingCount > 9 ? "9+" : pendingCount}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User section */}
        <div className="px-3 pb-4 space-y-1 border-t border-slate-100 pt-3 shrink-0">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="h-8 w-8 rounded-full bg-[#1e3fae] flex items-center justify-center text-white text-xs font-bold shrink-0">
              AC
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-800 truncate">Alex Chen</p>
              <p className="text-xs text-slate-400 truncate">Admin</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="w-full flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition-colors"
          >
            <span className="material-symbols-outlined text-[18px] text-slate-400">logout</span>
            Sign out
          </button>
        </div>
      </aside>

      {/* ── Main area ── */}
      <div className="flex-1 ml-64 flex flex-col min-h-screen">
        {/* Topbar */}
        <header className="sticky top-0 z-40 h-16 bg-white border-b border-slate-200 flex items-center px-6 gap-4 shrink-0">
          <div className="relative flex-1 max-w-xs">
            <span className="material-symbols-outlined text-slate-400 text-base absolute left-3 top-1/2 -translate-y-1/2">search</span>
            <input
              type="search"
              placeholder="Search…"
              className="w-full h-9 pl-9 pr-3 rounded-lg border border-slate-200 bg-slate-50 text-sm text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1e3fae]/30 focus:border-[#1e3fae]/50"
            />
          </div>
          <div className="flex-1" />
          <button className="relative p-2 rounded-lg hover:bg-slate-100 text-slate-500 transition-colors">
            <span className="material-symbols-outlined text-xl">notifications</span>
          </button>
          <Link
            href="/dashboard/decisions"
            className="flex items-center gap-1.5 h-9 px-4 rounded-xl bg-[#1e3fae] hover:bg-[#162f85] text-white text-sm font-semibold shadow-sm shadow-[#1e3fae]/20 transition-colors"
          >
            <span className="material-symbols-outlined text-base leading-none">add</span>
            New Decision
          </Link>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
