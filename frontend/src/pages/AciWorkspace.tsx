import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight } from "lucide-react";
import { apiGet } from "@/lib/api";
import { useAnalytics, useSummary, number, percent } from "@/lib/data";
import { useOrbisStore } from "@/lib/store";
import type { PaginatedObjects } from "@/lib/orbis";
import {
  DataState,
  MetricCard,
  PageHeader,
  Panel,
  StatusChip,
} from "@/components/ConsolePrimitives";
import { HistogramPanel } from "@/components/MissionCharts";
import { ReliabilityContext } from "@/components/ObjectIntelligence";

export default function AciWorkspace() {
  const navigate = useNavigate();
  const { setSelectedObject } = useOrbisStore();
  const summary = useSummary();
  const analytics = useAnalytics();
  const [decisionFilter, setDecisionFilter] = useState<string>("ALL");

  const s = !summary.isError ? summary.data : undefined;
  const a = s?.aci;

  // Query catalog sample matching decision filter
  const objects = useQuery({
    queryKey: ["aci-workspace-objects", decisionFilter],
    queryFn: () => {
      const param = decisionFilter !== "ALL" ? `&decision=${decisionFilter}` : "";
      return apiGet<PaginatedObjects>(`/objects?limit=15&sort=aci&order=asc${param}`);
    },
    retry: false,
  });

  return (
    <div data-testid="aci-insights-page" className="fade-enter space-y-6">
      <PageHeader
        eyebrow="RELIABILITY / ADAPTIVE CONFIDENCE INDEX"
        title="ACI Operational Insights"
        description="A composite evidence confidence measure combining temporal decay, precise SP3 orbit validation, SGP4 trajectory consistency, and ML reliability."
        action={
          <button
            onClick={() => navigate("/conjunctions")}
            className="flex items-center gap-1.5 rounded border border-cyan-400/40 bg-cyan-400/10 px-3 py-1.5 font-mono text-[10px] font-bold text-cyan-200 transition-colors hover:bg-cyan-400/20"
          >
            OPEN SCREENING <ArrowUpRight size={12} />
          </button>
        }
      />

      <DataState
        error={summary.isError || analytics.isError}
        loading={summary.isLoading}
        retry={() => {
          summary.refetch();
          analytics.refetch();
        }}
      />

      {/* Metric Cards Row */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Mean ACI"
          value={number(a?.mean, 4)}
          hint="Catalog average confidence [0.0–1.0]"
        />
        <MetricCard
          label="Minimum ACI"
          value={number(a?.minimum, 4)}
          tone="amber"
          hint="Lowest confidence object in catalog"
        />
        <MetricCard
          label="Maximum ACI"
          value={number(a?.maximum, 4)}
          tone="green"
          hint="Highest confidence object in catalog"
        />
        <MetricCard
          label="Catalog Population"
          value={s?.total_objects?.toLocaleString() ?? "—"}
          hint={`${s?.satellites?.toLocaleString() ?? 0} active · ${s?.debris?.toLocaleString() ?? 0} debris`}
        />
      </div>

      {/* The 4 ACI Factors Explanatory Grid */}
      <Panel title="Four-Factor Mathematical Composition" eyebrow="ALGORITHMIC ARCHITECTURE">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 text-xs">
          <div className="rounded border border-slate-800 bg-[#080e18] p-3.5">
            <div className="font-mono text-[10px] font-bold text-cyan-300">FACTOR 1 · DATA AGE</div>
            <p className="mt-1.5 text-slate-400 leading-5">
              Evaluates elapsed time since TLE epoch. Exponential decay models degradation due to unmodeled atmospheric drag and solar radiation pressure.
            </p>
            <div className="mt-2 font-mono text-[9px] text-slate-500">Normalizer: linear threshold (7-day cutoff)</div>
          </div>

          <div className="rounded border border-slate-800 bg-[#080e18] p-3.5">
            <div className="font-mono text-[10px] font-bold text-emerald-300">FACTOR 2 · SP3 ERROR</div>
            <p className="mt-1.5 text-slate-400 leading-5">
              Ground-truth precise orbit validation. Compares SGP4 ECEF position against IGS precise GPS ephemerides at coincident timestamps.
            </p>
            <div className="mt-2 font-mono text-[9px] text-slate-500">Normalizer: 1.0 - (error_km / 100 km)</div>
          </div>

          <div className="rounded border border-slate-800 bg-[#080e18] p-3.5">
            <div className="font-mono text-[10px] font-bold text-sky-300">FACTOR 3 · SGP4 ARC</div>
            <p className="mt-1.5 text-slate-400 leading-5">
              Evaluates SGP4 numerical stability along the orbital propagation arc. Quantifies smooth velocity and position progression.
            </p>
            <div className="mt-2 font-mono text-[9px] text-slate-500">Normalizer: trajectory consistency [0–1]</div>
          </div>

          <div className="rounded border border-slate-800 bg-[#080e18] p-3.5">
            <div className="font-mono text-[10px] font-bold text-purple-300">FACTOR 4 · CALIBRATED ML</div>
            <p className="mt-1.5 text-slate-400 leading-5">
              Random Forest classifier calibrated via isotonic regression. Learns nonlinear reliability patterns from 6 orbital feature dimensions.
            </p>
            <div className="mt-2 font-mono text-[9px] text-slate-500">Normalizer: calibrated probability score</div>
          </div>
        </div>
      </Panel>

      {/* Histograms & Decision Rules */}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <HistogramPanel
          title="ACI distribution"
          id="aci-detail"
          data={!analytics.isError ? analytics.data?.aci_histogram || [] : []}
        />

        <Panel title="Operational Decision Breakdown" eyebrow="AUTOMATED ROUTING LOGIC">
          <div data-testid="aci-boundary-panel" className="space-y-3">
            {[
              ["FAST", "ACI ≥ 0.70 — Rapid automated clearance", s?.fast, "text-emerald-300", "border-emerald-500/20 bg-emerald-500/5"],
              ["DEEP", "ACI < 0.70 — Requires manual operator review", s?.deep, "text-amber-300", "border-amber-500/20 bg-amber-500/5"],
              ["INSUFFICIENT_DATA", "Missing critical orbital elements", s?.insufficient_data, "text-slate-400", "border-slate-800 bg-slate-900/40"],
            ].map(([label, rule, count, color, bg]) => (
              <button
                key={String(label)}
                data-testid={`aci-boundary-${label}`}
                onClick={() => setDecisionFilter(String(label))}
                className={`flex w-full items-center justify-between rounded border px-4 py-3 text-left transition-all ${
                  decisionFilter === label ? "ring-1 ring-cyan-400" : ""
                } ${bg}`}
              >
                <div>
                  <div className={`font-mono text-xs font-bold ${color}`}>{label}</div>
                  <div className="mt-1 text-[10px] text-slate-400">{rule}</div>
                </div>
                <span className="font-mono text-lg font-bold text-slate-100">
                  {typeof count === "number" ? count.toLocaleString() : "—"}
                </span>
              </button>
            ))}
          </div>

          <div className="mt-4 flex items-center justify-between pt-2">
            <span className="font-mono text-[9px] text-slate-500">FILTERING BY DECISION: {decisionFilter}</span>
            {decisionFilter !== "ALL" && (
              <button
                onClick={() => setDecisionFilter("ALL")}
                className="font-mono text-[9px] text-cyan-300 underline"
              >
                Reset to ALL
              </button>
            )}
          </div>
        </Panel>
      </div>

      {/* Lowest ACI Catalog Objects Table */}
      <Panel
        title={`Objects Requiring Operator Review (${decisionFilter})`}
        eyebrow="RANKED BY LOWEST ACI FIRST"
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-[11px]">
            <thead className="technical-label">
              <tr>
                {["Object", "ACI Score", "Decision", "ML Prediction", "Data Age", "SP3 Error", "Actions"].map(
                  (header) => (
                    <th key={header} className="px-3 pb-3 font-normal">
                      {header}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {!objects.isError ? (
                objects.data?.objects.map((o) => (
                  <tr
                    key={o.id}
                    data-testid={`aci-object-${o.id}`}
                    className="border-t border-slate-800 hover:bg-slate-900/30 transition-colors"
                  >
                    <td className="px-3 py-2.5">
                      <button
                        onClick={() => {
                          setSelectedObject(o.id);
                          navigate(`/objects/${o.id}`);
                        }}
                        className="text-left font-medium text-cyan-200 hover:underline"
                      >
                        {o.name || o.id}
                      </button>
                      <div className="font-mono text-[8px] text-slate-500">
                        {o.id} · {o.type}
                      </div>
                    </td>
                    <td className="px-3 font-mono font-bold text-slate-200">
                      {number(o.aci, 4)}
                    </td>
                    <td className="px-3">
                      <StatusChip value={o.decision} />
                    </td>
                    <td className="px-3">
                      <div className="font-mono text-cyan-100">{percent(o.model_confidence)}</div>
                      <span className="font-mono text-[8px] text-slate-500">{o.ml_prediction}</span>
                    </td>
                    <td className="px-3 font-mono text-slate-400">
                      {number(o.data_age_days, 1, " d")}
                    </td>
                    <td className="px-3 font-mono text-slate-400">
                      {o.prediction_error_km != null ? number(o.prediction_error_km, 2, " km") : "—"}
                    </td>
                    <td className="px-3">
                      <Link
                        to={`/conjunctions?target=${o.id}`}
                        className="font-mono text-[9px] text-cyan-300 hover:underline"
                      >
                        SCREEN ↗
                      </Link>
                    </td>
                  </tr>
                ))
              ) : null}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Context Banner */}
      <div className="grid gap-4 md:grid-cols-2">
        <ReliabilityContext />
        <Panel title="Operational Context" eyebrow="CONFIDENCE ≠ COLLISION PROBABILITY">
          <p data-testid="aci-interpretation" className="text-xs leading-6 text-slate-400">
            A high ACI indicates confidence in the available orbital elements. A lower value flags that
            propagation errors may be higher than normal. Neither decision guarantees an object is geometrically
            clear of collision hazards. Spatial safety requires conjunction screening.
          </p>
          <Link
            data-testid="aci-open-screening"
            to="/conjunctions"
            className="mt-3 inline-flex items-center gap-1.5 font-mono text-[10px] text-cyan-300 hover:underline"
          >
            OPEN CONJUNCTION SCREENING <ArrowUpRight size={11} />
          </Link>
        </Panel>
      </div>
    </div>
  );
}