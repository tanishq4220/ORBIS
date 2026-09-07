import { useQuery } from "@tanstack/react-query";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Activity, BarChart3, ChevronRight, CircleUserRound, Database, Gauge, LogOut, Radar, Search, Settings2, ShieldAlert, Sparkles, Target, X } from "lucide-react";
import { apiGet, apiPost } from "@/lib/api";
import type { AuthUser, OrbisObject } from "@/lib/orbis";
import { useOrbisStore } from "@/lib/store";
import { useState } from "react";

const nav = [
  ["/dashboard", "Dashboard", Gauge], ["/objects", "Objects", Database], ["/satellites", "Satellites", Radar], ["/debris", "Debris", Sparkles],
  ["/conjunctions", "Conjunctions", ShieldAlert], ["/risk-analysis", "Risk Analysis", Target], ["/aci-insights", "ACI Insights", Activity], ["/analytics", "Analytics", BarChart3], ["/settings", "Settings", Settings2],
] as const;

function SearchBox() {
  const [query, setQuery] = useState("");
  const { setSelectedObject } = useOrbisStore();
  const results = useQuery({ queryKey: ["global-search", query], queryFn: () => apiGet<{ results: OrbisObject[] }>(`/search?q=${encodeURIComponent(query)}&limit=6`), enabled: query.trim().length > 1, staleTime: 20_000 });
  return <div className="relative w-full max-w-sm">
    <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
    <input data-testid="global-search-input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search catalog ID or name" className="h-9 w-full rounded border border-slate-800 bg-slate-950/80 pl-9 pr-3 font-mono text-[11px] text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-400/60" />
    {results.data?.results?.length ? <div data-testid="global-search-results" className="absolute left-0 right-0 top-11 z-50 overflow-hidden rounded border border-slate-700 bg-[#0b1220] shadow-2xl">
      {results.data.results.map((object) => <button data-testid={`global-search-result-${object.id}`} key={object.id} onClick={() => { setSelectedObject(object.id); setQuery(""); }} className="flex w-full items-center justify-between border-b border-slate-800 px-3 py-2 text-left hover:bg-cyan-400/10"><span className="truncate text-xs text-slate-200">{object.name || object.id}</span><span className="font-mono text-[10px] text-cyan-300">{object.id}</span></button>)}
    </div> : null}
  </div>;
}

export default function AppShell() {
  const navigate = useNavigate();
  const { selectedObjectId, setSelectedObject } = useOrbisStore();
  const user = useQuery({ queryKey: ["auth-me"], queryFn: () => apiGet<AuthUser | null>("/auth/me"), retry: false });
  const selected = useQuery({ queryKey: ["object", selectedObjectId], queryFn: () => apiGet<OrbisObject>(`/objects/${selectedObjectId}`), enabled: Boolean(selectedObjectId) });
  const logout = async () => { await apiPost<void>("/auth/logout"); navigate("/login", { replace: true }); };
  return <div className="min-h-screen bg-[#050811] text-slate-200">
    <aside data-testid="sidebar-navigation" className="fixed inset-y-0 left-0 z-40 hidden w-60 border-r border-slate-800/80 bg-[#080e1a] lg:flex lg:flex-col">
      <Link data-testid="orbis-logo-link" to="/dashboard" className="flex h-20 items-center gap-3 border-b border-slate-800 px-5"><div className="grid h-9 w-9 place-items-center rounded border border-cyan-400/50 bg-cyan-400/10 text-cyan-300"><Radar size={20} /></div><div><div data-testid="orbis-logo-label" className="font-heading text-lg font-black tracking-[0.18em] text-white">ORBIS</div><div data-testid="orbis-logo-subtitle" className="font-mono text-[8px] tracking-[0.14em] text-slate-500">ORBITAL RISK INTEL</div></div></Link>
      <nav className="flex-1 space-y-1 px-3 py-5">{nav.map(([to, label, Icon]) => <NavLink data-testid={`nav-${label.toLowerCase().replaceAll(" ", "-")}`} key={to} to={to} className={({ isActive }) => `group flex items-center gap-3 rounded px-3 py-2.5 text-xs font-semibold tracking-wide ${isActive ? "bg-cyan-400/10 text-cyan-300" : "text-slate-500 hover:bg-slate-900 hover:text-slate-200"}`}><Icon size={15} /><span>{label}</span>{label === "Conjunctions" ? <span data-testid="conjunction-alert-count" className="ml-auto rounded bg-red-500/15 px-1.5 py-0.5 font-mono text-[9px] text-red-300">LIVE</span> : null}</NavLink>)}</nav>
      <div className="border-t border-slate-800 p-4"><div data-testid="sidebar-system-status" className="mb-3 flex items-center gap-2 font-mono text-[10px] uppercase tracking-wider text-emerald-300"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />System nominal</div><div data-testid="sidebar-api-status" className="flex items-center justify-between font-mono text-[9px] text-slate-600"><span>API CONNECTION</span><span className="text-cyan-400">ENCRYPTED</span></div></div>
    </aside>
    <main className="lg:pl-60"><header data-testid="top-bar" className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-slate-800/80 bg-[#070c16]/90 px-4 backdrop-blur-xl sm:px-7"><div className="flex min-w-0 items-center gap-3"><div className="lg:hidden font-heading font-black tracking-[0.18em] text-white">ORBIS</div><SearchBox /></div><div className="flex items-center gap-3"><div data-testid="utc-clock" className="hidden items-center gap-2 font-mono text-[10px] text-slate-500 sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />UTC {new Date().toISOString().slice(11, 19)}Z</div><div data-testid="live-status" className="hidden rounded border border-emerald-400/20 bg-emerald-400/5 px-2 py-1 font-mono text-[9px] tracking-wider text-emerald-300 sm:block">LIVE / SGP4 SYNC</div><button data-testid="user-profile-button" onClick={() => navigate("/settings")} className="flex items-center gap-2 rounded px-2 py-1 hover:bg-slate-800"><CircleUserRound size={18} className="text-cyan-300" /><span data-testid="user-profile-name" className="hidden text-xs text-slate-300 md:block">{user.data?.name || "Operator"}</span></button><button data-testid="logout-button" onClick={logout} className="rounded p-2 text-slate-500 hover:bg-red-400/10 hover:text-red-300"><LogOut size={16} /></button></div></header><div className="min-h-[calc(100vh-4rem)] p-4 sm:p-7"><Outlet /></div></main>
    {selectedObjectId && selected.data ? <div data-testid="selected-object-dock" className="fixed bottom-4 right-4 z-40 w-72 rounded-lg border border-cyan-400/30 bg-[#0b1220]/95 p-4 shadow-[0_0_30px_rgba(0,229,255,0.12)] backdrop-blur-xl"><div className="mb-3 flex items-start justify-between"><div><div data-testid="selected-object-dock-label" className="font-mono text-[9px] tracking-[0.18em] text-cyan-300">SELECTED OBJECT</div><div data-testid="selected-object-dock-name" className="mt-1 truncate font-heading text-sm font-bold text-white">{selected.data.name || selected.data.id}</div></div><button data-testid="clear-selected-object-button" onClick={() => setSelectedObject(null)}><X size={15} className="text-slate-500 hover:text-white" /></button></div><div className="grid grid-cols-2 gap-2 font-mono text-[10px]"><div data-testid="selected-object-dock-aci" className="rounded bg-slate-900 p-2"><span className="text-slate-600">ACI</span><strong className="mt-1 block text-cyan-300">{selected.data.aci?.toFixed(3) ?? "N/A"}</strong></div><div data-testid="selected-object-dock-decision" className="rounded bg-slate-900 p-2"><span className="text-slate-600">DECISION</span><strong className="mt-1 block text-amber-300">{selected.data.decision || "N/A"}</strong></div></div><button data-testid="selected-object-open-detail" onClick={() => navigate(`/objects/${selectedObjectId}`)} className="mt-3 flex w-full items-center justify-between border-t border-slate-800 pt-3 text-left font-mono text-[10px] text-cyan-300 hover:text-white">OPEN FULL TELEMETRY <ChevronRight size={14} /></button></div> : null}
  </div>;
}