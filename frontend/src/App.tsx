import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router-dom";
import { apiGet } from "@/lib/api";
import AppShell from "@/components/WorkstationShell";
import type { AuthUser } from "@/lib/orbis";
import Dashboard from "@/pages/CommandDashboard";
import CatalogPage from "@/pages/CatalogWorkspace";
import ObjectDetail from "@/pages/ObjectWorkspace";
import Conjunctions from "@/pages/ScreeningWorkspace";
import ConjunctionHistory from "@/pages/HistoryWorkspace";
import AciInsights from "@/pages/AciWorkspace";
import Analytics from "@/pages/AnalyticsWorkspace";
import RiskAnalysis from "@/pages/RiskWorkspace";
import Settings from "@/pages/SettingsWorkspace";
import Login from "@/pages/Login";
import Register from "@/pages/RegisterWorkspace";
import ForgotPassword from "@/pages/ForgotPassword";

function ProtectedRoutes() { const session = useQuery({ queryKey: ["auth-me"], queryFn: () => apiGet<AuthUser | null>("/auth/me"), retry: false }); if (session.isLoading) return <div data-testid="session-loading" className="grid min-h-screen place-items-center bg-[#050811] font-mono text-xs text-cyan-300">AUTHENTICATING…</div>; if (session.isError || !session.data) return <Navigate to="/login" replace />; return <AppShell />; }
export default function App() {
  return <Routes><Route path="/login" element={<Login />} /><Route path="/register" element={<Register />} /><Route path="/forgot-password" element={<ForgotPassword />} /><Route element={<ProtectedRoutes />}><Route path="/" element={<Navigate to="/dashboard" replace />} /><Route path="/dashboard" element={<Dashboard />} /><Route path="/objects" element={<CatalogPage />} /><Route path="/objects/:id" element={<ObjectDetail />} /><Route path="/satellites" element={<CatalogPage mode="Satellite" />} /><Route path="/debris" element={<CatalogPage mode="Debris" />} /><Route path="/conjunctions" element={<Conjunctions />} /><Route path="/conjunctions/history" element={<ConjunctionHistory />} /><Route path="/risk-analysis" element={<RiskAnalysis />} /><Route path="/aci-insights" element={<AciInsights />} /><Route path="/analytics" element={<Analytics />} /><Route path="/settings" element={<Settings />} /></Route><Route path="*" element={<Navigate to="/dashboard" replace />} /></Routes>;
}
