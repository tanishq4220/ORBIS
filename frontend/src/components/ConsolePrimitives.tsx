import { useId } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, RefreshCw, Radio, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { OrbisObject } from "@/lib/orbis";
import { number, percent, useConnection } from "@/lib/data";

const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-");
export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div data-testid="page-header" className="mb-5 flex flex-wrap items-end justify-between gap-3"><div><div data-testid="page-header-eyebrow" className="technical-label text-cyan-400/80">{eyebrow}</div><h1 data-testid="page-header-title" className="mt-1.5 font-heading text-2xl font-medium tracking-tight text-slate-100 xl:text-[28px]">{title}</h1><p data-testid="page-header-description" className="mt-1 max-w-3xl text-xs leading-5 text-slate-400">{description}</p></div>{action}</div>;
}
export function Panel({ title, eyebrow, children, className = "", action }: { title: string; eyebrow?: string; children: ReactNode; className?: string; action?: ReactNode }) {
  const id = slug(title);
  return <section data-testid={`panel-${id}`} className={`console-panel ${className}`}><div className="flex items-center justify-between gap-3 border-b border-[#1b2a39] px-4 py-3"><div><div data-testid={`panel-${id}-eyebrow`} className="technical-label">{eyebrow || "ORBIS INTELLIGENCE"}</div><h2 data-testid={`panel-${id}-title`} className="mt-1 text-[13px] font-medium text-slate-200">{title}</h2></div>{action || <span aria-hidden="true" className="h-1 w-1 bg-cyan-400/70" />}</div><div className="p-4">{children}</div></section>;
}
export function MetricCard({ label, value, hint, tone = "cyan" }: { label: string; value: string | number; hint?: string; tone?: "cyan" | "amber" | "red" | "green" }) {
  const color = { cyan: "text-cyan-200", amber: "text-amber-300", red: "text-rose-300", green: "text-emerald-300" }[tone]; const id = slug(label);
  return <div data-testid={`metric-card-${id}`} className="console-panel relative h-full px-4 py-3.5 hover:border-slate-500"><div data-testid={`metric-${id}-label`} className="technical-label">{label}</div><div data-testid={`metric-${id}-value`} className={`metric-value mt-2 font-mono text-[23px] font-medium ${color}`}>{typeof value === "number" ? value.toLocaleString() : value}</div>{hint ? <div data-testid={`metric-${id}-hint`} className="mt-1 text-[10px] text-slate-500">{hint}</div> : null}</div>;
}
export function StatusChip({ value, testId }: { value: string | null | undefined; testId?: string }) {
  const unique = useId(); const text = value || "N/A";
  const good = ["FAST", "RELIABLE", "CLEAR", "OPERATIONAL", "OK", "AVAILABLE", "CONNECTED"].includes(text);
  const bad = ["ERROR", "OFFLINE", "POTENTIAL_CONJUNCTION", "DEGRADED"].includes(text);
  return <span data-testid={testId || `status-${slug(text)}-${slug(unique)}`} className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-sm border px-1.5 py-1 font-mono text-[8px] tracking-wide ${good ? "border-emerald-400/15 bg-emerald-400/5 text-emerald-300" : bad ? "border-red-400/20 bg-red-400/5 text-red-300" : "border-amber-400/15 bg-amber-400/5 text-amber-200"}`}><span aria-hidden="true" className="h-1 w-1 rounded-full bg-current" />{text.replaceAll("_", " ")}</span>;
}
export function ObjectTable({ objects, onSelect }: { objects: OrbisObject[]; onSelect: (id: string) => void }) {
  return <div data-testid="object-table" className="overflow-x-auto"><table className="w-full min-w-[1050px] text-left text-[11px]"><thead className="border-y border-slate-800 bg-[#0e1925] font-mono text-[9px] uppercase tracking-wide text-slate-400"><tr>{["ID", "Name", "Type", "ACI", "Decision", "Model confidence", "ML prediction", "Data age", "Prediction error"].map(h => <th data-testid={`table-heading-${slug(h)}`} key={h} className="px-3 py-3 font-normal">{h}</th>)}</tr></thead><tbody>{objects.map(o => <tr data-testid={`object-row-${o.id}`} key={o.id} className="border-b border-slate-800/60 hover:bg-cyan-400/5"><td data-testid={`row-${o.id}-id`} className="px-3 py-3 font-mono text-slate-400">{o.id}</td><td className="max-w-[230px] px-3 py-3"><button data-testid={`open-object-${o.id}`} onClick={() => onSelect(o.id)} className="flex max-w-full items-center gap-2 text-left text-cyan-100 hover:text-cyan-300"><span className="truncate">{o.name || "UNNAMED OBJECT"}</span><ArrowUpRight size={11} /></button></td><td data-testid={`row-${o.id}-type`} className={`px-3 ${o.type === "Debris" ? "text-amber-300" : "text-slate-400"}`}>{o.type || "N/A"}</td><td data-testid={`row-${o.id}-aci`} className="px-3 font-mono">{number(o.aci, 3)}</td><td className="px-3"><StatusChip value={o.decision} /></td><td data-testid={`row-${o.id}-confidence`} className="px-3 font-mono text-cyan-200">{percent(o.model_confidence)}</td><td className="px-3"><StatusChip value={o.ml_prediction} /></td><td data-testid={`row-${o.id}-age`} className="px-3 font-mono text-slate-400">{number(o.data_age_days, 1, " d")}</td><td data-testid={`row-${o.id}-prediction-error`} title={o.prediction_error_km == null ? "No valid live/reference comparison available." : undefined} className="px-3 font-mono text-slate-400">{number(o.prediction_error_km, 2, " km")}</td></tr>)}</tbody></table></div>;
}
export function EmptyState({ message }: { message: string }) { const id = useId(); return <div data-testid={`empty-${slug(id)}`} className="grid min-h-28 place-items-center rounded-sm border border-dashed border-slate-700/70 p-6 text-center font-mono text-[10px] leading-6 text-slate-400">{message}</div>; }
export function DetailValue({ label, value }: { label: string; value: ReactNode }) { const id = useId(); return <div data-testid={`detail-${slug(label)}-${slug(id)}`} className="border-b border-slate-800/60 py-2.5"><div className="technical-label">{label}</div><div className="mt-1 font-mono text-[11px] text-slate-200">{value}</div></div>; }
export function DataState({ error, loading, retry, message = "LOADING CATALOG" }: { error?: boolean; loading?: boolean; retry?: () => void; message?: string }) {
  const config = useConnection(); const id = useId();
  if (!error && !loading) return null;
  return <div data-testid={`data-state-${slug(id)}`} role="status" className={`mb-4 flex flex-wrap items-center gap-3 rounded-sm border px-4 py-3 text-xs ${error ? "border-red-400/20 bg-red-400/5 text-red-200" : "border-cyan-400/15 text-slate-400"}`}>
    {error ? <AlertTriangle size={16} /> : <Radio size={15} className="animate-pulse" />}<div className="min-w-0 flex-1"><div data-testid={`data-state-label-${slug(id)}`} className="font-mono text-[10px]">{error ? "BACKEND OFFLINE / DATA UNAVAILABLE" : message}</div>{error ? <div className="mt-1 break-all text-[10px] text-slate-400">API: {config.data?.url || "Same-origin /api · hosted Python backend"}</div> : null}</div>
    {error && retry ? <Button data-testid={`retry-data-${slug(id)}`} variant="outline" size="sm" onClick={retry}><RefreshCw size={12} />RETRY</Button> : null}{error ? <Link data-testid={`set-api-url-${slug(id)}`} to="/settings" className="text-[10px] text-cyan-300 underline">SET API URL</Link> : null}
  </div>;
}